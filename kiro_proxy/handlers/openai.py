"""OpenAI 协议处理 - /v1/chat/completions"""
import json
import uuid
import time
import asyncio
import httpx
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse

from ..config import KIRO_API_URL, map_model_name, parse_stream_mode
from ..core import state, is_retryable_error, stats_manager
from ..core.state import RequestLog
from ..core.history_manager import HistoryManager, get_history_config, is_content_length_error
from ..core.error_handler import classify_error, ErrorType, format_error_log
from ..core.rate_limiter import get_rate_limiter
from ..kiro_api import build_headers, build_kiro_request, parse_event_stream, is_quota_exceeded_error
from ..converters import generate_session_id, convert_openai_messages_to_kiro, extract_images_from_content


class KiroStreamParser:
    """Kiro event-stream 流式解析器，支持文本和工具调用"""
    
    def __init__(self):
        self.buffer = b""
        self.tool_buffers = {}  # tool_id -> {name, input_parts}
        self.processed_pos = 0
    
    def feed(self, data: bytes) -> tuple[list[str], list[dict]]:
        """
        喂入数据，返回 (文本列表, 完成的工具调用列表)
        """
        self.buffer += data
        texts = []
        completed_tools = []
        
        pos = self.processed_pos
        while pos < len(self.buffer):
            if pos + 12 > len(self.buffer):
                break  # 不完整的帧头，等待更多数据
            
            total_len = int.from_bytes(self.buffer[pos:pos+4], 'big')
            headers_len = int.from_bytes(self.buffer[pos+4:pos+8], 'big')
            
            if total_len == 0:
                pos += 4
                continue
            
            if pos + total_len > len(self.buffer):
                break  # 不完整的帧，等待更多数据
            
            # 解析 headers 判断事件类型
            header_start = pos + 12
            header_end = header_start + headers_len
            headers_data = self.buffer[header_start:header_end]
            
            event_type = None
            try:
                headers_str = headers_data.decode('utf-8', errors='ignore')
                if 'toolUseEvent' in headers_str:
                    event_type = 'toolUseEvent'
                elif 'assistantResponseEvent' in headers_str:
                    event_type = 'assistantResponseEvent'
            except:
                pass
            
            # 解析 payload
            payload_start = pos + 12 + headers_len
            payload_end = pos + total_len - 4
            
            if payload_start < payload_end:
                try:
                    payload = json.loads(self.buffer[payload_start:payload_end].decode('utf-8'))
                    
                    # 文本内容
                    if 'assistantResponseEvent' in payload:
                        content = payload['assistantResponseEvent'].get('content', '')
                        if content:
                            texts.append(content)
                    
                    # 工具调用
                    if event_type == 'toolUseEvent' or 'toolUseId' in payload:
                        tool_id = payload.get('toolUseId', '')
                        tool_name = payload.get('name', '')
                        tool_input = payload.get('input', '')
                        
                        if tool_id:
                            if tool_id not in self.tool_buffers:
                                self.tool_buffers[tool_id] = {"name": tool_name, "input_parts": []}
                            if tool_name and not self.tool_buffers[tool_id]["name"]:
                                self.tool_buffers[tool_id]["name"] = tool_name
                            if tool_input:
                                self.tool_buffers[tool_id]["input_parts"].append(tool_input)
                except:
                    pass
            
            pos += total_len
        
        self.processed_pos = pos
        return texts, completed_tools
    
    def get_tool_calls(self) -> list[dict]:
        """获取所有工具调用（流结束时调用）"""
        tools = []
        for tool_id, data in self.tool_buffers.items():
            input_str = "".join(data["input_parts"])
            try:
                input_json = json.loads(input_str)
            except:
                input_json = {"raw": input_str}
            
            tools.append({
                "id": tool_id,
                "type": "function",
                "function": {
                    "name": data["name"],
                    "arguments": json.dumps(input_json)
                }
            })
        return tools


async def handle_chat_completions(request: Request):
    """处理 /v1/chat/completions 请求"""
    start_time = time.time()
    log_id = uuid.uuid4().hex[:8]
    
    body = await request.json()
    raw_model = body.get("model", "claude-sonnet-4")
    
    # 解析流式模式前缀
    model_without_prefix, use_fake_stream = parse_stream_mode(raw_model)
    model = map_model_name(model_without_prefix)
    
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    tools = body.get("tools", None)
    tool_choice = body.get("tool_choice", None)
    
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
    
    # 使用账号的动态 Machine ID（提前构建，供摘要使用）
    creds = account.get_credentials()
    headers = build_headers(
        token,
        machine_id=account.get_machine_id(),
        profile_arn=creds.profile_arn if creds else None,
        client_id=creds.client_id if creds else None
    )
    
    # 限速检查
    rate_limiter = get_rate_limiter()
    can_request, wait_seconds, reason = rate_limiter.can_request(account.id)
    if not can_request:
        print(f"[OpenAI] 限速: {reason}")
        await asyncio.sleep(wait_seconds)
    
    # 使用增强的转换函数
    user_content, history, tool_results, kiro_tools = convert_openai_messages_to_kiro(
        messages, model, tools, tool_choice
    )
    
    # 历史消息预处理
    history_manager = HistoryManager(get_history_config(), cache_key=session_id)
    
    async def call_summary(prompt: str) -> str:
        req = build_kiro_request(prompt, "claude-haiku-4.5", [])
        try:
            async with httpx.AsyncClient(verify=False, timeout=60) as client:
                resp = await client.post(KIRO_API_URL, json=req, headers=headers)
                if resp.status_code == 200:
                    return parse_event_stream(resp.content)
        except Exception as e:
            print(f"[Summary] API 调用失败: {e}")
        return ""

    # 检查是否需要智能摘要或错误重试预摘要
    if history_manager.should_summarize(history) or history_manager.should_pre_summary_for_error_retry(history, user_content):
        history = await history_manager.pre_process_async(history, user_content, call_summary)
    else:
        history = history_manager.pre_process(history, user_content)
    
    # 摘要/截断后再次修复历史交替和 toolUses/toolResults 配对
    from ..converters import fix_history_alternation
    history = fix_history_alternation(history)
    
    if history_manager.was_truncated:
        print(f"[OpenAI] {history_manager.truncate_info}")

    
    # 提取最后一条消息中的图片
    images = []
    if messages:
        last_msg = messages[-1]
        if last_msg.get("role") == "user":
            _, images = extract_images_from_content(last_msg.get("content", ""))
    
    kiro_request = build_kiro_request(
        user_content, model, history, 
        images=images,
        tools=kiro_tools if kiro_tools else None,
        tool_results=tool_results if tool_results else None
    )
    
    error_msg = None
    status_code = 200
    content = ""
    current_account = account
    max_retries = 2
    
    # 真流式模式：跳过重试循环，直接返回流式响应
    if stream and not use_fake_stream:
        async def generate_real_stream():
            nonlocal current_account, status_code, error_msg
            stream_start = time.time()
            parser = KiroStreamParser()
            
            try:
                async with httpx.AsyncClient(verify=False, timeout=120) as client:
                    async with client.stream("POST", KIRO_API_URL, json=kiro_request, headers=headers) as resp:
                        status_code = resp.status_code
                        
                        if resp.status_code != 200:
                            error_text = await resp.aread()
                            error_msg = error_text.decode('utf-8', errors='ignore')[:500]
                            
                            # 记录错误统计
                            duration = (time.time() - stream_start) * 1000
                            stats_manager.record_request(
                                account_id=current_account.id,
                                model=model,
                                success=False,
                                latency_ms=duration
                            )
                            
                            error_data = {
                                "id": f"chatcmpl-{log_id}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [{"index": 0, "delta": {"content": f"[Error {resp.status_code}]: {error_msg[:100]}"}, "finish_reason": "stop"}]
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"
                            yield "data: [DONE]\n\n"
                            return
                        
                        async for chunk in resp.aiter_bytes():
                            texts, _ = parser.feed(chunk)
                            
                            for text in texts:
                                data = {
                                    "id": f"chatcmpl-{log_id}",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": model,
                                    "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]
                                }
                                yield f"data: {json.dumps(data)}\n\n"
                        
                        # 流结束，检查工具调用
                        tool_calls = parser.get_tool_calls()
                        if tool_calls:
                            tool_data = {
                                "id": f"chatcmpl-{log_id}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"tool_calls": tool_calls},
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(tool_data)}\n\n"
                            
                            end_data = {
                                "id": f"chatcmpl-{log_id}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]
                            }
                            yield f"data: {json.dumps(end_data)}\n\n"
                        else:
                            end_data = {
                                "id": f"chatcmpl-{log_id}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                            }
                            yield f"data: {json.dumps(end_data)}\n\n"
                        
                        yield "data: [DONE]\n\n"
                        
                        # 记录成功统计
                        current_account.request_count += 1
                        current_account.last_used = time.time()
                        get_rate_limiter().record_request(current_account.id)
                        
                        duration = (time.time() - stream_start) * 1000
                        stats_manager.record_request(
                            account_id=current_account.id,
                            model=model,
                            success=True,
                            latency_ms=duration
                        )
                        
            except Exception as e:
                error_msg = str(e)
                status_code = 500
                
                duration = (time.time() - stream_start) * 1000
                stats_manager.record_request(
                    account_id=current_account.id if current_account else "unknown",
                    model=model,
                    success=False,
                    latency_ms=duration
                )
                
                error_data = {
                    "id": f"chatcmpl-{log_id}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": f"[Stream Error: {str(e)}]"}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate_real_stream(), media_type="text/event-stream")
    
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
                    
                    # 使用统一的错误处理
                    error = classify_error(resp.status_code, error_msg)
                    print(format_error_log(error, current_account.id))
                    
                    # 账号封禁 - 禁用账号
                    if error.should_disable_account:
                        current_account.enabled = False
                        from ..credential import CredentialStatus
                        current_account.status = CredentialStatus.SUSPENDED
                        print(f"[OpenAI] 账号 {current_account.id} 已被禁用 (封禁)")
                    
                    # 配额超限 - 标记冷却
                    if error.type == ErrorType.RATE_LIMITED:
                        current_account.mark_quota_exceeded(error_msg[:100])
                    
                    # 尝试切换账号
                    if error.should_switch_account:
                        next_account = state.get_next_available_account(current_account.id)
                        if next_account and retry < max_retries:
                            print(f"[OpenAI] 切换账号: {current_account.id} -> {next_account.id}")
                            current_account = next_account
                            headers["Authorization"] = f"Bearer {current_account.get_token()}"
                            continue
                    
                    # 检查是否为内容长度超限错误，尝试截断重试
                    if error.type == ErrorType.CONTENT_TOO_LONG:
                        history_chars, user_chars, total_chars = history_manager.estimate_request_chars(
                            history, user_content
                        )
                        print(f"[OpenAI] 内容长度超限: history={history_chars} chars, user={user_chars} chars, total={total_chars} chars")
                        truncated_history, should_retry = await history_manager.handle_length_error_async(
                            history, retry, call_summary
                        )
                        if should_retry:
                            print(f"[OpenAI] 内容长度超限，{history_manager.truncate_info}")
                            history = truncated_history
                            kiro_request = build_kiro_request(
                                user_content, model, history,
                                images=images,
                                tools=kiro_tools if kiro_tools else None,
                                tool_results=tool_results if tool_results else None
                            )
                            continue
                        else:
                            print(f"[OpenAI] 内容长度超限但未重试: retry={retry}/{max_retries}")
                    
                    raise HTTPException(resp.status_code, error.user_message)
                
                content = parse_event_stream(resp.content)
                current_account.request_count += 1
                current_account.last_used = time.time()
                get_rate_limiter().record_request(current_account.id)
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
        # 伪流式：先获取完整响应，再分块发送
        async def generate_fake_stream():
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
        
        return StreamingResponse(generate_fake_stream(), media_type="text/event-stream")
    
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
