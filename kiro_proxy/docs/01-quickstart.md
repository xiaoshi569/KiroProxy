# 快速开始

## 安装运行

### 方式一：下载预编译版本

从 [Releases](https://github.com/yourname/kiro-proxy/releases) 下载对应平台的安装包：

- **Windows**: `kiro-proxy-windows.zip`
- **macOS**: `kiro-proxy-macos.zip`
- **Linux**: `kiro-proxy-linux.tar.gz`

解压后双击运行即可。

### 方式二：从源码运行

```bash
# 克隆项目
git clone https://github.com/yourname/kiro-proxy.git
cd kiro-proxy

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行（默认端口 8080）
python run.py

# 指定端口
python run.py 8081
```

启动成功后，访问 http://localhost:8080 打开管理界面。

---

## 获取 Kiro 账号

Kiro Proxy 需要 Kiro 账号的 Token 才能工作。有两种方式获取：

### 方式一：在线登录（推荐）

1. 打开 Web UI，点击「账号」标签页
2. 点击「在线登录」按钮
3. 选择登录方式：
   - **Google** - 使用 Google 账号
   - **GitHub** - 使用 GitHub 账号
   - **AWS** - 使用 AWS Builder ID
4. 在弹出的浏览器中完成授权
5. 授权成功后，账号自动添加到代理

### 方式二：扫描本地 Token

如果你已经在 Kiro IDE 中登录过：

1. 打开 Kiro IDE，确保已登录
2. 回到 Web UI，点击「扫描 Token」
3. 系统会扫描 `~/.aws/sso/cache/` 目录
4. 选择要添加的 Token 文件

---

## 配置 AI 客户端

### Claude Code (VSCode 插件)

这是最推荐的使用方式，工具调用功能已验证可用。

1. 安装 Claude Code 插件
2. 打开设置，添加自定义 Provider：

```
名称: Kiro Proxy
API Provider: Anthropic
API Key: any（随便填一个）
Base URL: http://localhost:8080
模型: claude-sonnet-4
```

3. 选择 Kiro Proxy 作为当前 Provider

### Codex CLI

OpenAI 官方命令行工具。

```bash
# 安装
npm install -g @openai/codex

# 配置 (~/.codex/config.toml)
model = "gpt-4o"
model_provider = "kiro"

[model_providers.kiro]
name = "Kiro Proxy"
base_url = "http://localhost:8080/v1"
```

### Gemini CLI

```bash
# 设置环境变量
export GEMINI_API_BASE=http://localhost:8080/v1

# 或在配置文件中设置
base_url = "http://localhost:8080/v1"
model = "gemini-pro"
```

### 其他兼容客户端

任何支持 OpenAI 或 Anthropic API 的客户端都可以使用：

- **Base URL**: `http://localhost:8080` 或 `http://localhost:8080/v1`
- **API Key**: 任意值（代理不验证）
- **模型**: 见模型对照表
