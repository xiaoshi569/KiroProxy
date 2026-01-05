"""OpenAI 协议处理 - /v1/chat/completions"""
import json
import uuid
import time
import asyncio
import httpx
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse

from ..config import KIRO_API_URL, map_model_name
from ..models import state, RequestLog
from ..kiro_api import build_headers, build_kiro_request, parse_event_stream
from ..converters import generate_session_id, convert_openai_messages_to_kiro, extract_images_from_content


async def handle_chat_completions(request: Request):
    """处理 /v1/chat/completions 请求"""
    start_time = time.time()
    log_id = uuid.uuid4().hex[:8]
    
    body = await request.json()
    model = map_model_name(body.get("model", "claude-sonnet-4"))
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    
    if not messages:
        raise HTTPException(400, "messages required")
    
    session_id = generate_session_id(messages)
    account = state.get_available_account(session_id)
    
    if not account:
        raise HTTPException(503, "All accounts are rate limited")
    
    token = account.get_token()
    if not token:
        raise HTTPException(500, f"Failed to get token for account {account.name}")
    
    user_content, history = convert_openai_messages_to_kiro(messages, model)
    
    # 提取最后一条消息中的图片
    images = []
    if messages:
        last_msg = messages[-1]
        if last_msg.get("role") == "user":
            _, images = extract_images_from_content(last_msg.get("content", ""))
    
    kiro_request = build_kiro_request(user_content, model, history, images=images)
    headers = build_headers(token)
    
    error_msg = None
    status_code = 200
    content = ""
    
    try:
        async with httpx.AsyncClient(verify=False, timeout=120) as client:
            resp = await client.post(KIRO_API_URL, json=kiro_request, headers=headers)
            status_code = resp.status_code
            
            if resp.status_code == 429:
                state.mark_rate_limited(account.id, 60)
                new_account = state.get_available_account()
                if new_account and new_account.id != account.id:
                    token = new_account.get_token()
                    headers = build_headers(token)
                    resp = await client.post(KIRO_API_URL, json=kiro_request, headers=headers)
                    status_code = resp.status_code
                    account = new_account
                else:
                    raise HTTPException(429, "Rate limited")
            
            if resp.status_code != 200:
                error_msg = resp.text
                # 打印详细错误信息
                import logging
                logging.error(f"Kiro API error {resp.status_code}: {resp.text[:500]}")
                raise HTTPException(resp.status_code, resp.text)
            
            content = parse_event_stream(resp.content)
            account.request_count += 1
            account.last_used = time.time()
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        raise HTTPException(500, str(e))
    finally:
        duration = (time.time() - start_time) * 1000
        state.add_log(RequestLog(
            id=log_id,
            timestamp=time.time(),
            method="POST",
            path="/v1/chat/completions",
            model=model,
            account_id=account.id if account else None,
            status=status_code,
            duration_ms=duration,
            error=error_msg
        ))
    
    if stream:
        async def generate():
            for chunk in [content[i:i+20] for i in range(0, len(content), 20)]:
                data = {
                    "id": f"chatcmpl-{log_id}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(0.02)
            
            end_data = {
                "id": f"chatcmpl-{log_id}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(end_data)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    return {
        "id": f"chatcmpl-{log_id}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }
