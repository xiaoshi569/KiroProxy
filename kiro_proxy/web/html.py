"""Web UI - 组件化单文件结构"""

# ==================== CSS 样式 ====================
CSS_BASE = '''
* { margin: 0; padding: 0; box-sizing: border-box; }
:root { --bg: #fafafa; --card: #fff; --border: #e5e5e5; --text: #1a1a1a; --muted: #666; --accent: #000; --success: #22c55e; --error: #ef4444; --warn: #f59e0b; --info: #3b82f6; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #0a0a0a; --card: #141414; --border: #262626; --text: #fafafa; --muted: #a3a3a3; --accent: #fff; }
}
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
.container { max-width: 1100px; margin: 0 auto; padding: 2rem 1rem; }
'''

CSS_LAYOUT = '''
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border); }
h1 { font-size: 1.5rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; }
h1 img { width: 28px; height: 28px; }
.status { font-size: 0.875rem; color: var(--muted); display: flex; align-items: center; gap: 1rem; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.ok { background: var(--success); }
.status-dot.err { background: var(--error); }
.tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.tab { padding: 0.5rem 1rem; border: 1px solid var(--border); background: var(--card); cursor: pointer; font-size: 0.875rem; transition: all 0.2s; border-radius: 6px; }
.tab.active { background: var(--accent); color: var(--bg); border-color: var(--accent); }
.panel { display: none; }
.panel.active { display: block; }
.footer { text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); }
'''

CSS_COMPONENTS = '''
.card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; }
.card h3 { font-size: 1rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
.stat-item { text-align: center; padding: 1rem; background: var(--bg); border-radius: 6px; }
.stat-value { font-size: 1.5rem; font-weight: 600; }
.stat-label { font-size: 0.75rem; color: var(--muted); }
.badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
.badge.success { background: #dcfce7; color: #166534; }
.badge.error { background: #fee2e2; color: #991b1b; }
.badge.warn { background: #fef3c7; color: #92400e; }
.badge.info { background: #dbeafe; color: #1e40af; }
@media (prefers-color-scheme: dark) {
  .badge.success { background: #14532d; color: #86efac; }
  .badge.error { background: #7f1d1d; color: #fca5a5; }
  .badge.warn { background: #78350f; color: #fde68a; }
  .badge.info { background: #1e3a5f; color: #93c5fd; }
}
'''

CSS_FORMS = '''
.input-row { display: flex; gap: 0.5rem; }
.input-row input, .input-row select { flex: 1; padding: 0.75rem 1rem; border: 1px solid var(--border); border-radius: 6px; background: var(--card); color: var(--text); font-size: 1rem; }
button { padding: 0.75rem 1.5rem; background: var(--accent); color: var(--bg); border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: opacity 0.2s; }
button:hover { opacity: 0.8; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
button.secondary { background: var(--card); color: var(--text); border: 1px solid var(--border); }
button.small { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
select { padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px; background: var(--card); color: var(--text); }
pre { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 1rem; overflow-x: auto; font-size: 0.8rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }
th { font-weight: 500; color: var(--muted); }
'''

CSS_ACCOUNTS = '''
.account-card { border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; background: var(--card); }
.account-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.account-name { font-weight: 500; display: flex; align-items: center; gap: 0.5rem; }
.account-meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.5rem; font-size: 0.8rem; color: var(--muted); }
.account-meta-item { display: flex; justify-content: space-between; padding: 0.25rem 0; }
.account-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border); }
'''

CSS_API = '''
.endpoint { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.method { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
.method.get { background: #dcfce7; color: #166534; }
.method.post { background: #fef3c7; color: #92400e; }
@media (prefers-color-scheme: dark) {
  .method.get { background: #14532d; color: #86efac; }
  .method.post { background: #78350f; color: #fde68a; }
}
.copy-btn { padding: 0.25rem 0.5rem; font-size: 0.75rem; background: var(--card); border: 1px solid var(--border); color: var(--text); }
'''

CSS_DOCS = '''
.docs-container { display: flex; gap: 1.5rem; min-height: 500px; }
.docs-nav { width: 200px; flex-shrink: 0; }
.docs-nav-item { display: block; padding: 0.5rem 0.75rem; margin-bottom: 0.25rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; color: var(--text); text-decoration: none; transition: background 0.2s; }
.docs-nav-item:hover { background: var(--bg); }
.docs-nav-item.active { background: var(--accent); color: var(--bg); }
.docs-content { flex: 1; min-width: 0; }
.docs-content h1 { font-size: 1.5rem; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }
.docs-content h2 { font-size: 1.25rem; margin: 1.5rem 0 0.75rem; color: var(--text); }
.docs-content h3 { font-size: 1rem; margin: 1rem 0 0.5rem; color: var(--text); }
.docs-content h4 { font-size: 0.9rem; margin: 0.75rem 0 0.5rem; color: var(--muted); }
.docs-content p { margin: 0.5rem 0; }
.docs-content ul, .docs-content ol { margin: 0.5rem 0; padding-left: 1.5rem; }
.docs-content li { margin: 0.25rem 0; }
.docs-content code { background: var(--bg); padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.9em; }
.docs-content pre { margin: 0.75rem 0; }
.docs-content pre code { background: none; padding: 0; }
.docs-content table { margin: 0.75rem 0; }
.docs-content blockquote { margin: 0.75rem 0; padding: 0.5rem 1rem; border-left: 3px solid var(--border); color: var(--muted); background: var(--bg); border-radius: 0 6px 6px 0; }
.docs-content hr { margin: 1.5rem 0; border: none; border-top: 1px solid var(--border); }
.docs-content a { color: var(--info); text-decoration: none; }
.docs-content a:hover { text-decoration: underline; }
@media (max-width: 768px) {
  .docs-container { flex-direction: column; }
  .docs-nav { width: 100%; display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .docs-nav-item { margin-bottom: 0; }
}
'''

CSS_STYLES = CSS_BASE + CSS_LAYOUT + CSS_COMPONENTS + CSS_FORMS + CSS_ACCOUNTS + CSS_API + CSS_DOCS


# ==================== HTML 模板 ====================
HTML_HEADER = '''
<header>
  <h1><img src="/assets/icon.svg" alt="Kiro">Kiro API Proxy</h1>
  <div class="status">
    <span class="status-dot" id="statusDot"></span>
    <span id="statusText">检查中...</span>
    <span id="uptime"></span>
  </div>
</header>

<div class="tabs">
  <div class="tab active" data-tab="help">帮助</div>
  <div class="tab" data-tab="flows">流量</div>
  <div class="tab" data-tab="monitor">监控</div>
  <div class="tab" data-tab="accounts">账号</div>
  <div class="tab" data-tab="logs">日志</div>
  <div class="tab" data-tab="api">API</div>
</div>
'''

HTML_HELP = '''
<div class="panel active" id="help">
  <div class="card" style="padding:1rem">
    <div class="docs-container">
      <nav class="docs-nav" id="docsNav"></nav>
      <div class="docs-content" id="docsContent">
        <p style="color:var(--muted)">加载中...</p>
      </div>
    </div>
  </div>
</div>
'''

HTML_FLOWS = '''
<div class="panel" id="flows">
  <div class="card">
    <h3>Flow 统计 <button class="secondary small" onclick="loadFlowStats()">刷新</button></h3>
    <div class="stats-grid" id="flowStatsGrid"></div>
  </div>
  <div class="card">
    <h3>流量监控</h3>
    <div style="display:flex;gap:0.5rem;margin-bottom:1rem;flex-wrap:wrap">
      <select id="flowProtocol" onchange="loadFlows()">
        <option value="">全部协议</option>
        <option value="anthropic">Anthropic</option>
        <option value="openai">OpenAI</option>
        <option value="gemini">Gemini</option>
      </select>
      <select id="flowState" onchange="loadFlows()">
        <option value="">全部状态</option>
        <option value="completed">完成</option>
        <option value="error">错误</option>
        <option value="streaming">流式中</option>
        <option value="pending">等待中</option>
      </select>
      <input type="text" id="flowSearch" placeholder="搜索内容..." style="flex:1;min-width:150px" onkeydown="if(event.key==='Enter')loadFlows()">
      <button class="secondary" onclick="loadFlows()">搜索</button>
      <button class="secondary" onclick="exportFlows()">导出</button>
    </div>
    <div id="flowList"></div>
  </div>
  <div class="card" id="flowDetail" style="display:none">
    <h3>Flow 详情 <button class="secondary small" onclick="$('#flowDetail').style.display='none'">关闭</button></h3>
    <div id="flowDetailContent"></div>
  </div>
</div>
'''

HTML_MONITOR = '''
<div class="panel" id="monitor">
  <div class="card">
    <h3>服务状态 <button class="secondary small" onclick="loadStats()">刷新</button></h3>
    <div class="stats-grid" id="statsGrid"></div>
  </div>
  <div class="card">
    <h3>配额状态</h3>
    <div id="quotaStatus"></div>
  </div>
  <div class="card">
    <h3>速度测试</h3>
    <button onclick="runSpeedtest()" id="speedtestBtn">开始测试</button>
    <span id="speedtestResult" style="margin-left:1rem"></span>
  </div>
</div>
'''


HTML_ACCOUNTS = '''
<div class="panel" id="accounts">
  <div class="card">
    <h3>账号管理</h3>
    <div style="display:flex;gap:0.5rem;margin-bottom:1rem;flex-wrap:wrap">
      <button onclick="showLoginOptions()">在线登录</button>
      <button class="secondary" onclick="scanTokens()">扫描 Token</button>
      <button class="secondary" onclick="showAddAccount()">手动添加</button>
      <button class="secondary" onclick="refreshAllTokens()">刷新所有 Token</button>
      <button class="secondary" onclick="checkTokens()">检查有效期</button>
    </div>
    <div id="accountList"></div>
  </div>
  <div class="card" id="loginOptions" style="display:none">
    <h3>选择登录方式 <button class="secondary small" onclick="$('#loginOptions').style.display='none'">关闭</button></h3>
    <div style="margin-bottom:1rem">
      <label style="display:flex;align-items:center;gap:0.5rem;cursor:pointer">
        <input type="checkbox" id="incognitoMode"> 无痕/隐私模式打开
      </label>
    </div>
    <div style="margin-bottom:1rem">
      <p style="color:var(--muted);font-size:0.875rem;margin-bottom:0.5rem">选择浏览器：</p>
      <div id="browserList" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:0.5rem;margin-bottom:1rem"></div>
    </div>
    <div>
      <p style="color:var(--muted);font-size:0.875rem;margin-bottom:0.5rem">选择登录方式：</p>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem">
        <button class="secondary" onclick="startSocialLogin('google')" style="display:flex;align-items:center;justify-content:center;gap:0.5rem">
          <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
          Google
        </button>
        <button class="secondary" onclick="startSocialLogin('github')" style="display:flex;align-items:center;justify-content:center;gap:0.5rem">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
          GitHub
        </button>
        <button class="secondary" onclick="startAwsLogin()" style="display:flex;align-items:center;justify-content:center;gap:0.5rem">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#FF9900"><path d="M6.763 10.036c0 .296.032.535.088.71.064.176.144.368.256.576.04.063.056.127.056.183 0 .08-.048.16-.152.24l-.503.335a.383.383 0 0 1-.208.072c-.08 0-.16-.04-.239-.112a2.47 2.47 0 0 1-.287-.375 6.18 6.18 0 0 1-.248-.471c-.622.734-1.405 1.101-2.347 1.101-.67 0-1.205-.191-1.596-.574-.391-.384-.59-.894-.59-1.533 0-.678.239-1.23.726-1.644.487-.415 1.133-.623 1.955-.623.272 0 .551.024.846.064.296.04.6.104.918.176v-.583c0-.607-.127-1.03-.375-1.277-.255-.248-.686-.367-1.3-.367-.28 0-.568.031-.863.103-.296.072-.583.16-.862.272a2.287 2.287 0 0 1-.28.104.488.488 0 0 1-.127.023c-.112 0-.168-.08-.168-.247v-.391c0-.128.016-.224.056-.28a.597.597 0 0 1 .224-.167c.279-.144.614-.264 1.005-.36a4.84 4.84 0 0 1 1.246-.151c.95 0 1.644.216 2.091.647.439.43.662 1.085.662 1.963v2.586zm-3.24 1.214c.263 0 .534-.048.822-.144.287-.096.543-.271.758-.51.128-.152.224-.32.272-.512.047-.191.08-.423.08-.694v-.335a6.66 6.66 0 0 0-.735-.136 6.02 6.02 0 0 0-.75-.048c-.535 0-.926.104-1.19.32-.263.215-.39.518-.39.917 0 .375.095.655.295.846.191.2.47.296.838.296zm6.41.862c-.144 0-.24-.024-.304-.08-.064-.048-.12-.16-.168-.311L7.586 5.55a1.398 1.398 0 0 1-.072-.32c0-.128.064-.2.191-.2h.783c.151 0 .255.025.31.08.065.048.113.16.16.312l1.342 5.284 1.245-5.284c.04-.16.088-.264.151-.312a.549.549 0 0 1 .32-.08h.638c.152 0 .256.025.32.08.063.048.12.16.151.312l1.261 5.348 1.381-5.348c.048-.16.104-.264.16-.312a.52.52 0 0 1 .311-.08h.743c.127 0 .2.065.2.2 0 .04-.009.08-.017.128a1.137 1.137 0 0 1-.056.2l-1.923 6.17c-.048.16-.104.263-.168.311a.51.51 0 0 1-.303.08h-.687c-.151 0-.255-.024-.32-.08-.063-.056-.119-.16-.15-.32l-1.238-5.148-1.23 5.14c-.04.16-.087.264-.15.32-.065.056-.177.08-.32.08zm10.256.215c-.415 0-.83-.048-1.229-.143-.399-.096-.71-.2-.918-.32-.128-.071-.215-.151-.247-.223a.563.563 0 0 1-.048-.224v-.407c0-.167.064-.247.183-.247.048 0 .096.008.144.024.048.016.12.048.2.08.271.12.566.215.878.279.319.064.63.096.95.096.502 0 .894-.088 1.165-.264a.86.86 0 0 0 .415-.758.777.777 0 0 0-.215-.559c-.144-.151-.416-.287-.807-.415l-1.157-.36c-.583-.183-1.014-.454-1.277-.813a1.902 1.902 0 0 1-.4-1.158c0-.335.073-.63.216-.886.144-.255.335-.479.575-.654.24-.184.51-.32.83-.415.32-.096.655-.136 1.006-.136.175 0 .359.008.535.032.183.024.35.056.518.088.16.04.312.08.455.127.144.048.256.096.336.144a.69.69 0 0 1 .24.2.43.43 0 0 1 .071.263v.375c0 .168-.064.256-.184.256a.83.83 0 0 1-.303-.096 3.652 3.652 0 0 0-1.532-.311c-.455 0-.815.071-1.062.223-.248.152-.375.383-.375.71 0 .224.08.416.24.567.159.152.454.304.877.44l1.134.358c.574.184.99.44 1.237.767.247.327.367.702.367 1.117 0 .343-.072.655-.207.926-.144.272-.336.511-.583.703-.248.2-.543.343-.886.447-.36.111-.734.167-1.142.167zM21.698 16.207c-2.626 1.94-6.442 2.969-9.722 2.969-4.598 0-8.74-1.7-11.87-4.526-.247-.223-.024-.527.27-.351 3.384 1.963 7.559 3.153 11.877 3.153 2.914 0 6.114-.607 9.06-1.852.439-.2.814.287.385.607zM22.792 14.961c-.336-.43-2.22-.207-3.074-.103-.255.032-.295-.192-.063-.36 1.5-1.053 3.967-.75 4.254-.399.287.36-.08 2.826-1.485 4.007-.215.184-.423.088-.327-.151.32-.79 1.03-2.57.695-2.994z"/></svg>
          AWS
        </button>
      </div>
    </div>
  </div>
  <div class="card" id="loginPanel" style="display:none">
    <h3>Kiro 在线登录 <button class="secondary small" onclick="cancelKiroLogin()">取消</button></h3>
    <div id="loginContent"></div>
  </div>
  <div class="card" id="scanResults" style="display:none">
    <h3>扫描结果</h3>
    <div id="scanList"></div>
  </div>
  <div class="card">
    <h3>登录方式</h3>
    <p style="color:var(--muted);font-size:0.875rem;margin-bottom:0.5rem">
      <strong>方式一：在线登录（推荐）</strong> - 点击上方"在线登录"按钮，浏览器授权
    </p>
    <p style="color:var(--muted);font-size:0.875rem;margin-bottom:0.5rem">
      <strong>方式二：扫描 Token</strong> - 从 Kiro IDE 登录后扫描本地 Token
    </p>
  </div>
</div>
'''

HTML_LOGS = '''
<div class="panel" id="logs">
  <div class="card">
    <h3>请求日志 <button class="secondary small" onclick="loadLogs()">刷新</button></h3>
    <table>
      <thead><tr><th>时间</th><th>路径</th><th>模型</th><th>账号</th><th>状态</th><th>耗时</th></tr></thead>
      <tbody id="logTable"></tbody>
    </table>
  </div>
</div>
'''

HTML_API = '''
<div class="panel" id="api">
  <div class="card">
    <h3>API 端点</h3>
    <p style="color:var(--muted);font-size:0.875rem;margin-bottom:1rem">支持 OpenAI、Anthropic、Gemini 三种协议</p>
    <h4 style="color:var(--muted);margin-bottom:0.5rem">OpenAI 协议</h4>
    <div class="endpoint"><span class="method post">POST</span><code>/v1/chat/completions</code></div>
    <div class="endpoint"><span class="method get">GET</span><code>/v1/models</code></div>
    <h4 style="color:var(--muted);margin-top:1rem;margin-bottom:0.5rem">Anthropic 协议</h4>
    <div class="endpoint"><span class="method post">POST</span><code>/v1/messages</code></div>
    <div class="endpoint"><span class="method post">POST</span><code>/v1/messages/count_tokens</code></div>
    <h4 style="color:var(--muted);margin-top:1rem;margin-bottom:0.5rem">Gemini 协议</h4>
    <div class="endpoint"><span class="method post">POST</span><code>/v1/models/{model}:generateContent</code></div>
    <h4 style="margin-top:1rem;color:var(--muted)">Base URL</h4>
    <pre><code id="baseUrl"></code></pre>
    <button class="copy-btn" onclick="copy(location.origin)" style="margin-top:0.5rem">复制</button>
  </div>
  <div class="card">
    <h3>配置示例</h3>
    <h4 style="color:var(--muted);margin-bottom:0.5rem">Claude Code</h4>
    <pre><code>Base URL: <span class="pyUrl"></span>
API Key: any
模型: claude-sonnet-4</code></pre>
    <h4 style="color:var(--muted);margin-top:1rem;margin-bottom:0.5rem">Codex CLI</h4>
    <pre><code>Endpoint: <span class="pyUrl"></span>/v1
API Key: any
模型: gpt-4o</code></pre>
  </div>
</div>
'''

HTML_BODY = HTML_HEADER + HTML_HELP + HTML_FLOWS + HTML_MONITOR + HTML_ACCOUNTS + HTML_LOGS + HTML_API


# ==================== JavaScript ====================
JS_UTILS = '''
const $=s=>document.querySelector(s);
const $$=s=>document.querySelectorAll(s);

function copy(text){
  navigator.clipboard.writeText(text).then(()=>{
    const toast=document.createElement('div');
    toast.textContent='已复制';
    toast.style.cssText='position:fixed;bottom:2rem;left:50%;transform:translateX(-50%);background:var(--accent);color:var(--bg);padding:0.5rem 1rem;border-radius:6px;font-size:0.875rem;z-index:1000';
    document.body.appendChild(toast);
    setTimeout(()=>toast.remove(),1500);
  });
}

function formatUptime(s){
  if(s<60)return s+'秒';
  if(s<3600)return Math.floor(s/60)+'分钟';
  return Math.floor(s/3600)+'小时'+Math.floor((s%3600)/60)+'分钟';
}

function escapeHtml(text){
  const div=document.createElement('div');
  div.textContent=text;
  return div.innerHTML;
}
'''

JS_TABS = '''
// Tabs
$$('.tab').forEach(t=>t.onclick=()=>{
  $$('.tab').forEach(x=>x.classList.remove('active'));
  $$('.panel').forEach(x=>x.classList.remove('active'));
  t.classList.add('active');
  $('#'+t.dataset.tab).classList.add('active');
  if(t.dataset.tab==='monitor'){loadStats();loadQuota();}
  if(t.dataset.tab==='logs')loadLogs();
  if(t.dataset.tab==='accounts')loadAccounts();
  if(t.dataset.tab==='flows'){loadFlowStats();loadFlows();}
});
'''

JS_STATUS = '''
// Status
async function checkStatus(){
  try{
    const r=await fetch('/api/status');
    const d=await r.json();
    $('#statusDot').className='status-dot '+(d.ok?'ok':'err');
    $('#statusText').textContent=d.ok?'已连接':'未连接';
    if(d.stats)$('#uptime').textContent='运行 '+formatUptime(d.stats.uptime_seconds);
  }catch(e){
    $('#statusDot').className='status-dot err';
    $('#statusText').textContent='连接失败';
  }
}
checkStatus();
setInterval(checkStatus,30000);

// URLs
$('#baseUrl').textContent=location.origin;
$$('.pyUrl').forEach(e=>e.textContent=location.origin);
'''

JS_DOCS = '''
// 文档浏览
let docsData = [];
let currentDoc = null;

// 简单的 Markdown 渲染
function renderMarkdown(text) {
  return text
    .replace(/```(\\w*)\\n([\\s\\S]*?)```/g, '<pre><code class="lang-$1">$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
    .replace(/\\*(.+?)\\*/g, '<em>$1</em>')
    .replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank">$1</a>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\\/li>\\n?)+/g, '<ul>$&</ul>')
    .replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^---$/gm, '<hr>')
    .replace(/\\|(.+)\\|/g, function(match) {
      const cells = match.split('|').filter(c => c.trim());
      if (cells.every(c => /^[\\s-:]+$/.test(c))) return '';
      const tag = match.includes('---') ? 'th' : 'td';
      return '<tr>' + cells.map(c => '<' + tag + '>' + c.trim() + '</' + tag + '>').join('') + '</tr>';
    })
    .replace(/(<tr>.*<\\/tr>\\n?)+/g, '<table>$&</table>')
    .replace(/\\n\\n/g, '</p><p>')
    .replace(/\\n/g, '<br>');
}

async function loadDocs() {
  try {
    const r = await fetch('/api/docs');
    const d = await r.json();
    docsData = d.docs || [];
    
    // 渲染导航
    $('#docsNav').innerHTML = docsData.map((doc, i) => 
      '<a class="docs-nav-item' + (i === 0 ? ' active' : '') + '" data-id="' + doc.id + '" onclick="showDoc(\\'' + doc.id + '\\')">' + doc.title + '</a>'
    ).join('');
    
    // 显示第一个文档
    if (docsData.length > 0) {
      showDoc(docsData[0].id);
    }
  } catch (e) {
    $('#docsContent').innerHTML = '<p style="color:var(--error)">加载文档失败</p>';
  }
}

async function showDoc(id) {
  // 更新导航状态
  $$('.docs-nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.id === id);
  });
  
  // 获取文档内容
  try {
    const r = await fetch('/api/docs/' + id);
    const d = await r.json();
    currentDoc = d;
    $('#docsContent').innerHTML = renderMarkdown(d.content);
  } catch (e) {
    $('#docsContent').innerHTML = '<p style="color:var(--error)">加载文档失败</p>';
  }
}

// 页面加载时加载文档
loadDocs();
'''

JS_STATS = '''
// Stats
async function loadStats(){
  try{
    const r=await fetch('/api/stats');
    const d=await r.json();
    $('#statsGrid').innerHTML=`
      <div class="stat-item"><div class="stat-value">${d.total_requests}</div><div class="stat-label">总请求</div></div>
      <div class="stat-item"><div class="stat-value">${d.total_errors}</div><div class="stat-label">错误数</div></div>
      <div class="stat-item"><div class="stat-value">${d.error_rate}</div><div class="stat-label">错误率</div></div>
      <div class="stat-item"><div class="stat-value">${d.accounts_available}/${d.accounts_total}</div><div class="stat-label">可用账号</div></div>
      <div class="stat-item"><div class="stat-value">${d.accounts_cooldown||0}</div><div class="stat-label">冷却中</div></div>
    `;
  }catch(e){console.error(e)}
}

// Quota
async function loadQuota(){
  try{
    const r=await fetch('/api/quota');
    const d=await r.json();
    if(d.exceeded_credentials&&d.exceeded_credentials.length>0){
      $('#quotaStatus').innerHTML=d.exceeded_credentials.map(c=>`
        <div style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem;background:var(--bg);border-radius:4px;margin-bottom:0.5rem">
          <span><span class="badge warn">冷却中</span> ${c.credential_id}</span>
          <span style="color:var(--muted);font-size:0.8rem">剩余 ${c.remaining_seconds}秒</span>
          <button class="secondary small" onclick="restoreAccount('${c.credential_id}')">恢复</button>
        </div>
      `).join('');
    }else{
      $('#quotaStatus').innerHTML='<p style="color:var(--muted)">无冷却中的账号</p>';
    }
  }catch(e){console.error(e)}
}

// Speedtest
async function runSpeedtest(){
  $('#speedtestBtn').disabled=true;
  $('#speedtestResult').textContent='测试中...';
  try{
    const r=await fetch('/api/speedtest',{method:'POST'});
    const d=await r.json();
    $('#speedtestResult').textContent=d.ok?`延迟: ${d.latency_ms.toFixed(0)}ms (${d.account_id})`:'测试失败: '+d.error;
  }catch(e){$('#speedtestResult').textContent='测试失败'}
  $('#speedtestBtn').disabled=false;
}
'''

JS_LOGS = '''
// Logs
async function loadLogs(){
  try{
    const r=await fetch('/api/logs?limit=50');
    const d=await r.json();
    $('#logTable').innerHTML=(d.logs||[]).map(l=>`
      <tr>
        <td>${new Date(l.timestamp*1000).toLocaleTimeString()}</td>
        <td>${l.path}</td>
        <td>${l.model||'-'}</td>
        <td>${l.account_id||'-'}</td>
        <td><span class="badge ${l.status<400?'success':l.status<500?'warn':'error'}">${l.status}</span></td>
        <td>${l.duration_ms.toFixed(0)}ms</td>
      </tr>
    `).join('');
  }catch(e){console.error(e)}
}
'''


JS_ACCOUNTS = '''
// Accounts
async function loadAccounts(){
  try{
    const r=await fetch('/api/accounts');
    const d=await r.json();
    if(!d.accounts||d.accounts.length===0){
      $('#accountList').innerHTML='<p style="color:var(--muted)">暂无账号，请点击"扫描 Token"</p>';
      return;
    }
    $('#accountList').innerHTML=d.accounts.map(a=>{
      const statusBadge=a.status==='active'?'success':a.status==='cooldown'?'warn':'error';
      const statusText={active:'可用',cooldown:'冷却中',unhealthy:'不健康',disabled:'已禁用'}[a.status]||a.status;
      const authBadge=a.auth_method==='idc'?'info':'success';
      const authText=a.auth_method==='idc'?'IdC':'Social';
      return `
        <div class="account-card">
          <div class="account-header">
            <div class="account-name">
              <span class="badge ${statusBadge}">${statusText}</span>
              <span class="badge ${authBadge}">${authText}</span>
              <span>${a.name}</span>
            </div>
            <span style="color:var(--muted);font-size:0.75rem">${a.id}</span>
          </div>
          <div class="account-meta">
            <div class="account-meta-item"><span>请求数</span><span>${a.request_count}</span></div>
            <div class="account-meta-item"><span>错误数</span><span>${a.error_count}</span></div>
            <div class="account-meta-item"><span>Token</span><span class="badge ${a.token_expired?'error':a.token_expiring_soon?'warn':'success'}">${a.token_expired?'已过期':a.token_expiring_soon?'即将过期':'有效'}</span></div>
            ${a.cooldown_remaining?`<div class="account-meta-item"><span>冷却剩余</span><span>${a.cooldown_remaining}秒</span></div>`:''}
          </div>
          <div id="usage-${a.id}" class="account-usage" style="display:none;margin-top:0.75rem;padding:0.75rem;background:var(--bg);border-radius:6px"></div>
          <div class="account-actions">
            <button class="secondary small" onclick="queryUsage('${a.id}')">查询用量</button>
            <button class="secondary small" onclick="refreshToken('${a.id}')">刷新 Token</button>
            <button class="secondary small" onclick="viewAccountDetail('${a.id}')">详情</button>
            ${a.status==='cooldown'?`<button class="secondary small" onclick="restoreAccount('${a.id}')">恢复</button>`:''}
            <button class="secondary small" onclick="toggleAccount('${a.id}')">${a.enabled?'禁用':'启用'}</button>
            <button class="secondary small" onclick="deleteAccount('${a.id}')" style="color:var(--error)">删除</button>
          </div>
        </div>
      `;
    }).join('');
  }catch(e){console.error(e)}
}

async function queryUsage(id){
  const usageDiv=$('#usage-'+id);
  usageDiv.style.display='block';
  usageDiv.innerHTML='<span style="color:var(--muted)">查询中...</span>';
  try{
    const r=await fetch('/api/accounts/'+id+'/usage');
    const d=await r.json();
    if(d.ok){
      const u=d.usage;
      const pct=u.usage_limit>0?((u.current_usage/u.usage_limit)*100).toFixed(1):0;
      const barColor=u.is_low_balance?'var(--error)':'var(--success)';
      usageDiv.innerHTML=`
        <div style="display:flex;justify-content:space-between;margin-bottom:0.5rem">
          <span style="font-weight:500">${u.subscription_title}</span>
          <span class="badge ${u.is_low_balance?'error':'success'}">${u.is_low_balance?'余额不足':'正常'}</span>
        </div>
        <div style="background:var(--border);border-radius:4px;height:8px;margin-bottom:0.5rem;overflow:hidden">
          <div style="background:${barColor};height:100%;width:${pct}%;transition:width 0.3s"></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.5rem;font-size:0.8rem">
          <div><span style="color:var(--muted)">已用:</span> ${u.current_usage.toFixed(2)}</div>
          <div><span style="color:var(--muted)">总额:</span> ${u.usage_limit.toFixed(2)}</div>
          <div><span style="color:var(--muted)">余额:</span> ${u.balance.toFixed(2)}</div>
          <div><span style="color:var(--muted)">使用率:</span> ${pct}%</div>
        </div>
      `;
    }else{
      usageDiv.innerHTML=`<span style="color:var(--error)">查询失败: ${d.error}</span>`;
    }
  }catch(e){
    usageDiv.innerHTML=`<span style="color:var(--error)">查询失败: ${e.message}</span>`;
  }
}

async function refreshToken(id){
  try{
    const r=await fetch('/api/accounts/'+id+'/refresh',{method:'POST'});
    const d=await r.json();
    alert(d.ok?'刷新成功':'刷新失败: '+d.message);
    loadAccounts();
  }catch(e){alert('刷新失败: '+e.message)}
}

async function refreshAllTokens(){
  try{
    const r=await fetch('/api/accounts/refresh-all',{method:'POST'});
    const d=await r.json();
    alert(`刷新完成: ${d.refreshed} 个账号`);
    loadAccounts();
  }catch(e){alert('刷新失败: '+e.message)}
}

async function restoreAccount(id){
  try{
    await fetch('/api/accounts/'+id+'/restore',{method:'POST'});
    loadAccounts();
    loadQuota();
  }catch(e){alert('恢复失败: '+e.message)}
}

async function viewAccountDetail(id){
  try{
    const r=await fetch('/api/accounts/'+id);
    const d=await r.json();
    alert(`账号: ${d.name}\\nID: ${d.id}\\n状态: ${d.status}\\n请求数: ${d.request_count}\\n错误数: ${d.error_count}`);
  }catch(e){alert('获取详情失败: '+e.message)}
}

async function toggleAccount(id){
  await fetch('/api/accounts/'+id+'/toggle',{method:'POST'});
  loadAccounts();
}

async function deleteAccount(id){
  if(confirm('确定删除此账号?')){
    await fetch('/api/accounts/'+id,{method:'DELETE'});
    loadAccounts();
  }
}

function showAddAccount(){
  const path=prompt('输入 Token 文件路径:');
  if(path){
    const name=prompt('账号名称:','账号');
    fetch('/api/accounts',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name,token_path:path})
    }).then(r=>r.json()).then(d=>{
      if(d.ok)loadAccounts();
      else alert(d.detail||'添加失败');
    });
  }
}

async function scanTokens(){
  try{
    const r=await fetch('/api/token/scan');
    const d=await r.json();
    const panel=$('#scanResults');
    const list=$('#scanList');
    if(d.tokens&&d.tokens.length>0){
      panel.style.display='block';
      list.innerHTML=d.tokens.map(t=>`
        <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem;border:1px solid var(--border);border-radius:6px;margin-bottom:0.5rem">
          <div>
            <div>${t.name}</div>
            <div style="color:var(--muted);font-size:0.75rem">${t.path}</div>
          </div>
          ${t.already_added?'<span class="badge info">已添加</span>':`<button class="secondary small" onclick="addFromScan('${t.path}','${t.name}')">添加</button>`}
        </div>
      `).join('');
    }else{
      alert('未找到 Token 文件');
    }
  }catch(e){alert('扫描失败: '+e.message)}
}

async function addFromScan(path,name){
  try{
    const r=await fetch('/api/token/add-from-scan',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path,name})
    });
    const d=await r.json();
    if(d.ok){
      loadAccounts();
      scanTokens();
    }else{
      alert(d.detail||'添加失败');
    }
  }catch(e){alert('添加失败: '+e.message)}
}

async function checkTokens(){
  try{
    const r=await fetch('/api/token/refresh-check',{method:'POST'});
    const d=await r.json();
    let msg='Token 状态:\\n\\n';
    (d.accounts||[]).forEach(a=>{
      const status=a.valid?'✅ 有效':'❌ 无效';
      msg+=`${a.name}: ${status}\\n`;
    });
    alert(msg);
  }catch(e){alert('检查失败: '+e.message)}
}
'''

JS_LOGIN = '''
// Kiro 在线登录
let loginPollTimer=null;
let selectedBrowser='default';

async function showLoginOptions(){
  try{
    const r=await fetch('/api/browsers');
    const d=await r.json();
    const browsers=d.browsers||[];
    if(browsers.length>0){
      $('#browserList').innerHTML=browsers.map(b=>`
        <button class="${b.id==='default'?'':'secondary'} small" onclick="selectBrowser('${b.id}',this)" data-browser="${b.id}">${b.name}</button>
      `).join('');
    }
    selectedBrowser='default';
    $('#loginOptions').style.display='block';
  }catch(e){
    $('#loginOptions').style.display='block';
  }
}

function selectBrowser(id,btn){
  selectedBrowser=id;
  $$('#browserList button').forEach(b=>b.classList.add('secondary'));
  btn.classList.remove('secondary');
}

async function startSocialLogin(provider){
  const incognito=$('#incognitoMode')?.checked||false;
  $('#loginOptions').style.display='none';
  try{
    const r=await fetch('/api/kiro/social/start',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({provider,browser:selectedBrowser,incognito})
    });
    const d=await r.json();
    if(!d.ok){alert('启动登录失败: '+d.error);return;}
    showSocialLoginPanel(d.provider);
  }catch(e){alert('启动登录失败: '+e.message)}
}

function showSocialLoginPanel(provider){
  $('#loginPanel').style.display='block';
  $('#loginContent').innerHTML=`
    <div style="text-align:center;padding:1rem">
      <p style="margin-bottom:1rem">正在使用 ${provider} 登录...</p>
      <p style="color:var(--muted);font-size:0.875rem">请在浏览器中完成授权</p>
      <p style="color:var(--muted);font-size:0.875rem;margin-top:1rem">授权完成后，请将浏览器地址栏中的完整 URL 粘贴到下方：</p>
      <input type="text" id="callbackUrl" placeholder="粘贴回调 URL..." style="width:100%;margin-top:0.5rem">
      <button onclick="handleSocialCallback()" style="margin-top:0.5rem">提交</button>
      <p style="color:var(--muted);font-size:0.75rem;margin-top:0.5rem" id="loginStatus"></p>
    </div>
  `;
}

async function handleSocialCallback(){
  const url=$('#callbackUrl').value;
  if(!url){alert('请粘贴回调 URL');return;}
  try{
    const urlObj=new URL(url);
    const code=urlObj.searchParams.get('code');
    const state=urlObj.searchParams.get('state');
    if(!code||!state){alert('无效的回调 URL');return;}
    $('#loginStatus').textContent='正在交换 Token...';
    const r=await fetch('/api/kiro/social/exchange',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({code,state})
    });
    const d=await r.json();
    if(d.ok&&d.completed){
      $('#loginStatus').textContent='✅ '+d.message;
      $('#loginStatus').style.color='var(--success)';
      setTimeout(()=>{$('#loginPanel').style.display='none';loadAccounts();},1500);
    }else{
      $('#loginStatus').textContent='❌ '+(d.error||'登录失败');
      $('#loginStatus').style.color='var(--error)';
    }
  }catch(e){alert('处理回调失败: '+e.message)}
}

async function startAwsLogin(){
  $('#loginOptions').style.display='none';
  startKiroLogin(selectedBrowser);
}

async function startKiroLogin(browser='default'){
  const incognito=$('#incognitoMode')?.checked||false;
  try{
    const r=await fetch('/api/kiro/login/start',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({browser,incognito})
    });
    const d=await r.json();
    if(!d.ok){alert('启动登录失败: '+d.error);return;}
    showLoginPanel(d);
    startLoginPoll();
  }catch(e){alert('启动登录失败: '+e.message)}
}

function showLoginPanel(data){
  $('#loginPanel').style.display='block';
  $('#loginContent').innerHTML=`
    <div style="text-align:center;padding:1rem">
      <p style="margin-bottom:1rem">请在浏览器中完成 AWS Builder ID 授权：</p>
      <div style="font-size:2rem;font-weight:bold;letter-spacing:0.5rem;padding:1rem;background:var(--bg);border-radius:8px;margin-bottom:1rem">${data.user_code}</div>
      <p style="margin-bottom:1rem">
        <a href="${data.verification_uri}" target="_blank" style="color:var(--info);text-decoration:underline">点击打开授权页面</a>
        <button class="secondary small" style="margin-left:0.5rem" onclick="copy('${data.verification_uri}')">复制链接</button>
      </p>
      <p style="color:var(--muted);font-size:0.875rem">授权码有效期: ${Math.floor(data.expires_in/60)} 分钟</p>
      <p style="color:var(--muted);font-size:0.875rem;margin-top:0.5rem" id="loginStatus">等待授权...</p>
    </div>
  `;
}

function startLoginPoll(){
  if(loginPollTimer)clearInterval(loginPollTimer);
  loginPollTimer=setInterval(pollLogin,3000);
}

async function pollLogin(){
  try{
    const r=await fetch('/api/kiro/login/poll');
    const d=await r.json();
    if(!d.ok){$('#loginStatus').textContent='错误: '+d.error;stopLoginPoll();return;}
    if(d.completed){
      $('#loginStatus').textContent='✅ 登录成功！';
      $('#loginStatus').style.color='var(--success)';
      stopLoginPoll();
      setTimeout(()=>{$('#loginPanel').style.display='none';loadAccounts();},1500);
    }
  }catch(e){$('#loginStatus').textContent='轮询失败: '+e.message}
}

function stopLoginPoll(){
  if(loginPollTimer){clearInterval(loginPollTimer);loginPollTimer=null;}
}

async function cancelKiroLogin(){
  stopLoginPoll();
  await fetch('/api/kiro/login/cancel',{method:'POST'});
  $('#loginPanel').style.display='none';
}
'''


JS_FLOWS = '''
// Flow Monitor
async function loadFlowStats(){
  try{
    const r=await fetch('/api/flows/stats');
    const d=await r.json();
    $('#flowStatsGrid').innerHTML=`
      <div class="stat-item"><div class="stat-value">${d.total_flows}</div><div class="stat-label">总请求</div></div>
      <div class="stat-item"><div class="stat-value">${d.completed}</div><div class="stat-label">完成</div></div>
      <div class="stat-item"><div class="stat-value">${d.errors}</div><div class="stat-label">错误</div></div>
      <div class="stat-item"><div class="stat-value">${d.error_rate}</div><div class="stat-label">错误率</div></div>
      <div class="stat-item"><div class="stat-value">${d.avg_duration_ms.toFixed(0)}ms</div><div class="stat-label">平均延迟</div></div>
      <div class="stat-item"><div class="stat-value">${d.total_tokens_in}</div><div class="stat-label">输入Token</div></div>
      <div class="stat-item"><div class="stat-value">${d.total_tokens_out}</div><div class="stat-label">输出Token</div></div>
    `;
  }catch(e){console.error(e)}
}

async function loadFlows(){
  try{
    const protocol=$('#flowProtocol').value;
    const state=$('#flowState').value;
    const search=$('#flowSearch').value;
    let url='/api/flows?limit=50';
    if(protocol)url+=`&protocol=${protocol}`;
    if(state)url+=`&state=${state}`;
    if(search)url+=`&search=${encodeURIComponent(search)}`;
    const r=await fetch(url);
    const d=await r.json();
    if(!d.flows||d.flows.length===0){
      $('#flowList').innerHTML='<p style="color:var(--muted)">暂无请求记录</p>';
      return;
    }
    $('#flowList').innerHTML=d.flows.map(f=>{
      const stateBadge={completed:'success',error:'error',streaming:'info',pending:'warn'}[f.state]||'info';
      const stateText={completed:'完成',error:'错误',streaming:'流式中',pending:'等待中'}[f.state]||f.state;
      const time=new Date(f.timing.created_at*1000).toLocaleTimeString();
      const duration=f.timing.duration_ms?f.timing.duration_ms.toFixed(0)+'ms':'-';
      const model=f.request?.model||'-';
      const tokens=f.response?.usage?(f.response.usage.input_tokens+'/'+f.response.usage.output_tokens):'-';
      return `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem;border:1px solid var(--border);border-radius:6px;margin-bottom:0.5rem;cursor:pointer" onclick="viewFlow('${f.id}')">
          <div style="flex:1">
            <div style="display:flex;align-items:center;gap:0.5rem">
              <span class="badge ${stateBadge}">${stateText}</span>
              <span style="font-weight:500">${model}</span>
              ${f.bookmarked?'<span style="color:var(--warn)">★</span>':''}
            </div>
            <div style="color:var(--muted);font-size:0.75rem;margin-top:0.25rem">
              ${time} · ${duration} · ${tokens} tokens · ${f.protocol}
            </div>
          </div>
          <button class="secondary small" onclick="event.stopPropagation();toggleBookmark('${f.id}',${!f.bookmarked})">${f.bookmarked?'取消':'收藏'}</button>
        </div>
      `;
    }).join('');
  }catch(e){console.error(e)}
}

async function viewFlow(id){
  try{
    const r=await fetch('/api/flows/'+id);
    const f=await r.json();
    let html=`<div style="margin-bottom:1rem"><strong>ID:</strong> ${f.id}<br><strong>协议:</strong> ${f.protocol}<br><strong>状态:</strong> ${f.state}<br><strong>时间:</strong> ${new Date(f.timing.created_at*1000).toLocaleString()}<br><strong>延迟:</strong> ${f.timing.duration_ms?f.timing.duration_ms.toFixed(0)+'ms':'N/A'}</div>`;
    if(f.request){
      html+=`<h4 style="margin-bottom:0.5rem">请求</h4><div style="margin-bottom:1rem"><strong>模型:</strong> ${f.request.model}<br><strong>流式:</strong> ${f.request.stream?'是':'否'}</div>`;
    }
    if(f.response){
      html+=`<h4 style="margin-top:1rem;margin-bottom:0.5rem">响应</h4><div><strong>状态码:</strong> ${f.response.status_code}<br><strong>Token:</strong> ${f.response.usage?.input_tokens||0} in / ${f.response.usage?.output_tokens||0} out</div>`;
    }
    if(f.error){
      html+=`<h4 style="margin-top:1rem;margin-bottom:0.5rem;color:var(--error)">错误</h4><div><strong>类型:</strong> ${f.error.type}<br><strong>消息:</strong> ${f.error.message}</div>`;
    }
    $('#flowDetailContent').innerHTML=html;
    $('#flowDetail').style.display='block';
  }catch(e){alert('获取详情失败: '+e.message)}
}

async function toggleBookmark(id,bookmarked){
  await fetch('/api/flows/'+id+'/bookmark',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bookmarked})});
  loadFlows();
}

async function exportFlows(){
  try{
    const r=await fetch('/api/flows/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({format:'json'})});
    const d=await r.json();
    const blob=new Blob([d.content],{type:'application/json'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;
    a.download='flows_'+new Date().toISOString().slice(0,10)+'.json';
    a.click();
  }catch(e){alert('导出失败: '+e.message)}
}
'''

JS_SCRIPTS = JS_UTILS + JS_TABS + JS_STATUS + JS_DOCS + JS_STATS + JS_LOGS + JS_ACCOUNTS + JS_LOGIN + JS_FLOWS


# ==================== 组装最终 HTML ====================
HTML_PAGE = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kiro API</title>
<link rel="icon" type="image/svg+xml" href="/assets/icon.svg">
<style>
{CSS_STYLES}
</style>
</head>
<body>
<div class="container">
{HTML_BODY}
<div class="footer">Kiro API Proxy v1.5.0 - Flow Monitor | 在线登录 | Token 自动刷新 | 配额管理</div>
</div>
<script>
{JS_SCRIPTS}
</script>
</body>
</html>'''
