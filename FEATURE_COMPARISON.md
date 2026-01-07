# Kiro Proxy vs ProxyCast 功能对比

## 概述

| 项目 | 技术栈 | 定位 |
|------|--------|------|
| **Kiro Proxy** (本项目) | Python + FastAPI | 轻量级 API 代理 |
| **ProxyCast** | Rust + Tauri + React | 全功能桌面应用 |

---

## ✅ Kiro Proxy 有，ProxyCast 没有的

| 功能 | 说明 |
|------|------|
| **轻量级部署** | 纯 Python，`pip install` + `python run.py` 即可运行 |
| **单文件 Web UI** | HTML 内嵌，无需前端构建 |
| **Gemini 协议原生支持** | `/v1/models/{model}:generateContent` 端点 |
| **Token 计数 API** | `/v1/messages/count_tokens` 端点 |
| **低资源占用** | 无需编译，内存占用小 |

---

## 已实现的 ProxyCast 功能 ✅

### Phase 1: 核心稳定性 (已完成)

| 功能 | 状态 | 说明 |
|------|------|------|
| **Token 自动刷新** | ✅ 已实现 | 检测过期，自动调用 refresh_token API |
| **动态 Machine ID** | ✅ 已实现 | 基于凭证生成唯一指纹 + 时间因子 |
| **配额管理器** | ✅ 已实现 | 429 检测、自动冷却、自动恢复 |
| **凭证状态管理** | ✅ 已实现 | Active/Cooldown/Unhealthy/Disabled |
| **自动账号切换** | ✅ 已实现 | 配额超限时自动切换到下一个可用账号 |
| **凭证文件智能合并** | ✅ 已实现 | 自动合并 clientIdHash 对应文件 |
| **请求重试机制** | ✅ 已实现 | 网络错误/5xx 自动重试，指数退避 |
| **Token 过期预刷新** | ✅ 已实现 | 后台定时检查，提前 15 分钟刷新 |
| **健康检查** | ✅ 已实现 | 定期检测账号可用性，自动标记状态 |
| **请求统计增强** | ✅ 已实现 | 按账号/模型统计，24 小时趋势 |

---

## ❌ 尚未实现的 ProxyCast 功能

### 多 Provider 支持

| Provider | Kiro Proxy | ProxyCast |
|----------|------------|-----------|
| Kiro | ✅ | ✅ |
| Gemini CLI (OAuth) | ❌ | ✅ |
| Gemini API Key | ❌ | ✅ |
| 通义千问 (Qwen) | ❌ | ✅ |
| Vertex AI | ❌ | ✅ |
| Antigravity | ❌ | ✅ |
| Claude Custom | ❌ | ✅ |
| OpenAI Custom | ❌ | ✅ |

### 其他功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| **配置持久化** | ✅ 已实现 | 账号配置保存到 `~/.kiro-proxy/config.json` |
| **IdC 认证支持** | AWS Identity Center (SSO) 认证 | ⭐ 低 |
| **预览模型回退** | 配额超限时切换到 preview 模型 | ⭐ 低 |
| **远程管理 API** | `/v0/management/*` 远程配置管理 | ⭐ 低 |
| **Per-Key 代理** | 每个凭证可单独配置 HTTP 代理 | ⭐ 低 |
| **桌面 GUI** | Tauri 跨平台桌面应用 | ⭐ 低 |

---

## 🔑 Kiro 实现细节对比

| 特性 | Kiro Proxy | ProxyCast |
|------|------------|-----------|
| **Machine ID** | ✅ 基于凭证动态生成 + 时间因子 | 基于凭证动态生成 + 时间因子 |
| **Token 刷新** | ✅ 自动检测过期并刷新 | 自动检测过期并刷新 |
| **认证方式** | Social (IdC 部分支持) | Social + IdC (SSO) |
| **凭证文件处理** | ✅ 智能合并 clientIdHash 文件 | 智能合并 clientIdHash 文件 |
| **错误处理** | ✅ 详细分类 + 自动重试 | 详细分类 + 友好提示 |
| **User-Agent** | ✅ 完整模拟 Kiro IDE | 完整模拟 Kiro IDE |
| **Kiro 版本号** | ✅ 自动检测本地 Kiro.app | 自动检测本地 Kiro.app |

---

## 📋 新增 API 端点

### 账号管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/accounts` | GET | 获取所有账号状态（增强版） |
| `/api/accounts/{id}` | GET | 获取账号详细信息 |
| `/api/accounts/{id}/refresh` | POST | 刷新指定账号的 token |
| `/api/accounts/{id}/restore` | POST | 恢复账号（从冷却状态） |
| `/api/accounts/refresh-all` | POST | 刷新所有即将过期的 token |

### 配额管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/quota` | GET | 获取配额状态（冷却中的账号等） |

---

## 参考资源

- ProxyCast Kiro Provider: `proxycast/src-tauri/src/providers/kiro.rs`
- ProxyCast 配额管理: `proxycast/src-tauri/src/credential/quota.rs`
- ProxyCast 凭证池: `proxycast/src-tauri/src/credential/pool.rs`

---

## 项目结构 (v1.3.0)

```
kiro_proxy/
├── __init__.py
├── main.py                    # FastAPI 应用入口
├── config.py                  # 全局配置
├── converters.py              # 协议转换
├── kiro_api.py                # 兼容层（调用 providers/kiro.py）
├── models.py                  # 兼容层（调用 core/）
│
├── core/                      # 核心模块
│   ├── __init__.py
│   ├── account.py            # 账号管理
│   └── state.py              # 全局状态、请求日志
│
├── credential/                # 凭证管理
│   ├── __init__.py
│   ├── types.py              # KiroCredentials, CredentialStatus
│   ├── fingerprint.py        # Machine ID 生成
│   ├── quota.py              # 配额管理器
│   └── refresher.py          # Token 刷新
│
├── providers/                 # Provider 抽象
│   ├── __init__.py
│   ├── base.py               # BaseProvider 基类
│   └── kiro.py               # Kiro Provider
│
├── handlers/                  # API 处理器
│   ├── anthropic.py          # /v1/messages
│   ├── openai.py             # /v1/chat/completions
│   ├── gemini.py             # /v1/models/{model}:generateContent
│   └── admin.py              # 管理 API
│
└── web/
    └── html.py               # Web UI
```

### 扩展指南

**添加新 Provider（如 Gemini OAuth）：**
1. 创建 `providers/gemini.py`，继承 `BaseProvider`
2. 实现 `build_headers`、`build_request`、`parse_response`、`refresh_token`
3. 在 `handlers/` 中使用新 Provider
