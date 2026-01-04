#!/usr/bin/env python3
"""
Kiro API 代理服务器 - 增强版
支持多账号轮询、请求日志、配额监控、429自动切换、工具调用等功能
"""

import json
import uuid
import httpx
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime, timedelta
from pathlib import Path
import logging
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from collections import deque
import time
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Kiro API Proxy", docs_url="/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 配置 ====================

KIRO_API_URL = "https://q.us-east-1.amazonaws.com/generateAssistantResponse"
MODELS_URL = "https://q.us-east-1.amazonaws.com/ListAvailableModels"
TOKEN_PATH = Path.home() / ".aws/sso/cache/kiro-auth-token.json"
MACHINE_ID = "fa41d5def91e29225c73f6ea8ee0941a87bd812aae5239e3dde72c3ba7603a26"

# ==================== 数据结构 ====================

@dataclass
class Account:
    id: str
    name: str
    token_path: str
    enabled: bool = True
    rate_limited_until: Optional[float] = None
    request_count: int = 0
    error_count: int = 0
    last_used: Optional[float] = None
    
    def is_available(self) -> bool:
        if not self.enabled:
            return False
        if self.rate_limited_until and time.time() < self.rate_limited_until:
            return False
        return True
    
    def get_token(self) -> str:
        try:
            with open(self.token_path) as f:
                return json.load(f).get("accessToken", "")
        except:
            return ""

@dataclass
class RequestLog:
    id: str
    timestamp: float
    method: str
    path: str
    model: str
    account_id: Optional[str]
    status: int
    duration_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    error: Optional[str] = None

# ==================== 全局状态 ====================

class ProxyState:
    def __init__(self):
        self.accounts: List[Account] = []
        self.request_logs: deque = deque(maxlen=1000)
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.session_locks: Dict[str, str] = {}
        self.session_timestamps: Dict[str, float] = {}
        self.start_time: float = time.time()
        self._init_default_account()
    
    def _init_default_account(self):
        if TOKEN_PATH.exists():
            self.accounts.append(Account(id="default", name="默认账号", token_path=str(TOKEN_PATH)))
    
    def get_available_account(self, session_id: Optional[str] = None) -> Optional[Account]:
        if session_id and session_id in self.session_locks:
            account_id = self.session_locks[session_id]
            ts = self.session_timestamps.get(session_id, 0)
            if time.time() - ts < 60:
                for acc in self.accounts:
                    if acc.id == account_id and acc.is_available():
                        self.session_timestamps[session_id] = time.time()
                        return acc
        available = [a for a in self.accounts if a.is_available()]
        if not available:
            return None
        account = min(available, key=lambda a: a.request_count)
        if session_id:
            self.session_locks[session_id] = account.id
            self.session_timestamps[session_id] = time.time()
        return account
    
    def mark_rate_limited(self, account_id: str, duration_seconds: int = 60):
        for acc in self.accounts:
            if acc.id == account_id:
                acc.rate_limited_until = time.time() + duration_seconds
                acc.error_count += 1
                logger.warning(f"Account {acc.name} rate limited for {duration_seconds}s")
                break
    
    def add_log(self, log: RequestLog):
        self.request_logs.append(log)
        self.total_requests += 1
        if log.error:
            self.total_errors += 1
    
    def get_stats(self) -> dict:
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": int(uptime),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": f"{(self.total_errors / max(1, self.total_requests) * 100):.1f}%",
            "accounts_total": len(self.accounts),
            "accounts_available": len([a for a in self.accounts if a.is_available()]),
            "recent_logs": len(self.request_logs)
        }

state = ProxyState()

# ==================== 工具函数 ====================

def build_headers(token: str, agent_mode: str = "vibe") -> dict:
    return {
        "content-type": "application/json",
        "x-amzn-codewhisperer-optout": "true",
        "x-amzn-kiro-agent-mode": agent_mode,
        "x-amz-user-agent": f"aws-sdk-js/1.0.27 KiroIDE-0.8.0-{MACHINE_ID}",
        "amz-sdk-invocation-id": str(uuid.uuid4()),
        "amz-sdk-request": "attempt=1; max=3",
        "Authorization": f"Bearer {token}",
    }

def generate_session_id(messages: list) -> str:
    content = json.dumps(messages[:3], sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]

# ==================== Anthropic 工具格式转换 ====================

def convert_anthropic_tools_to_kiro(tools: List[dict]) -> List[dict]:
    """将 Anthropic 工具格式转换为 Kiro 格式"""
    kiro_tools = []
    for tool in tools:
        kiro_tool = {
            "toolSpecification": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "inputSchema": {
                    "json": tool.get("input_schema", {})
                }
            }
        }
        kiro_tools.append(kiro_tool)
    return kiro_tools

def convert_anthropic_messages_to_kiro(messages: List[dict], system: str = "") -> tuple:
    """将 Anthropic 消息格式转换为 Kiro 格式，返回 (user_content, history)"""
    history = []
    user_content = ""
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        # 处理 content 可能是列表的情况
        if isinstance(content, list):
            text_parts = []
            tool_results = []
            for block in content:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    tool_results.append({
                        "toolUseId": block.get("tool_use_id", ""),
                        "content": block.get("content", "")
                    })
            content = "\n".join(text_parts)
            if tool_results:
                # 工具结果需要特殊处理
                for tr in tool_results:
                    history.append({
                        "toolResultMessage": {
                            "toolUseId": tr["toolUseId"],
                            "content": tr["content"] if isinstance(tr["content"], str) else json.dumps(tr["content"])
                        }
                    })
                continue
        
        if role == "user":
            if system and not history:
                content = f"{system}\n\n{content}"
            history.append({
                "userInputMessage": {
                    "content": content,
                    "modelId": "claude-sonnet-4",
                    "origin": "AI_EDITOR"
                }
            })
            user_content = content
        elif role == "assistant":
            # 检查是否有工具调用
            tool_uses = []
            if isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if block.get("type") == "tool_use":
                        tool_uses.append({
                            "toolUseId": block.get("id", ""),
                            "name": block.get("name", ""),
                            "input": json.dumps(block.get("input", {}))
                        })
            
            history.append({
                "assistantResponseMessage": {
                    "content": content if isinstance(content, str) else "",
                    "toolUses": tool_uses
                }
            })
    
    return user_content, history[:-1] if history else []  # 最后一条是当前消息，不放入历史

# ==================== AWS Event Stream 解析 ====================

def parse_event_stream_full(raw: bytes) -> dict:
    """解析 AWS event-stream 格式，返回完整的响应结构"""
    result = {
        "content": [],
        "tool_uses": [],
        "stop_reason": "end_turn"
    }
    
    current_tool = None
    tool_input_buffer = {}
    
    pos = 0
    while pos < len(raw):
        if pos + 12 > len(raw):
            break
        total_len = int.from_bytes(raw[pos:pos+4], 'big')
        headers_len = int.from_bytes(raw[pos+4:pos+8], 'big')
        if total_len == 0 or total_len > len(raw) - pos:
            break
        
        # 解析 headers 获取事件类型
        header_start = pos + 12
        header_end = header_start + headers_len
        headers_data = raw[header_start:header_end]
        event_type = None
        
        # 简单解析 headers
        try:
            headers_str = headers_data.decode('utf-8', errors='ignore')
            if 'toolUseEvent' in headers_str:
                event_type = 'toolUseEvent'
            elif 'assistantResponseEvent' in headers_str:
                event_type = 'assistantResponseEvent'
        except:
            pass
        
        payload_start = pos + 12 + headers_len
        payload_end = pos + total_len - 4
        
        if payload_start < payload_end:
            try:
                payload = json.loads(raw[payload_start:payload_end].decode('utf-8'))
                
                if event_type == 'assistantResponseEvent' or 'content' in payload:
                    content = payload.get('content', '')
                    if content:
                        result["content"].append(content)
                
                elif event_type == 'toolUseEvent' or 'toolUseId' in payload:
                    tool_id = payload.get('toolUseId', '')
                    tool_name = payload.get('name', '')
                    tool_input = payload.get('input', '')
                    
                    if tool_id:
                        if tool_id not in tool_input_buffer:
                            tool_input_buffer[tool_id] = {
                                "id": tool_id,
                                "name": tool_name,
                                "input_parts": []
                            }
                        if tool_name and not tool_input_buffer[tool_id]["name"]:
                            tool_input_buffer[tool_id]["name"] = tool_name
                        if tool_input:
                            tool_input_buffer[tool_id]["input_parts"].append(tool_input)
                
            except Exception as e:
                pass
        
        pos += total_len
    
    # 组装工具调用
    for tool_id, tool_data in tool_input_buffer.items():
        input_str = "".join(tool_data["input_parts"])
        try:
            input_json = json.loads(input_str)
        except:
            input_json = {"raw": input_str}
        
        result["tool_uses"].append({
            "type": "tool_use",
            "id": tool_data["id"],
            "name": tool_data["name"],
            "input": input_json
        })
    
    if result["tool_uses"]:
        result["stop_reason"] = "tool_use"
    
    return result

def parse_event_stream(raw: bytes) -> str:
    """解析 AWS event-stream 格式，只返回文本内容"""
    result = parse_event_stream_full(raw)
    return "".join(result["content"]) or "[No response]"

# ==================== 模型映射 ====================

MODEL_MAPPING = {
    "claude-3-5-sonnet-20241022": "claude-sonnet-4",
    "claude-3-5-sonnet-latest": "claude-sonnet-4",
    "claude-3-5-sonnet": "claude-sonnet-4",
    "claude-3-5-haiku-20241022": "claude-haiku-4.5",
    "claude-3-5-haiku-latest": "claude-haiku-4.5",
    "claude-3-opus-20240229": "claude-opus-4.5",
    "claude-3-opus-latest": "claude-opus-4.5",
    "claude-3-sonnet-20240229": "claude-sonnet-4",
    "claude-3-haiku-20240307": "claude-haiku-4.5",
    "claude-4-sonnet": "claude-sonnet-4",
    "claude-4-opus": "claude-opus-4.5",
    "gpt-4o": "claude-sonnet-4",
    "gpt-4o-mini": "claude-haiku-4.5",
    "gpt-4-turbo": "claude-sonnet-4",
    "gpt-4": "claude-sonnet-4",
    "gpt-3.5-turbo": "claude-haiku-4.5",
    "o1": "claude-opus-4.5",
    "o1-preview": "claude-opus-4.5",
    "o1-mini": "claude-sonnet-4",
    "gemini-2.0-flash": "claude-sonnet-4",
    "gemini-2.0-flash-thinking": "claude-opus-4.5",
    "gemini-1.5-pro": "claude-sonnet-4.5",
    "gemini-1.5-flash": "claude-sonnet-4",
    "sonnet": "claude-sonnet-4",
    "haiku": "claude-haiku-4.5",
    "opus": "claude-opus-4.5",
}

def map_model_name(model: str) -> str:
    if not model:
        return "claude-sonnet-4"
    if model in MODEL_MAPPING:
        return MODEL_MAPPING[model]
    kiro_models = {"auto", "claude-sonnet-4.5", "claude-sonnet-4", "claude-haiku-4.5", "claude-opus-4.5"}
    if model in kiro_models:
        return model
    model_lower = model.lower()
    if "opus" in model_lower:
        return "claude-opus-4.5"
    if "haiku" in model_lower:
        return "claude-haiku-4.5"
    if "sonnet" in model_lower:
        return "claude-sonnet-4.5" if "4.5" in model_lower else "claude-sonnet-4"
    return "claude-sonnet-4"


# ==================== API 端点 ====================

@app.get("/v1/models")
async def list_models():
    """OpenAI 兼容的模型列表"""
    models = [
        {"id": "claude-sonnet-4", "object": "model", "owned_by": "kiro"},
        {"id": "claude-sonnet-4.5", "object": "model", "owned_by": "kiro"},
        {"id": "claude-haiku-4.5", "object": "model", "owned_by": "kiro"},
        {"id": "claude-opus-4.5", "object": "model", "owned_by": "kiro"},
        {"id": "auto", "object": "model", "owned_by": "kiro"},
    ]
    return {"object": "list", "data": models}

@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    """Anthropic 兼容接口 - 支持工具调用"""
    start_time = time.time()
    body = await request.json()
    
    model = map_model_name(body.get("model", "claude-sonnet-4"))
    messages = body.get("messages", [])
    system = body.get("system", "")
    stream = body.get("stream", False)
    tools = body.get("tools", [])
    max_tokens = body.get("max_tokens", 16000)
    
    session_id = generate_session_id(messages)
    account = state.get_available_account(session_id)
    
    if not account:
        raise HTTPException(status_code=503, detail="No available accounts")
    
    token = account.get_token()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 转换消息格式
    user_content, history = convert_anthropic_messages_to_kiro(messages, system)
    
    # 构建 Kiro 请求
    kiro_request = {
        "conversationState": {
            "conversationId": str(uuid.uuid4()),
            "history": history
        },
        "userInputMessage": {
            "content": user_content,
            "modelId": model,
            "origin": "AI_EDITOR"
        },
        "userInputMessageContext": {}
    }
    
    # 添加工具定义
    if tools:
        kiro_tools = convert_anthropic_tools_to_kiro(tools)
        kiro_request["userInputMessageContext"]["tools"] = kiro_tools
    
    headers = build_headers(token)
    
    async def generate_stream():
        """流式响应生成器"""
        try:
            async with httpx.AsyncClient(verify=False, timeout=300) as client:
                async with client.stream("POST", KIRO_API_URL, json=kiro_request, headers=headers) as response:
                    if response.status_code == 429:
                        state.mark_rate_limited(account.id)
                        yield f'data: {{"type":"error","error":{{"type":"rate_limit_error","message":"Rate limited"}}}}\n\n'
                        return
                    
                    if response.status_code != 200:
                        yield f'data: {{"type":"error","error":{{"type":"api_error","message":"API error: {response.status_code}"}}}}\n\n'
                        return
                    
                    # 发送开始事件
                    msg_id = f"msg_{uuid.uuid4().hex[:24]}"
                    yield f'data: {{"type":"message_start","message":{{"id":"{msg_id}","type":"message","role":"assistant","content":[],"model":"{model}","stop_reason":null,"stop_sequence":null,"usage":{{"input_tokens":0,"output_tokens":0}}}}}}\n\n'
                    yield f'data: {{"type":"content_block_start","index":0,"content_block":{{"type":"text","text":""}}}}\n\n'
                    
                    # 收集完整响应用于解析工具调用
                    full_response = b""
                    text_buffer = ""
                    
                    async for chunk in response.aiter_bytes():
                        full_response += chunk
                        
                        # 尝试实时解析文本内容
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
                                        if 'content' in payload and payload['content']:
                                            text = payload['content']
                                            yield f'data: {{"type":"content_block_delta","index":0,"delta":{{"type":"text_delta","text":{json.dumps(text)}}}}}\n\n'
                                    except:
                                        pass
                                pos += total_len
                        except:
                            pass
                    
                    # 解析完整响应获取工具调用
                    result = parse_event_stream_full(full_response)
                    
                    # 结束文本块
                    yield f'data: {{"type":"content_block_stop","index":0}}\n\n'
                    
                    # 如果有工具调用，发送工具调用块
                    if result["tool_uses"]:
                        for i, tool_use in enumerate(result["tool_uses"], 1):
                            yield f'data: {{"type":"content_block_start","index":{i},"content_block":{{"type":"tool_use","id":"{tool_use["id"]}","name":"{tool_use["name"]}","input":{{}}}}}}\n\n'
                            yield f'data: {{"type":"content_block_delta","index":{i},"delta":{{"type":"input_json_delta","partial_json":{json.dumps(json.dumps(tool_use["input"]))}}}}}\n\n'
                            yield f'data: {{"type":"content_block_stop","index":{i}}}\n\n'
                    
                    # 发送结束事件
                    stop_reason = result["stop_reason"]
                    yield f'data: {{"type":"message_delta","delta":{{"stop_reason":"{stop_reason}","stop_sequence":null}},"usage":{{"output_tokens":100}}}}\n\n'
                    yield f'data: {{"type":"message_stop"}}\n\n'
                    
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f'data: {{"type":"error","error":{{"type":"api_error","message":"{str(e)}"}}}}\n\n'
    
    async def generate_non_stream():
        """非流式响应"""
        try:
            async with httpx.AsyncClient(verify=False, timeout=300) as client:
                response = await client.post(KIRO_API_URL, json=kiro_request, headers=headers)
                
                if response.status_code == 429:
                    state.mark_rate_limited(account.id)
                    raise HTTPException(status_code=429, detail="Rate limited")
                
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail="API error")
                
                result = parse_event_stream_full(response.content)
                
                # 构建 Anthropic 格式响应
                content = []
                text = "".join(result["content"])
                if text:
                    content.append({"type": "text", "text": text})
                
                for tool_use in result["tool_uses"]:
                    content.append(tool_use)
                
                return {
                    "id": f"msg_{uuid.uuid4().hex[:24]}",
                    "type": "message",
                    "role": "assistant",
                    "content": content,
                    "model": model,
                    "stop_reason": result["stop_reason"],
                    "stop_sequence": None,
                    "usage": {"input_tokens": 100, "output_tokens": 100}
                }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Non-stream error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    account.request_count += 1
    account.last_used = time.time()
    
    if stream:
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
    else:
        return await generate_non_stream()

@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI 兼容接口"""
    start_time = time.time()
    body = await request.json()
    
    model = map_model_name(body.get("model", "claude-sonnet-4"))
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    
    session_id = generate_session_id(messages)
    account = state.get_available_account(session_id)
    
    if not account:
        raise HTTPException(status_code=503, detail="No available accounts")
    
    token = account.get_token()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 转换 OpenAI 消息格式
    system_content = ""
    user_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            system_content = msg.get("content", "")
        else:
            user_messages.append(msg)
    
    # 获取最后一条用户消息
    user_content = ""
    history = []
    for msg in user_messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join([c.get("text", "") for c in content if c.get("type") == "text"])
        
        if msg.get("role") == "user":
            if system_content and not history:
                content = f"{system_content}\n\n{content}"
            history.append({
                "userInputMessage": {
                    "content": content,
                    "modelId": model,
                    "origin": "AI_EDITOR"
                }
            })
            user_content = content
        elif msg.get("role") == "assistant":
            history.append({
                "assistantResponseMessage": {
                    "content": content
                }
            })
    
    kiro_request = {
        "conversationState": {
            "conversationId": str(uuid.uuid4()),
            "history": history[:-1] if history else []
        },
        "userInputMessage": {
            "content": user_content,
            "modelId": model,
            "origin": "AI_EDITOR"
        },
        "userInputMessageContext": {}
    }
    
    headers = build_headers(token)
    
    async def generate_stream():
        try:
            async with httpx.AsyncClient(verify=False, timeout=300) as client:
                async with client.stream("POST", KIRO_API_URL, json=kiro_request, headers=headers) as response:
                    if response.status_code == 429:
                        state.mark_rate_limited(account.id)
                        yield f'data: {{"error": "Rate limited"}}\n\n'
                        return
                    
                    if response.status_code != 200:
                        yield f'data: {{"error": "API error: {response.status_code}"}}\n\n'
                        return
                    
                    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
                    
                    async for chunk in response.aiter_bytes():
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
                                        if 'content' in payload and payload['content']:
                                            delta = {"role": "assistant", "content": payload['content']}
                                            chunk_data = {
                                                "id": chat_id,
                                                "object": "chat.completion.chunk",
                                                "created": int(time.time()),
                                                "model": model,
                                                "choices": [{"index": 0, "delta": delta, "finish_reason": None}]
                                            }
                                            yield f"data: {json.dumps(chunk_data)}\n\n"
                                    except:
                                        pass
                                pos += total_len
                        except:
                            pass
                    
                    # 发送结束
                    end_data = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                    }
                    yield f"data: {json.dumps(end_data)}\n\n"
                    yield "data: [DONE]\n\n"
                    
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}")
            yield f'data: {{"error": "{str(e)}"}}\n\n'
    
    account.request_count += 1
    account.last_used = time.time()
    
    if stream:
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
    else:
        async with httpx.AsyncClient(verify=False, timeout=300) as client:
            response = await client.post(KIRO_API_URL, json=kiro_request, headers=headers)
            
            if response.status_code == 429:
                state.mark_rate_limited(account.id)
                raise HTTPException(status_code=429, detail="Rate limited")
            
            text = parse_event_stream(response.content)
            
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200}
            }

# Gemini 兼容接口
@app.post("/v1/models/{model_name}:generateContent")
async def gemini_generate(model_name: str, request: Request):
    """Gemini 兼容接口"""
    body = await request.json()
    
    model = map_model_name(model_name)
    contents = body.get("contents", [])
    
    account = state.get_available_account()
    if not account:
        raise HTTPException(status_code=503, detail="No available accounts")
    
    token = account.get_token()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 转换 Gemini 消息格式
    user_content = ""
    history = []
    for content in contents:
        role = content.get("role", "user")
        parts = content.get("parts", [])
        text = " ".join([p.get("text", "") for p in parts if "text" in p])
        
        if role == "user":
            history.append({
                "userInputMessage": {
                    "content": text,
                    "modelId": model,
                    "origin": "AI_EDITOR"
                }
            })
            user_content = text
        elif role == "model":
            history.append({
                "assistantResponseMessage": {
                    "content": text
                }
            })
    
    kiro_request = {
        "conversationState": {
            "conversationId": str(uuid.uuid4()),
            "history": history[:-1] if history else []
        },
        "userInputMessage": {
            "content": user_content,
            "modelId": model,
            "origin": "AI_EDITOR"
        },
        "userInputMessageContext": {}
    }
    
    headers = build_headers(token)
    
    async with httpx.AsyncClient(verify=False, timeout=300) as client:
        response = await client.post(KIRO_API_URL, json=kiro_request, headers=headers)
        
        if response.status_code == 429:
            state.mark_rate_limited(account.id)
            raise HTTPException(status_code=429, detail="Rate limited")
        
        text = parse_event_stream(response.content)
        
        return {
            "candidates": [{
                "content": {
                    "parts": [{"text": text}],
                    "role": "model"
                },
                "finishReason": "STOP"
            }]
        }


# ==================== 管理 API ====================

@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    return state.get_stats()

@app.get("/api/accounts")
async def get_accounts():
    """获取账号列表"""
    return [{
        "id": acc.id,
        "name": acc.name,
        "enabled": acc.enabled,
        "available": acc.is_available(),
        "request_count": acc.request_count,
        "error_count": acc.error_count,
        "rate_limited": acc.rate_limited_until > time.time() if acc.rate_limited_until else False
    } for acc in state.accounts]

@app.post("/api/accounts")
async def add_account(request: Request):
    """添加账号"""
    body = await request.json()
    name = body.get("name", f"Account {len(state.accounts) + 1}")
    token_path = body.get("token_path", "")
    
    if not token_path or not Path(token_path).exists():
        raise HTTPException(status_code=400, detail="Invalid token path")
    
    account = Account(
        id=str(uuid.uuid4())[:8],
        name=name,
        token_path=token_path
    )
    state.accounts.append(account)
    return {"status": "ok", "account_id": account.id}

@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: str):
    """删除账号"""
    state.accounts = [a for a in state.accounts if a.id != account_id]
    return {"status": "ok"}

@app.post("/api/accounts/{account_id}/toggle")
async def toggle_account(account_id: str):
    """切换账号启用状态"""
    for acc in state.accounts:
        if acc.id == account_id:
            acc.enabled = not acc.enabled
            return {"status": "ok", "enabled": acc.enabled}
    raise HTTPException(status_code=404, detail="Account not found")

@app.get("/api/logs")
async def get_logs(limit: int = Query(default=100, le=1000)):
    """获取请求日志"""
    logs = list(state.request_logs)[-limit:]
    return [asdict(log) for log in logs]

# ==================== Web UI ====================

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kiro API Proxy</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 15px; }
        header img { width: 40px; height: 40px; }
        header h1 { font-size: 24px; font-weight: 600; }
        header span { color: #666; font-size: 14px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .stat-card .label { font-size: 12px; color: #666; text-transform: uppercase; }
        .stat-card .value { font-size: 28px; font-weight: 600; margin-top: 5px; }
        .section { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section h2 { font-size: 18px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { font-weight: 600; color: #666; font-size: 12px; text-transform: uppercase; }
        .status { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .status.ok { background: #e8f5e9; color: #2e7d32; }
        .status.error { background: #ffebee; color: #c62828; }
        .status.limited { background: #fff3e0; color: #ef6c00; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #333; color: #fff; }
        .btn-danger { background: #c62828; color: #fff; }
        .btn:hover { opacity: 0.9; }
        .endpoint { background: #f5f5f5; padding: 10px 15px; border-radius: 4px; font-family: monospace; margin: 5px 0; }
        .endpoint code { color: #333; }
        .form-row { display: flex; gap: 10px; margin-top: 15px; }
        .form-row input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        footer { text-align: center; padding: 20px; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <img src="/assets/icon.svg" alt="Kiro">
            <div>
                <h1>Kiro API Proxy</h1>
                <span>v1.0.0</span>
            </div>
        </header>
        
        <div class="stats" id="stats">
            <div class="stat-card"><div class="label">Uptime</div><div class="value" id="uptime">-</div></div>
            <div class="stat-card"><div class="label">Requests</div><div class="value" id="requests">-</div></div>
            <div class="stat-card"><div class="label">Errors</div><div class="value" id="errors">-</div></div>
            <div class="stat-card"><div class="label">Accounts</div><div class="value" id="accounts">-</div></div>
        </div>
        
        <div class="section">
            <h2>API Endpoints</h2>
            <div class="endpoint"><code>POST /v1/messages</code> - Anthropic (Claude Code)</div>
            <div class="endpoint"><code>POST /v1/chat/completions</code> - OpenAI (Codex CLI)</div>
            <div class="endpoint"><code>POST /v1/models/{model}:generateContent</code> - Gemini</div>
            <div class="endpoint"><code>GET /v1/models</code> - Model List</div>
        </div>
        
        <div class="section">
            <h2>Accounts</h2>
            <table id="accounts-table">
                <thead><tr><th>Name</th><th>Status</th><th>Requests</th><th>Errors</th><th>Actions</th></tr></thead>
                <tbody></tbody>
            </table>
            <div class="form-row">
                <input type="text" id="account-name" placeholder="Account Name">
                <input type="text" id="token-path" placeholder="Token Path">
                <button class="btn btn-primary" onclick="addAccount()">Add Account</button>
            </div>
        </div>
        
        <footer>Kiro API Proxy - For personal use only</footer>
    </div>
    
    <script>
        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('uptime').textContent = formatUptime(data.uptime_seconds);
            document.getElementById('requests').textContent = data.total_requests;
            document.getElementById('errors').textContent = data.total_errors;
            document.getElementById('accounts').textContent = `${data.accounts_available}/${data.accounts_total}`;
        }
        
        async function loadAccounts() {
            const res = await fetch('/api/accounts');
            const accounts = await res.json();
            const tbody = document.querySelector('#accounts-table tbody');
            tbody.innerHTML = accounts.map(acc => `
                <tr>
                    <td>${acc.name}</td>
                    <td><span class="status ${acc.available ? 'ok' : (acc.rate_limited ? 'limited' : 'error')}">${acc.available ? 'Available' : (acc.rate_limited ? 'Rate Limited' : 'Disabled')}</span></td>
                    <td>${acc.request_count}</td>
                    <td>${acc.error_count}</td>
                    <td>
                        <button class="btn" onclick="toggleAccount('${acc.id}')">${acc.enabled ? 'Disable' : 'Enable'}</button>
                        <button class="btn btn-danger" onclick="deleteAccount('${acc.id}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        }
        
        async function addAccount() {
            const name = document.getElementById('account-name').value;
            const tokenPath = document.getElementById('token-path').value;
            await fetch('/api/accounts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, token_path: tokenPath})
            });
            loadAccounts();
        }
        
        async function toggleAccount(id) {
            await fetch(`/api/accounts/${id}/toggle`, {method: 'POST'});
            loadAccounts();
        }
        
        async function deleteAccount(id) {
            if (confirm('Delete this account?')) {
                await fetch(`/api/accounts/${id}`, {method: 'DELETE'});
                loadAccounts();
            }
        }
        
        function formatUptime(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            return h > 0 ? `${h}h ${m}m` : `${m}m`;
        }
        
        loadStats();
        loadAccounts();
        setInterval(loadStats, 5000);
        setInterval(loadAccounts, 10000);
    </script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE

@app.get("/assets/{path:path}")
async def serve_assets(path: str):
    """提供静态资源"""
    file_path = Path("assets") / path
    if file_path.exists():
        content_type = "image/svg+xml" if path.endswith(".svg") else "application/octet-stream"
        return StreamingResponse(open(file_path, "rb"), media_type=content_type)
    raise HTTPException(status_code=404)

# ==================== 启动 ====================

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"\n{'='*50}")
    print(f"  Kiro API Proxy v1.0.0")
    print(f"  http://localhost:{port}")
    print(f"{'='*50}\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
