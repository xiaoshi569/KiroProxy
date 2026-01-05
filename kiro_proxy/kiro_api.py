"""Kiro API 调用模块"""
import json
import uuid
from typing import List, Dict, Any, Optional

from .config import KIRO_API_URL, MACHINE_ID


def build_headers(token: str, agent_mode: str = "vibe") -> dict:
    """构建 Kiro API 请求头"""
    return {
        "content-type": "application/json",
        "x-amzn-codewhisperer-optout": "true",
        "x-amzn-kiro-agent-mode": agent_mode,
        "x-amz-user-agent": f"aws-sdk-js/1.0.27 KiroIDE-0.8.0-{MACHINE_ID}",
        "amz-sdk-invocation-id": str(uuid.uuid4()),
        "amz-sdk-request": "attempt=1; max=3",
        "Authorization": f"Bearer {token}",
    }


def build_kiro_request(
    user_content: str,
    model: str,
    history: List[dict] = None,
    tools: List[dict] = None,
    images: List[dict] = None
) -> dict:
    """构建 Kiro API 请求体"""
    conversation_id = str(uuid.uuid4())
    
    user_input_message = {
        "content": user_content,
        "modelId": model,
        "origin": "AI_EDITOR",
        "userInputMessageContext": {}
    }
    
    # 添加图片
    if images:
        user_input_message["images"] = images
    
    # 添加工具定义
    if tools:
        user_input_message["userInputMessageContext"]["tools"] = tools
    
    current_message = {
        "userInputMessage": user_input_message
    }
    
    request = {
        "conversationState": {
            "agentContinuationId": str(uuid.uuid4()),
            "agentTaskType": "vibe",
            "chatTriggerType": "MANUAL",
            "conversationId": conversation_id,
            "currentMessage": current_message,
            "history": history or []
        }
    }
    
    return request


def parse_event_stream(raw: bytes) -> str:
    """解析 AWS event-stream 格式，返回文本内容"""
    result = parse_event_stream_full(raw)
    return "".join(result["content"]) or "[No response]"


def parse_event_stream_full(raw: bytes) -> dict:
    """解析 AWS event-stream 格式，返回完整结构（包含工具调用）"""
    result = {
        "content": [],
        "tool_uses": [],
        "stop_reason": "end_turn"
    }
    
    tool_input_buffer = {}
    
    pos = 0
    while pos < len(raw):
        if pos + 12 > len(raw):
            break
        total_len = int.from_bytes(raw[pos:pos+4], 'big')
        headers_len = int.from_bytes(raw[pos+4:pos+8], 'big')
        if total_len == 0 or total_len > len(raw) - pos:
            break
        
        header_start = pos + 12
        header_end = header_start + headers_len
        headers_data = raw[header_start:header_end]
        event_type = None
        
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
                
                # 处理文本内容
                if 'assistantResponseEvent' in payload:
                    e = payload['assistantResponseEvent']
                    if 'content' in e:
                        result["content"].append(e['content'])
                elif 'content' in payload and event_type != 'toolUseEvent':
                    result["content"].append(payload['content'])
                
                # 处理工具调用
                if event_type == 'toolUseEvent' or 'toolUseId' in payload:
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
                
            except:
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
