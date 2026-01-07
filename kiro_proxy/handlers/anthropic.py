"""Anthropic 协议处理 - /v1/messages"""
import json
import uuid
import time
import httpx
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse

from ..config import KIRO_API_URL, map_model_name
from ..core import state, RetryableRequest, is_retryable_error, stats_manager
from ..core.state import RequestLog
from ..credential import quota_manager
from ..kiro_api import build_headers, build_kiro_request, parse_event_stream_full, is_quota_exceeded_error
from ..converters import (
    generate_session_id,
    convert_anthropic_tools_to_kiro,
    convert_anthropic_messages_to_kiro,
    convert_kiro_response_to_anthropic,
    extract_images_from_content
)


def _extract_text_from_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            parts.append(_extract_text_from_content(item))
        return "".join(parts)
    if isinstance(content, dict):
        if "text" in content and isinstance(content.get("text"), str):
            return content["text"]
        if "content" in content:
            return _extract_text_from_content(content.get("content"))
    return ""


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return (len(text) + 3) // 4


def _count_tokens_from_messages(messages, system: str = "") -> int:
    total = _estimate_tokens(system) if system else 0
    for msg in messages or []:
        total += _estimate_tokens(_extract_text_from_content(msg.get("content")))
    return total


def _classify_kiro_error(error_text: str, status_code: int = 500):
    """分类 Kiro API 错误"""
    lowered = error_text.lower()
    
    # 配额超限
    if is_quota_exceeded_error(status_code, error_text):
        return 429, "rate_limit_error", "Rate limited, please retry later."
    
    # 模型不可用
    if "model_temporarily_unavailable" in error_text or "unexpectedly high load" in lowered:
        return 503, "overloaded_error", "Model temporarily unavailable, please retry."
    
    # 内容过长
    if "content_length_exceeds_threshold" in error_text or "too long" in lowered:
        return 400, "invalid_request_error", "Conversation too long, please /clear or start a new chat."
    
    # 认证错误
    if status_code == 401 or "unauthorized" in lowered or "invalid token" in lowered:
        return 401, "authentication_error", "Token expired or invalid, please refresh."
    
    return 500, "api_error", "Upstream API error."


async def handle_count_tokens(request: Request):
    '''Handle /v1/messages/count_tokens requests.'''
    body = await request.json()
    messages = body.get("messages", [])
    system = body.get("system", "")
    if not messages and not system:
        raise HTTPException(400, "messages required")
    return {"input_tokens": _count_tokens_from_messages(messages, system)}


async def handle_messages(request: Request):
    """处理 /v1/messages 请求"""
    start_time = time.time()
    log_id = uuid.uuid4().hex[:8]
    
    body = await request.json()
    model = map_model_name(body.get("model", "claude-sonnet-4"))
    messages = body.get("messages", [])
    system = body.get("system", "")
    stream = body.get("stream", False)
    tools = body.get("tools", [])
    
    if not messages:
        raise HTTPException(400, "messages required")
    
    session_id = generate_session_id(messages)
    account = state.get_available_account(session_id)
    
    if not account:
        raise HTTPException(503, "All accounts are rate limited or unavailable")
    
    # 检查 token 是否即将过期，尝试刷新
    if account.is_token_expiring_soon(5):
        print(f"[Anthropic] Token 即将过期，尝试刷新: {account.id}")
        success, msg = await account.refresh_token()
        if not success:
            print(f"[Anthropic] Token 刷新失败: {msg}")
    
    token = account.get_token()
    if not token:
        raise HTTPException(500, f"Failed to get token for account {account.name}")
    
    # 转换消息格式
    user_content, history, tool_results = convert_anthropic_messages_to_kiro(messages, system)
    
    # 提取最后一条消息中的图片
    images = []
    if messages:
        last_msg = messages[-1]
        if last_msg.get("role") == "user":
            _, images = extract_images_from_content(last_msg.get("content", ""))
    
    # 构建 Kiro 请求
    kiro_tools = convert_anthropic_tools_to_kiro(tools) if tools else None
    kiro_request = build_kiro_request(user_content, model, history, kiro_tools, images, tool_results)
    
    # 使用账号的动态 Machine ID
    creds = account.get_credentials()
    headers = build_headers(
        token,
        machine_id=account.get_machine_id(),
        profile_arn=creds.profile_arn if creds else None,
        client_id=creds.client_id if creds else None
    )
    
    if stream:
        return await _handle_stream(kiro_request, headers, account, model, log_id, start_time, session_id)
    else:
        return await _handle_non_stream(kiro_request, headers, account, model, log_id, start_time, session_id)


async def _handle_stream(kiro_request, headers, account, model, log_id, start_time, session_id=None):
    """Handle streaming responses with auto-retry on quota exceeded and network errors."""
    
    async def generate():
        current_account = account
        retry_count = 0
        max_retries = 2
        
        while retry_count <= max_retries:
            try:
                async with httpx.AsyncClient(verify=False, timeout=300) as client:
                    async with client.stream("POST", KIRO_API_URL, json=kiro_request, headers=headers) as response:
                        
                        # 处理配额超限
                        if response.status_code == 429 or is_quota_exceeded_error(response.status_code, ""):
                            current_account.mark_quota_exceeded("Rate limited (stream)")
                            
                            # 尝试切换账号
                            next_account = state.get_next_available_account(current_account.id)
                            if next_account and retry_count < max_retries:
                                print(f"[Stream] 配额超限，切换账号: {current_account.id} -> {next_account.id}")
                                current_account = next_account
                                token = current_account.get_token()
                                headers["Authorization"] = f"Bearer {token}"
                                retry_count += 1
                                continue
                            
                            yield f'data: {{"type":"error","error":{{"type":"rate_limit_error","message":"All accounts rate limited"}}}}\n\n'
                            return

                        # 处理可重试的服务端错误
                        if is_retryable_error(response.status_code):
                            if retry_count < max_retries:
                                print(f"[Stream] 服务端错误 {response.status_code}，重试 {retry_count + 1}/{max_retries}")
                                retry_count += 1
                                import asyncio
                                await asyncio.sleep(0.5 * (2 ** retry_count))
                                continue
                            yield f'data: {{"type":"error","error":{{"type":"api_error","message":"Server error after retries"}}}}\n\n'
                            return

                        if response.status_code != 200:
                            error_text = await response.aread()
                            error_str = error_text.decode()
                            print(f"=== Kiro API Error ===")
                            print(f"Status: {response.status_code}")
                            print(f"Response: {error_str[:500]}")
                            print(f"======================")
                            
                            # 检查是否为配额超限
                            if is_quota_exceeded_error(response.status_code, error_str):
                                current_account.mark_quota_exceeded(error_str[:100])
                                next_account = state.get_next_available_account(current_account.id)
                                if next_account and retry_count < max_retries:
                                    current_account = next_account
                                    headers["Authorization"] = f"Bearer {current_account.get_token()}"
                                    retry_count += 1
                                    continue

                            _, error_type, error_msg = _classify_kiro_error(error_str, response.status_code)
                            yield f'data: {{"type":"error","error":{{"type":"{error_type}","message":"{error_msg}"}}}}\n\n'
                            return

                        # 正常处理响应
                        msg_id = f"msg_{log_id}"
                        yield f'data: {{"type":"message_start","message":{{"id":"{msg_id}","type":"message","role":"assistant","content":[],"model":"{model}","stop_reason":null,"stop_sequence":null,"usage":{{"input_tokens":0,"output_tokens":0}}}}}}\n\n'
                        yield f'data: {{"type":"content_block_start","index":0,"content_block":{{"type":"text","text":""}}}}\n\n'

                        full_response = b""

                        async for chunk in response.aiter_bytes():
                            full_response += chunk

                            try:
                                pos = 0
                                while pos < len(chunk):
                                    if pos + 12 > len(chunk):
                                        break
                                    total_len = int.from_bytes(chunk[pos:pos+4], 'big')
                                    if total_len == 0 or total_len > len(chunk) - pos:
                                        break
                                    headers_len = int.from_bytes(chunk[pos+4:pos+8], 'big')
                                    payload_start = pos + 12 + headers_len
                                    payload_end = pos + total_len - 4

                                    if payload_start < payload_end:
                                        try:
                                            payload = json.loads(chunk[payload_start:payload_end].decode('utf-8'))
                                            content = None
                                            if 'assistantResponseEvent' in payload:
                                                content = payload['assistantResponseEvent'].get('content')
                                            elif 'content' in payload:
                                                content = payload['content']
                                            if content:
                                                yield f'data: {{"type":"content_block_delta","index":0,"delta":{{"type":"text_delta","text":{json.dumps(content)}}}}}\n\n'
                                        except Exception:
                                            pass
                                    pos += total_len
                            except Exception:
                                pass

                        result = parse_event_stream_full(full_response)

                        yield f'data: {{"type":"content_block_stop","index":0}}\n\n'

                        if result["tool_uses"]:
                            for i, tool_use in enumerate(result["tool_uses"], 1):
                                yield f'data: {{"type":"content_block_start","index":{i},"content_block":{{"type":"tool_use","id":"{tool_use["id"]}","name":"{tool_use["name"]}","input":{{}}}}}}\n\n'
                                yield f'data: {{"type":"content_block_delta","index":{i},"delta":{{"type":"input_json_delta","partial_json":{json.dumps(json.dumps(tool_use["input"]))}}}}}\n\n'
                                yield f'data: {{"type":"content_block_stop","index":{i}}}\n\n'

                        stop_reason = result["stop_reason"]
                        yield f'data: {{"type":"message_delta","delta":{{"stop_reason":"{stop_reason}","stop_sequence":null}},"usage":{{"output_tokens":100}}}}\n\n'
                        yield f'data: {{"type":"message_stop"}}\n\n'

                        current_account.request_count += 1
                        current_account.last_used = time.time()
                        return

            except httpx.TimeoutException:
                if retry_count < max_retries:
                    print(f"[Stream] 请求超时，重试 {retry_count + 1}/{max_retries}")
                    retry_count += 1
                    import asyncio
                    await asyncio.sleep(0.5 * (2 ** retry_count))
                    continue
                yield f'data: {{"type":"error","error":{{"type":"api_error","message":"Request timeout after retries"}}}}\n\n'
                return
            except httpx.ConnectError:
                if retry_count < max_retries:
                    print(f"[Stream] 连接错误，重试 {retry_count + 1}/{max_retries}")
                    retry_count += 1
                    import asyncio
                    await asyncio.sleep(0.5 * (2 ** retry_count))
                    continue
                yield f'data: {{"type":"error","error":{{"type":"api_error","message":"Connection error after retries"}}}}\n\n'
                return
            except Exception as e:
                # 检查是否为可重试的网络错误
                if is_retryable_error(None, e) and retry_count < max_retries:
                    print(f"[Stream] 网络错误，重试 {retry_count + 1}/{max_retries}: {type(e).__name__}")
                    retry_count += 1
                    import asyncio
                    await asyncio.sleep(0.5 * (2 ** retry_count))
                    continue
                yield f'data: {{"type":"error","error":{{"type":"api_error","message":"{str(e)}"}}}}\n\n'
                return

    return StreamingResponse(generate(), media_type="text/event-stream")


async def _handle_non_stream(kiro_request, headers, account, model, log_id, start_time, session_id=None):
    """Handle non-streaming responses with auto-retry on quota exceeded and network errors."""
    error_msg = None
    status_code = 200
    current_account = account
    max_retries = 2
    retry_ctx = RetryableRequest(max_retries=2)

    for retry in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(verify=False, timeout=300) as client:
                response = await client.post(KIRO_API_URL, json=kiro_request, headers=headers)
                status_code = response.status_code

                # 处理配额超限
                if response.status_code == 429 or is_quota_exceeded_error(response.status_code, response.text):
                    current_account.mark_quota_exceeded("Rate limited")
                    
                    # 尝试切换账号
                    next_account = state.get_next_available_account(current_account.id)
                    if next_account and retry < max_retries:
                        print(f"[NonStream] 配额超限，切换账号: {current_account.id} -> {next_account.id}")
                        current_account = next_account
                        token = current_account.get_token()
                        creds = current_account.get_credentials()
                        headers["Authorization"] = f"Bearer {token}"
                        continue
                    
                    raise HTTPException(429, "All accounts rate limited")

                # 处理可重试的服务端错误
                if is_retryable_error(response.status_code):
                    if retry < max_retries:
                        print(f"[NonStream] 服务端错误 {response.status_code}，重试 {retry + 1}/{max_retries}")
                        await retry_ctx.wait()
                        continue
                    raise HTTPException(response.status_code, f"Server error after {max_retries} retries")

                if response.status_code != 200:
                    error_msg = response.text
                    status, _, error_message = _classify_kiro_error(error_msg, response.status_code)
                    
                    # 检查是否为配额超限
                    if is_quota_exceeded_error(response.status_code, error_msg):
                        current_account.mark_quota_exceeded(error_msg[:100])
                        next_account = state.get_next_available_account(current_account.id)
                        if next_account and retry < max_retries:
                            current_account = next_account
                            headers["Authorization"] = f"Bearer {current_account.get_token()}"
                            continue
                    
                    raise HTTPException(status, error_message)

                result = parse_event_stream_full(response.content)
                current_account.request_count += 1
                current_account.last_used = time.time()

                return convert_kiro_response_to_anthropic(result, model, f"msg_{log_id}")

        except HTTPException:
            raise
        except httpx.TimeoutException as e:
            error_msg = f"Request timeout: {e}"
            status_code = 408
            if retry < max_retries:
                print(f"[NonStream] 请求超时，重试 {retry + 1}/{max_retries}")
                await retry_ctx.wait()
                continue
            raise HTTPException(408, "Request timeout after retries")
        except httpx.ConnectError as e:
            error_msg = f"Connection error: {e}"
            status_code = 502
            if retry < max_retries:
                print(f"[NonStream] 连接错误，重试 {retry + 1}/{max_retries}")
                await retry_ctx.wait()
                continue
            raise HTTPException(502, "Connection error after retries")
        except Exception as e:
            error_msg = str(e)
            status_code = 500
            # 检查是否为可重试的网络错误
            if is_retryable_error(None, e) and retry < max_retries:
                print(f"[NonStream] 网络错误，重试 {retry + 1}/{max_retries}: {type(e).__name__}")
                await retry_ctx.wait()
                continue
            raise HTTPException(500, str(e))
        finally:
            if retry == max_retries or status_code == 200:
                duration = (time.time() - start_time) * 1000
                state.add_log(RequestLog(
                    id=log_id,
                    timestamp=time.time(),
                    method="POST",
                    path="/v1/messages",
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
    
    raise HTTPException(503, "All retries exhausted")
