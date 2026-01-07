"""智谱 GLM API 集成 (chatglm.cn)

用于 AI 助手功能，调用免费的 GLM-4.7 模型
"""
import uuid
import time
import hashlib
import httpx
from typing import Optional
from dataclasses import dataclass


# 智谱国内版密钥
CN_SECRET = '8a1317a7468aa3ad86e997d08f3f31cb'

# Token 缓存
@dataclass
class TokenCache:
    access_token: Optional[str] = None
    device_id: Optional[str] = None
    expires_at: int = 0


_token_cache = TokenCache()


def generate_timestamp() -> str:
    """生成带校验位的时间戳"""
    now = str(int(time.time() * 1000))
    digits = [int(d) for d in now]
    total = sum(digits)
    check_digit = (total - digits[-2]) % 10
    return now[:-2] + str(check_digit) + now[-1]


def generate_nonce() -> str:
    """生成 32 位 nonce"""
    return uuid.uuid4().hex


def create_sign(timestamp: str, nonce: str) -> str:
    """生成 MD5 签名"""
    data = f"{timestamp}-{nonce}-{CN_SECRET}"
    return hashlib.md5(data.encode()).hexdigest()


def generate_request_id() -> str:
    """生成请求 ID"""
    return uuid.uuid4().hex


async def get_cn_token() -> TokenCache:
    """获取智谱国内版 Token"""
    global _token_cache
    
    # 检查缓存是否有效（提前 5 分钟刷新）
    if _token_cache.access_token and time.time() * 1000 < _token_cache.expires_at - 300000:
        return _token_cache
    
    device_id = _token_cache.device_id or uuid.uuid4().hex
    timestamp = generate_timestamp()
    nonce = generate_nonce()
    sign = create_sign(timestamp, nonce)
    request_id = generate_request_id()
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': 'https://chatglm.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'app-name': 'chatglm',
        'x-app-platform': 'pc',
        'x-app-version': '0.0.1',
        'x-device-id': device_id,
        'x-lang': 'zh',
        'x-nonce': nonce,
        'x-request-id': request_id,
        'x-sign': sign,
        'x-timestamp': timestamp,
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            'https://chatglm.cn/chatglm/user-api/guest/access',
            headers=headers,
        )
        data = resp.json()
        
        if data.get('status') != 0:
            raise Exception(f"获取 Token 失败: {data.get('message')}")
        
        access_token = data['result']['access_token']
        # 解析 JWT 获取过期时间
        import base64
        import json
        payload = access_token.split('.')[1]
        # 补齐 base64 padding
        payload += '=' * (4 - len(payload) % 4)
        payload_data = json.loads(base64.b64decode(payload))
        expires_at = payload_data.get('exp', 0) * 1000
        
        _token_cache = TokenCache(
            access_token=access_token,
            device_id=device_id,
            expires_at=expires_at
        )
        
        return _token_cache


async def chat_with_glm(
    messages: list,
    model: str = 'glm-4.7',
) -> str:
    """
    调用智谱 GLM API
    
    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}]
        model: 模型名称
    
    Returns:
        完整回复文本
    """
    token_info = await get_cn_token()
    
    timestamp = generate_timestamp()
    nonce = generate_nonce()
    sign = create_sign(timestamp, nonce)
    request_id = generate_request_id()
    
    headers = {
        'Accept': 'text/event-stream',
        'Content-Type': 'application/json',
        'Origin': 'https://chatglm.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Authorization': f'Bearer {token_info.access_token}',
        'app-name': 'chatglm',
        'x-app-platform': 'pc',
        'x-app-version': '0.0.1',
        'x-device-id': token_info.device_id,
        'x-lang': 'zh',
        'x-nonce': nonce,
        'x-request-id': request_id,
        'x-sign': sign,
        'x-timestamp': timestamp,
    }
    
    # 转换消息格式，将 system 消息合并到第一条 user 消息
    cn_messages = []
    system_content = ''
    
    for m in messages:
        role = m.get('role', 'user')
        content = m.get('content', '')
        if isinstance(content, list):
            content = ' '.join([c.get('text', '') for c in content if c.get('type') == 'text'])
        
        if role == 'system':
            system_content = content
        elif role == 'user':
            # 如果有 system 消息，合并到第一条 user 消息
            if system_content and not cn_messages:
                content = f"[系统指令]\n{system_content}\n\n[用户问题]\n{content}"
                system_content = ''
            cn_messages.append({
                'role': 'user',
                'content': [{'type': 'text', 'text': content}]
            })
        elif role == 'assistant':
            cn_messages.append({
                'role': 'assistant',
                'content': [{'type': 'text', 'text': content}]
            })
    
    body = {
        'assistant_id': '65940acff94777010aa6b796',
        'conversation_id': '',
        'project_id': '',
        'chat_type': 'user_chat',
        'meta_data': {
            'cogview': {'rm_label_watermark': False},
            'is_test': False,
            'input_question_type': 'xxxx',
            'channel': '',
            'draft_id': '',
            'chat_mode': 'zero',
            'is_networking': False,
            'quote_log_id': '',
            'platform': 'pc'
        },
        'messages': cn_messages
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            'https://chatglm.cn/chatglm/backend-api/assistant/stream',
            headers=headers,
            json=body,
        )
        
        if resp.status_code != 200:
            raise Exception(f"API 请求失败: {resp.status_code}")
        
        # 解析 SSE 流
        full_content = ''
        for line in resp.text.split('\n'):
            if line.startswith('data:'):
                try:
                    import json
                    data = json.loads(line[5:].strip())
                    parts = data.get('parts', [])
                    if parts and parts[0].get('content'):
                        content_list = parts[0]['content']
                        if content_list and content_list[0].get('text'):
                            full_content = content_list[0]['text']
                except:
                    pass
        
        return full_content


async def glm_chat_completions(messages: list, model: str = 'glm-4.7') -> dict:
    """
    OpenAI 兼容的 chat completions 接口
    
    Returns:
        OpenAI 格式的响应
    """
    try:
        content = await chat_with_glm(messages, model)
        
        return {
            'id': f'chatcmpl-{uuid.uuid4().hex[:8]}',
            'object': 'chat.completion',
            'created': int(time.time()),
            'model': model,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': content
                },
                'finish_reason': 'stop'
            }],
            'usage': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        }
    except Exception as e:
        return {
            'error': {
                'message': str(e),
                'type': 'api_error'
            }
        }
