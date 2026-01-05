"""协议转换模块 - Anthropic/OpenAI/Gemini <-> Kiro"""
import json
import hashlib
import base64
import re
from typing import List, Dict, Any, Tuple, Optional


def generate_session_id(messages: list) -> str:
    """基于消息内容生成会话ID"""
    content = json.dumps(messages[:3], sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def extract_images_from_content(content) -> Tuple[str, List[dict]]:
    """从消息内容中提取文本和图片
    
    Returns:
        (text_content, images_list)
    """
    if isinstance(content, str):
        return content, []
    
    if not isinstance(content, list):
        return str(content), []
    
    text_parts = []
    images = []
    
    for block in content:
        if isinstance(block, str):
            text_parts.append(block)
        elif isinstance(block, dict):
            block_type = block.get("type", "")
            
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            
            elif block_type == "image":
                # Anthropic 格式
                source = block.get("source", {})
                media_type = source.get("media_type", "image/jpeg")
                data = source.get("data", "")
                
                # 提取格式
                fmt = "jpeg"
                if "png" in media_type:
                    fmt = "png"
                elif "gif" in media_type:
                    fmt = "gif"
                elif "webp" in media_type:
                    fmt = "webp"
                
                images.append({
                    "format": fmt,
                    "source": {"bytes": data}
                })
            
            elif block_type == "image_url":
                # OpenAI 格式
                image_url = block.get("image_url", {})
                url = image_url.get("url", "")
                
                if url.startswith("data:"):
                    # data:image/jpeg;base64,/9j/4AAQ...
                    match = re.match(r'data:image/(\w+);base64,(.+)', url)
                    if match:
                        fmt = match.group(1)
                        data = match.group(2)
                        images.append({
                            "format": fmt,
                            "source": {"bytes": data}
                        })
    
    return "\n".join(text_parts), images


# ==================== Anthropic 转换 ====================

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


def convert_anthropic_messages_to_kiro(messages: List[dict], system: str = "") -> Tuple[str, List[dict]]:
    """将 Anthropic 消息格式转换为 Kiro 格式
    
    Returns:
        (user_content, history)
    """
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
            
            # 工具结果需要特殊处理
            if tool_results:
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
    
    # 最后一条是当前消息，不放入历史
    return user_content, history[:-1] if history else []


def convert_kiro_response_to_anthropic(result: dict, model: str, msg_id: str) -> dict:
    """将 Kiro 响应转换为 Anthropic 格式"""
    content = []
    text = "".join(result["content"])
    if text:
        content.append({"type": "text", "text": text})
    
    for tool_use in result["tool_uses"]:
        content.append(tool_use)
    
    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": model,
        "stop_reason": result["stop_reason"],
        "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 100}
    }


# ==================== OpenAI 转换 ====================

def convert_openai_messages_to_kiro(messages: List[dict], model: str) -> Tuple[str, List[dict]]:
    """将 OpenAI 消息格式转换为 Kiro 格式"""
    system_content = ""
    history = []
    user_content = ""
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if isinstance(content, list):
            content = " ".join([c.get("text", "") for c in content if c.get("type") == "text"])
        
        if not content:
            content = ""
        
        if role == "system":
            system_content = content
        elif role == "user":
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
        elif role == "assistant":
            history.append({
                "assistantResponseMessage": {
                    "content": content
                }
            })
    
    # 如果没有用户消息，返回空
    if not user_content:
        user_content = messages[-1].get("content", "") if messages else ""
        if isinstance(user_content, list):
            user_content = " ".join([c.get("text", "") for c in user_content if c.get("type") == "text"])
    
    # 历史不包含最后一条用户消息（它会作为当前输入）
    return user_content, history[:-1] if len(history) > 1 else []


# ==================== Gemini 转换 ====================

def convert_gemini_contents_to_kiro(contents: List[dict], system_instruction: dict, model: str) -> Tuple[str, List[dict]]:
    """将 Gemini 消息格式转换为 Kiro 格式"""
    history = []
    user_content = ""
    
    # 处理 system instruction
    system_text = ""
    if system_instruction:
        parts = system_instruction.get("parts", [])
        system_text = " ".join(p.get("text", "") for p in parts if "text" in p)
    
    for content in contents:
        role = content.get("role", "user")
        parts = content.get("parts", [])
        text = " ".join(p.get("text", "") for p in parts if "text" in p)
        
        if role == "user":
            if system_text and not history:
                text = f"{system_text}\n\n{text}"
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
    
    return user_content, history[:-1] if history else []
