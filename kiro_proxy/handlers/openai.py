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
from ..core import state, is_retryable_error, stats_manager
from ..core.state import RequestLog
from ..kiro_api import build_headers, build_kiro_request, parse_event_stream, is_quota_exceeded_error
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
        raise HTTPException(503, "All accounts are rate limited or unavailable")
    
    # 检查 token 是否即将过期，尝试刷新
    if account.is_token_expiring_soon(5):
        print(f"[OpenAI] Token 即将过期，尝试刷新: {account.id}")
        success, msg = await account.refresh_token()
        if not success:
            print(f"[OpenAI] Token 刷新失败: {msg}")
    
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
    
    # 使用账号的动态 Machine ID
    creds = account.get_credentials()
    headers = build_headers(
        token,
        machine_id=account.get_machine_id(),
        profile_arn=creds.profile_arn if creds else None,
        client_id=creds.client_id if creds else None
    )
    
    error_msg = None
    status_code = 200
    content = ""
    current_account = account
    max_retries = 2
    
    for retry in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(verify=False, timeout=120) as client:
                resp = await client.post(KIRO_API_URL, json=kiro_request, headers=headers)
                status_code = resp.status_code
                
                # 处理配额超限
                if resp.status_code == 429 or is_quota_exceeded_error(resp.status_code, resp.text):
                    current_account.mark_quota_exceeded("Rate limited")
                    
                    # 尝试切换账号
                    next_account = state.get_next_available_account(current_account.id)
                    if next_account and retry < max_retries:
                        print(f"[OpenAI] 配额超限，切换账号: {current_account.id} -> {next_account.id}")
                        current_account = next_account
                        token = current_account.get_token()
                        creds = current_account.get_credentials()
                        headers = build_headers(
                            token,
                            machine_id=current_account.get_machine_id(),
                            profile_arn=creds.profile_arn if creds else None,
                            client_id=creds.client_id if creds else None
                        )
                        continue
                    
                    raise HTTPException(429, "All accounts rate limited")
                
                # 处理可重试的服务端错误
                if is_retryable_error(resp.status_code):
                    if retry < max_retries:
                        print(f"[OpenAI] 服务端错误 {resp.status_code}，重试 {retry + 1}/{max_retries}")
                        await asyncio.sleep(0.5 * (2 ** retry))
                        continue
                    raise HTTPException(resp.status_code, f"Server error after {max_retries} retries")
                
                if resp.status_code != 200:
                    error_msg = resp.text
                    print(f"[OpenAI] Kiro API error {resp.status_code}: {resp.text[:500]}")
                    
                    # 检查是否为配额超限
                    if is_quota_exceeded_error(resp.status_code, error_msg):
                        current_account.mark_quota_exceeded(error_msg[:100])
                        next_account = state.get_next_available_account(current_account.id)
                        if next_account and retry < max_retries:
                            current_account = next_account
                            headers["Authorization"] = f"Bearer {current_account.get_token()}"
                            continue
                    
                    raise HTTPException(resp.status_code, resp.text)
                
                content = parse_event_stream(resp.content)
                current_account.request_count += 1
                current_account.last_used = time.time()
                break
                
        except HTTPException:
            raise
        except httpx.TimeoutException:
            error_msg = "Request timeout"
            status_code = 408
            if retry < max_retries:
                print(f"[OpenAI] 请求超时，重试 {retry + 1}/{max_retries}")
                await asyncio.sleep(0.5 * (2 ** retry))
                continue
            raise HTTPException(408, "Request timeout after retries")
        except httpx.ConnectError:
            error_msg = "Connection error"
            status_code = 502
            if retry < max_retries:
                print(f"[OpenAI] 连接错误，重试 {retry + 1}/{max_retries}")
                await asyncio.sleep(0.5 * (2 ** retry))
                continue
            raise HTTPException(502, "Connection error after retries")
        except Exception as e:
            error_msg = str(e)
            status_code = 500
            # 检查是否为可重试的网络错误
            if is_retryable_error(None, e) and retry < max_retries:
                print(f"[OpenAI] 网络错误，重试 {retry + 1}/{max_retries}: {type(e).__name__}")
                await asyncio.sleep(0.5 * (2 ** retry))
                continue
            raise HTTPException(500, str(e))
    
    # 记录日志
    duration = (time.time() - start_time) * 1000
    state.add_log(RequestLog(
        id=log_id,
        timestamp=time.time(),
        method="POST",
        path="/v1/chat/completions",
        model=model,
        account_id=current_account.id if current_account else None,
        status=status_code,
        duration_ms=duration,
        error=error_msg
    ))
    
    # 记录统计
    stats_manager.record_request(
        account_id=current_account.id if current_account else "unknown",
        model=model,
        success=status_code == 200,
        latency_ms=duration
    )
    
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
