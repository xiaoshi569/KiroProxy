"""管理 API 处理"""
import json
import uuid
import time
import httpx
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from fastapi import Request, HTTPException, Query

from ..config import TOKEN_PATH, MODELS_URL
from ..core import state, Account, stats_manager
from ..credential import quota_manager, generate_machine_id, get_kiro_version, CredentialStatus


async def get_status():
    """服务状态"""
    try:
        with open(TOKEN_PATH) as f:
            data = json.load(f)
        return {
            "ok": True,
            "expires": data.get("expiresAt"),
            "stats": state.get_stats()
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "stats": state.get_stats()}


async def get_stats():
    """获取统计信息"""
    return state.get_stats()


async def get_logs(limit: int = Query(100, le=1000)):
    """获取请求日志"""
    logs = list(state.request_logs)[-limit:]
    return {
        "logs": [asdict(log) for log in reversed(logs)],
        "total": len(state.request_logs)
    }


async def get_accounts():
    """获取账号列表（增强版）"""
    return {
        "accounts": state.get_accounts_status()
    }


async def get_account_detail(account_id: str):
    """获取账号详细信息"""
    for acc in state.accounts:
        if acc.id == account_id:
            creds = acc.get_credentials()
            return {
                "id": acc.id,
                "name": acc.name,
                "enabled": acc.enabled,
                "status": acc.status.value,
                "available": acc.is_available(),
                "request_count": acc.request_count,
                "error_count": acc.error_count,
                "last_used": acc.last_used,
                "token_path": acc.token_path,
                "machine_id": acc.get_machine_id()[:16] + "...",
                "credentials": {
                    "has_access_token": bool(creds and creds.access_token),
                    "has_refresh_token": bool(creds and creds.refresh_token),
                    "has_client_id": bool(creds and creds.client_id),
                    "auth_method": creds.auth_method if creds else None,
                    "region": creds.region if creds else None,
                    "expires_at": creds.expires_at if creds else None,
                    "is_expired": acc.is_token_expired(),
                    "is_expiring_soon": acc.is_token_expiring_soon(),
                } if creds else None,
                "cooldown": {
                    "is_cooldown": not quota_manager.is_available(acc.id),
                    "remaining_seconds": quota_manager.get_cooldown_remaining(acc.id),
                }
            }
    raise HTTPException(404, "Account not found")


async def add_account(request: Request):
    """添加账号"""
    body = await request.json()
    name = body.get("name", f"账号{len(state.accounts)+1}")
    token_path = body.get("token_path")
    
    if not token_path or not Path(token_path).exists():
        raise HTTPException(400, "Invalid token path")
    
    account = Account(
        id=uuid.uuid4().hex[:8],
        name=name,
        token_path=token_path
    )
    state.accounts.append(account)
    
    # 预加载凭证
    account.load_credentials()
    
    # 保存配置
    state._save_accounts()
    
    return {"ok": True, "account_id": account.id}


async def delete_account(account_id: str):
    """删除账号"""
    state.accounts = [a for a in state.accounts if a.id != account_id]
    # 清理配额记录
    quota_manager.restore(account_id)
    # 保存配置
    state._save_accounts()
    return {"ok": True}


async def toggle_account(account_id: str):
    """启用/禁用账号"""
    for acc in state.accounts:
        if acc.id == account_id:
            acc.enabled = not acc.enabled
            # 保存配置
            state._save_accounts()
            return {"ok": True, "enabled": acc.enabled}
    raise HTTPException(404, "Account not found")


async def refresh_account_token(account_id: str):
    """刷新指定账号的 token"""
    success, message = await state.refresh_account_token(account_id)
    return {"ok": success, "message": message}


async def refresh_all_tokens():
    """刷新所有即将过期的 token"""
    results = await state.refresh_expiring_tokens()
    return {
        "ok": True,
        "results": results,
        "refreshed": len([r for r in results if r["success"]])
    }


async def restore_account(account_id: str):
    """恢复账号（从冷却状态）"""
    restored = quota_manager.restore(account_id)
    if restored:
        for acc in state.accounts:
            if acc.id == account_id:
                from ..credential import CredentialStatus
                acc.status = CredentialStatus.ACTIVE
                break
    return {"ok": restored}


async def speedtest():
    """测试 API 延迟"""
    account = state.get_available_account()
    if not account:
        return {"ok": False, "error": "No available account"}
    
    start = time.time()
    try:
        token = account.get_token()
        machine_id = account.get_machine_id()
        kiro_version = get_kiro_version()
        
        headers = {
            "content-type": "application/json",
            "x-amz-user-agent": f"aws-sdk-js/1.0.0 KiroIDE-{kiro_version}-{machine_id}",
            "Authorization": f"Bearer {token}",
        }
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            resp = await client.get(MODELS_URL, headers=headers, params={"origin": "AI_EDITOR"})
            latency = (time.time() - start) * 1000
            return {
                "ok": resp.status_code == 200,
                "latency_ms": round(latency, 2),
                "status": resp.status_code,
                "account_id": account.id
            }
    except Exception as e:
        return {"ok": False, "error": str(e), "latency_ms": (time.time() - start) * 1000}


async def scan_tokens():
    """扫描系统中的 Kiro token 文件"""
    found = []
    sso_cache = Path.home() / ".aws/sso/cache"
    if sso_cache.exists():
        for f in sso_cache.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    if "accessToken" in data:
                        # 检查是否已添加
                        already_added = any(a.token_path == str(f) for a in state.accounts)
                        
                        found.append({
                            "path": str(f),
                            "name": f.stem,
                            "expires": data.get("expiresAt"),
                            "auth_method": data.get("authMethod", "social"),
                            "region": data.get("region", "us-east-1"),
                            "has_refresh_token": "refreshToken" in data,
                            "already_added": already_added
                        })
            except:
                pass
    return {"tokens": found}


async def add_from_scan(request: Request):
    """从扫描结果添加账号"""
    body = await request.json()
    token_path = body.get("path")
    name = body.get("name", "扫描账号")
    
    if not token_path or not Path(token_path).exists():
        raise HTTPException(400, "Token 文件不存在")
    
    if any(a.token_path == token_path for a in state.accounts):
        raise HTTPException(400, "该账号已添加")
    
    try:
        with open(token_path) as f:
            data = json.load(f)
            if "accessToken" not in data:
                raise HTTPException(400, "无效的 token 文件")
    except json.JSONDecodeError:
        raise HTTPException(400, "无效的 JSON 文件")
    
    account = Account(
        id=uuid.uuid4().hex[:8],
        name=name,
        token_path=token_path
    )
    state.accounts.append(account)
    
    # 预加载凭证
    account.load_credentials()
    
    # 保存配置
    state._save_accounts()
    
    return {"ok": True, "account_id": account.id}


async def export_config():
    """导出配置"""
    return {
        "accounts": [
            {"name": a.name, "token_path": a.token_path, "enabled": a.enabled}
            for a in state.accounts
        ],
        "exported_at": datetime.now().isoformat()
    }


async def import_config(request: Request):
    """导入配置"""
    body = await request.json()
    accounts = body.get("accounts", [])
    imported = 0
    
    for acc_data in accounts:
        token_path = acc_data.get("token_path", "")
        if Path(token_path).exists():
            if not any(a.token_path == token_path for a in state.accounts):
                account = Account(
                    id=uuid.uuid4().hex[:8],
                    name=acc_data.get("name", "导入账号"),
                    token_path=token_path,
                    enabled=acc_data.get("enabled", True)
                )
                state.accounts.append(account)
                account.load_credentials()
                imported += 1
    
    # 保存配置
    state._save_accounts()
    
    return {"ok": True, "imported": imported}


async def refresh_token_check():
    """检查所有账号的 token 状态"""
    results = []
    for acc in state.accounts:
        creds = acc.get_credentials()
        if creds:
            results.append({
                "id": acc.id,
                "name": acc.name,
                "valid": not acc.is_token_expired(),
                "expiring_soon": acc.is_token_expiring_soon(),
                "expires": creds.expires_at,
                "auth_method": creds.auth_method,
                "has_refresh_token": bool(creds.refresh_token),
            })
        else:
            results.append({
                "id": acc.id,
                "name": acc.name,
                "valid": False,
                "error": "无法加载凭证"
            })
    
    return {"accounts": results}


async def get_quota_status():
    """获取配额状态"""
    return {
        "cooldown_seconds": quota_manager.cooldown_seconds,
        "exceeded_count": len(quota_manager.exceeded_records),
        "exceeded_credentials": [
            {
                "credential_id": r.credential_id,
                "exceeded_at": r.exceeded_at,
                "cooldown_until": r.cooldown_until,
                "remaining_seconds": max(0, int(r.cooldown_until - time.time())),
                "reason": r.reason
            }
            for r in quota_manager.exceeded_records.values()
        ]
    }


async def get_kiro_login_url():
    """获取 Kiro 登录说明"""
    return {
        "message": "Kiro 使用 AWS Identity Center 认证，无法直接 OAuth",
        "instructions": [
            "1. 打开 Kiro IDE",
            "2. 点击登录按钮，使用 Google/GitHub 账号登录",
            "3. 登录成功后，token 会自动保存到 ~/.aws/sso/cache/",
            "4. 本代理会自动读取该 token"
        ],
        "token_path": str(TOKEN_PATH),
        "token_exists": TOKEN_PATH.exists()
    }


async def get_detailed_stats():
    """获取详细统计信息"""
    basic_stats = state.get_stats()
    detailed = stats_manager.get_all_stats()
    
    return {
        **basic_stats,
        "detailed": detailed
    }


async def run_health_check():
    """手动触发健康检查"""
    results = []
    
    for acc in state.accounts:
        if not acc.enabled:
            results.append({
                "id": acc.id,
                "name": acc.name,
                "status": "disabled",
                "healthy": False
            })
            continue
        
        try:
            token = acc.get_token()
            if not token:
                acc.status = CredentialStatus.UNHEALTHY
                results.append({
                    "id": acc.id,
                    "name": acc.name,
                    "status": "no_token",
                    "healthy": False
                })
                continue
            
            headers = {
                "Authorization": f"Bearer {token}",
                "content-type": "application/json"
            }
            
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.get(
                    MODELS_URL,
                    headers=headers,
                    params={"origin": "AI_EDITOR"}
                )
                
                if resp.status_code == 200:
                    if acc.status == CredentialStatus.UNHEALTHY:
                        acc.status = CredentialStatus.ACTIVE
                    results.append({
                        "id": acc.id,
                        "name": acc.name,
                        "status": "healthy",
                        "healthy": True,
                        "latency_ms": resp.elapsed.total_seconds() * 1000
                    })
                elif resp.status_code == 401:
                    acc.status = CredentialStatus.UNHEALTHY
                    results.append({
                        "id": acc.id,
                        "name": acc.name,
                        "status": "auth_failed",
                        "healthy": False
                    })
                elif resp.status_code == 429:
                    results.append({
                        "id": acc.id,
                        "name": acc.name,
                        "status": "rate_limited",
                        "healthy": True  # 限流不代表不健康
                    })
                else:
                    results.append({
                        "id": acc.id,
                        "name": acc.name,
                        "status": f"error_{resp.status_code}",
                        "healthy": False
                    })
                    
        except Exception as e:
            results.append({
                "id": acc.id,
                "name": acc.name,
                "status": "error",
                "healthy": False,
                "error": str(e)
            })
    
    healthy_count = len([r for r in results if r["healthy"]])
    return {
        "ok": True,
        "total": len(results),
        "healthy": healthy_count,
        "unhealthy": len(results) - healthy_count,
        "results": results
    }
