# KaliMcp

> 将 Kali Linux 打造为 AI 可调用的 MCP Server

KaliMcp 是一个运行在 Kali Linux 上的 [MCP (Model Context Protocol)](https://modelcontextprotocol.io) 服务器，将 Kali 的 **500+ 内置安全工具**、**交互式终端**和**代码创建能力**暴露给大模型（Claude、GPT、Warp Agent 等），使 AI 能够自主编排完整的安全测试工作流。

---

## 核心能力

| 模块 | 能力 | 示例 |
|------|------|------|
| **Tool Engine** | 调用所有 Kali 命令行工具 | nmap 扫描、sqlmap 注入、hydra 爆破 |
| **Terminal Manager** | 管理交互式终端会话 | 操作 Metasploit、接收反弹 Shell |
| **CodeForge** | 创建/编辑/执行自定义程序 | 编写 Python 利用脚本并运行 |
| **Resources** | 查询系统状态与工具目录 | Kali 版本、网络接口、工具清单 |
| **Prompts** | 预置安全测试工作流模板 | 渗透测试、CTF、应急响应 |

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                 AI / LLM Client                 │
│         (Claude, GPT, Warp, 自定义Agent)        │
└──────────────────┬──────────────────────────────┘
                   │ MCP Protocol (Streamable HTTP)
┌──────────────────▼──────────────────────────────┐
│              KaliMcp Server (Python)             │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │         Auth & Rate Limiting Layer         │  │
│  ├────────────────────────────────────────────┤  │
│  │            MCP Tool Registry               │  │
│  │  ┌──────────┬────────────┬─────────────┐   │  │
│  │  │  Tool    │  Terminal  │  CodeForge   │   │  │
│  │  │  Engine  │  Manager   │  (代码创建)   │   │  │
│  │  └────┬─────┴─────┬──────┴──────┬──────┘   │  │
│  ├───────┼───────────┼─────────────┼──────────┤  │
│  │  ┌────▼────┐ ┌────▼─────┐ ┌─────▼──────┐  │  │
│  │  │ Process │ │   PTY    │ │ FileSystem │  │  │
│  │  │ Manager │ │  Manager │ │  Manager   │  │  │
│  │  └────┬────┘ └────┬─────┘ └─────┬──────┘  │  │
│  ├───────┼───────────┼─────────────┼──────────┤  │
│  │  ┌────▼───────────▼─────────────▼───────┐  │  │
│  │  │       Audit & Logging Layer          │  │  │
│  │  └──────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│                Kali Linux OS                     │
│  nmap, metasploit, sqlmap, hydra, aircrack ...   │
└──────────────────────────────────────────────────┘
```

---

## 技术选型

- **语言**: Python 3.11+ — Kali 原生预装，安全工具生态契合度最高
- **MCP SDK**: FastMCP (`mcp[cli]`) — 装饰器风格，开发效率高
- **传输**: Streamable HTTP (远程) + stdio (本地)
- **终端**: `pty` + `asyncio.subprocess` — 原生 PTY 伪终端
- **校验**: Pydantic v2 — 输入/输出数据模型
- **服务器**: uvicorn — 高性能 ASGI

---

## 项目结构

```
KaliMcp/
├── pyproject.toml                # 项目配置 & 依赖
├── README.md
├── config/
│   ├── default.yaml              # 默认配置 (端口、超时、限制等)
│   └── tools_catalog.yaml        # Kali 工具目录定义
├── src/
│   └── kalimcp/
│       ├── __init__.py
│       ├── server.py             # MCP Server 入口 + 启动逻辑
│       ├── auth.py               # API Key / JWT 认证
│       ├── config.py             # 配置加载 (YAML → Pydantic)
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── tool_engine.py    # 通用工具执行引擎 (exec_tool)
│       │   ├── recon.py          # 信息收集 (nmap, whois, amass...)
│       │   ├── vuln.py           # 漏洞分析 (nikto, openvas...)
│       │   ├── webapp.py         # Web 测试 (sqlmap, gobuster...)
│       │   ├── password.py       # 密码攻击 (john, hydra...)
│       │   ├── wireless.py       # 无线攻击 (aircrack-ng...)
│       │   ├── exploit.py        # 漏洞利用 (metasploit...)
│       │   ├── sniff.py          # 嗅探欺骗 (tshark, bettercap...)
│       │   ├── post_exploit.py   # 后渗透 (bloodhound...)
│       │   ├── forensic.py       # 取证 (volatility, binwalk...)
│       │   ├── social.py         # 社工 (setoolkit...)
│       │   ├── crypto.py         # 密码学 (hashid...)
│       │   └── reverse.py        # 逆向 (ghidra, radare2...)
│       ├── terminal/
│       │   ├── __init__.py
│       │   ├── manager.py        # 终端会话管理器
│       │   ├── pty_session.py    # PTY 伪终端会话
│       │   ├── listener.py       # Shell 监听器 (反弹Shell)
│       │   └── ansi.py           # ANSI 转义码清洗
│       ├── codeforge/
│       │   ├── __init__.py
│       │   ├── workspace.py      # /opt/kalimcp/workspace 管理
│       │   ├── editor.py         # 文件创建 / 编辑
│       │   └── executor.py       # 代码执行器
│       ├── resources/
│       │   ├── __init__.py
│       │   └── system.py         # MCP Resources (系统信息)
│       ├── prompts/
│       │   ├── __init__.py
│       │   └── workflows.py      # 预置渗透测试工作流模板
│       └── utils/
│           ├── __init__.py
│           ├── process.py        # 异步进程管理
│           ├── sanitizer.py      # 命令注入防护 / 输入清洗
│           ├── parser.py         # 工具输出解析 (XML/JSON/文本)
│           └── audit.py          # 审计日志
└── tests/
    ├── test_tool_engine.py
    ├── test_terminal.py
    ├── test_codeforge.py
    └── test_security.py
```

---

## 模块设计

### 1. Tool Engine — 工具执行引擎

将 Kali 所有命令行工具封装为 MCP Tool，按 Kali 菜单体系分类。

#### 工具分类

| 前缀 | 类别 | 典型工具 |
|------|------|---------|
| `recon_*` | 信息收集 | nmap, whois, dig, theHarvester, amass |
| `vuln_*` | 漏洞分析 | nikto, openvas, legion |
| `webapp_*` | Web 应用测试 | sqlmap, dirb, gobuster, wfuzz, zaproxy |
| `password_*` | 密码攻击 | john, hashcat, hydra, medusa, cewl |
| `wireless_*` | 无线攻击 | aircrack-ng, wifite, kismet |
| `exploit_*` | 漏洞利用 | metasploit, searchsploit |
| `sniff_*` | 嗅探与欺骗 | tshark, ettercap, bettercap, responder |
| `post_*` | 后渗透 | mimikatz, bloodhound, empire |
| `forensic_*` | 取证分析 | autopsy, volatility, binwalk, foremost |
| `social_*` | 社会工程 | setoolkit, gophish |
| `crypto_*` | 密码学 | hashid, hash-identifier |
| `reverse_*` | 逆向工程 | ghidra, radare2, gdb |

#### 核心接口

**通用执行** — 可调用任意已安装工具：

```python
@mcp.tool()
async def exec_tool(
    tool_name: str,           # 工具名，如 "nmap"
    arguments: str,           # 命令行参数
    timeout: int = 300,       # 超时(秒)
    output_format: str = "text"
) -> str:
    """执行任意 Kali 工具并返回结果"""
```

**高级封装** — 为高频工具提供结构化输入/输出：

```python
@mcp.tool()
async def recon_nmap(
    target: str,
    scan_type: Literal["quick", "full", "vuln", "os", "service"] = "quick",
    ports: str = "1-1000",
    extra_args: str = ""
) -> NmapResult:
    """nmap 网络扫描，返回结构化 JSON 结果"""
```

**工具发现**：

```python
@mcp.tool()
async def list_kali_tools(category: str = "all") -> list[KaliToolInfo]:
    """列出可用工具及描述"""

@mcp.tool()
async def tool_help(tool_name: str) -> str:
    """获取工具帮助信息 (--help / man)"""
```

---

### 2. Terminal Manager — 交互式终端管理

管理多个持久化 PTY 会话，用于操作 Metasploit、接收反弹 Shell 等交互式场景。

#### 会话管理

```python
@mcp.tool()
async def terminal_create(
    name: str = "",
    shell: str = "/bin/bash",
    cols: int = 120, rows: int = 40
) -> TerminalSession:
    """创建新的交互式终端会话"""

@mcp.tool()
async def terminal_exec(
    session_id: str,
    command: str,
    wait_for: str = "",       # 等待特定输出模式 (正则)
    timeout: int = 30
) -> TerminalOutput:
    """在终端中执行命令并等待输出"""

@mcp.tool()
async def terminal_read(session_id: str, lines: int = 50) -> str:
    """读取终端当前输出缓冲区"""

@mcp.tool()
async def terminal_send_input(
    session_id: str,
    data: str,
    press_enter: bool = True
) -> str:
    """向终端发送原始输入 (用于交互式程序)"""

@mcp.tool()
async def terminal_list() -> list[TerminalSession]:
    """列出所有活跃终端会话"""

@mcp.tool()
async def terminal_kill(session_id: str) -> bool:
    """销毁指定终端会话"""
```

#### Shell 监听器

```python
@mcp.tool()
async def shell_listener_start(
    port: int,
    protocol: Literal["tcp", "udp"] = "tcp",
    handler: Literal["raw", "meterpreter", "web"] = "raw"
) -> ListenerInfo:
    """启动监听器，等待目标反连"""

@mcp.tool()
async def shell_listener_list() -> list[ListenerInfo]:
    """列出所有活跃监听器及连接状态"""
```

#### PTY 实现细节

- 每个会话通过 `pty.openpty()` + `asyncio.subprocess` 创建独立伪终端
- 输出缓冲使用 **环形缓冲 (Ring Buffer)**，保留最近 10,000 行
- 自动清洗 ANSI 转义码，返回干净文本给 AI
- 会话超时自动回收（默认 30 分钟无操作）
- 最大并发会话数限制（默认 20）

---

### 3. CodeForge — AI 代码创建引擎

让 AI 在 Kali 上创建、编辑、执行自定义脚本和程序。

```python
@mcp.tool()
async def code_create(
    file_path: str,
    content: str,
    language: str = "python",
    executable: bool = False
) -> FileInfo:
    """创建新文件/脚本"""

@mcp.tool()
async def code_edit(
    file_path: str,
    edits: list[FileEdit]     # [{search: str, replace: str}]
) -> FileInfo:
    """编辑已有文件"""

@mcp.tool()
async def code_read(
    file_path: str,
    start_line: int = 0,
    end_line: int = -1
) -> str:
    """读取文件内容"""

@mcp.tool()
async def code_execute(
    file_path: str,
    args: str = "",
    timeout: int = 120,
    stdin_data: str = ""
) -> ExecutionResult:
    """执行脚本/程序"""

@mcp.tool()
async def code_install_deps(
    packages: list[str],
    manager: Literal["pip", "apt", "npm", "gem", "go"] = "pip"
) -> str:
    """安装依赖包"""
```

**工作空间**: 所有 AI 创建的文件默认存放在 `/opt/kalimcp/workspace/`，按任务自动组织。

---

### 4. Resources — 系统资源

通过 MCP Resource 协议暴露 Kali 系统状态：

```python
@mcp.resource("kali://system/info")       # 系统版本、内核、已安装工具
@mcp.resource("kali://tools/catalog")     # 完整工具目录及分类
@mcp.resource("kali://network/interfaces") # 网络接口信息
@mcp.resource("kali://workspace/{path}")  # 工作空间文件内容
```

---

### 5. Prompts — 工作流模板

预置安全测试场景模板，AI 可直接调用：

- **`pentest_recon`** — 信息收集标准流程
- **`pentest_webapp`** — Web 应用渗透测试
- **`pentest_network`** — 内网渗透标准流程
- **`ctf_solve`** — CTF 解题辅助
- **`incident_response`** — 应急响应流程
- **`vuln_assessment`** — 漏洞评估报告

---

## 安全设计

### 认证与授权

- **API Key 认证**: HTTP Header `Authorization: Bearer <key>`
- **可选 JWT**: 带权限声明 (scopes)
- **权限分级**:
  - `read` — 查看工具列表、读取文件、查看终端输出
  - `execute` — 执行工具、运行脚本
  - `admin` — 管理监听器、安装软件包、修改系统配置

### 安全防护

- **命令注入防护**: 所有参数经过严格校验和转义，使用白名单工具列表
- **路径穿越防护**: 文件操作限制在 `/opt/kalimcp/workspace/` 内
- **资源限制**: 单个命令 CPU / 内存 / 时间上限 (`ulimit` + `timeout`)
- **操作审计**: 全部操作记录到 `/var/log/kalimcp/audit.log`
- **网络隔离**: 建议 MCP 服务器仅监听 VPN / 内网接口
- **黑名单命令**: 拦截 `rm -rf /`、`mkfs`、`dd if=/dev/zero` 等破坏性操作

### 速率限制

- 每分钟最大请求数（可配置，默认 60）
- 并发执行进程数上限（默认 10）
- 大型扫描任务排队机制

---

## 部署指南（方案 A：直接部署在 Kali 上）

### 前置要求

- Kali Linux 2024.1+（建议最新 rolling release）
- Python 3.11+
- root 或 sudo 权限（部分安全工具需要）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/yourname/KaliMcp.git
cd KaliMcp

# 2. 创建虚拟环境 (推荐)
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装项目
pip install -e ".[dev]"

# 4. 创建工作空间目录
sudo mkdir -p /opt/kalimcp/workspace
sudo chown $(whoami):$(whoami) /opt/kalimcp/workspace

# 5. 创建日志目录
sudo mkdir -p /var/log/kalimcp
sudo chown $(whoami):$(whoami) /var/log/kalimcp

# 6. 生成 API Key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# 将输出的 Key 记下来，配置到 config/default.yaml
```

### 配置

编辑 `config/default.yaml`：

```yaml
server:
  host: "0.0.0.0"
  port: 8443
  workers: 4

auth:
  api_keys:
    - key: "YOUR_GENERATED_API_KEY"
      name: "default"
      scopes: ["read", "execute", "admin"]

security:
  max_requests_per_minute: 60
  max_concurrent_processes: 10
  command_timeout: 300
  session_timeout: 1800          # 终端会话超时 (秒)
  max_sessions: 20
  blocked_commands:
    - "rm -rf /"
    - "mkfs"
    - "dd if=/dev/zero"
    - ":(){:|:&};:"

workspace:
  root: "/opt/kalimcp/workspace"
  max_file_size_mb: 50

logging:
  audit_log: "/var/log/kalimcp/audit.log"
  level: "INFO"
```

### 启动服务

```bash
# 开发模式 (自动重载)
kalimcp serve --host 0.0.0.0 --port 8443 --reload

# 生产模式
kalimcp serve --host 0.0.0.0 --port 8443

# 指定配置文件
kalimcp serve --config /path/to/config.yaml

# 仅 stdio 模式 (本地使用)
kalimcp stdio
```

### 验证部署

```bash
# 使用 MCP Inspector 测试
npx @modelcontextprotocol/inspector http://localhost:8443/mcp

# 手动测试 (curl)
curl -X POST http://localhost:8443/mcp \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### 设置为系统服务

创建 `/etc/systemd/system/kalimcp.service`：

```ini
[Unit]
Description=KaliMcp - Kali Linux MCP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/KaliMcp
Environment=PATH=/opt/KaliMcp/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/KaliMcp/.venv/bin/kalimcp serve --host 0.0.0.0 --port 8443
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable kalimcp
sudo systemctl start kalimcp
sudo systemctl status kalimcp
```

---

## 客户端接入

### Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "kali": {
      "url": "http://KALI_IP:8443/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

### Warp Agent

在 Warp 设置中添加 MCP Server：

```json
{
  "mcpServers": {
    "kali": {
      "url": "http://KALI_IP:8443/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

### 自定义 Python 客户端

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client(
        "http://KALI_IP:8443/mcp",
        headers={"Authorization": "Bearer YOUR_API_KEY"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 列出所有工具
            tools = await session.list_tools()

            # 执行 nmap 扫描
            result = await session.call_tool("recon_nmap", {
                "target": "192.168.1.0/24",
                "scan_type": "quick"
            })
            print(result)
```

---

## AI 调用示例流程

以下是 AI 执行一次完整渗透测试的调用链示例：

```
1. list_kali_tools(category="recon")
   → 获取可用侦察工具列表

2. recon_nmap(target="192.168.1.0/24", scan_type="quick")
   → 发现 192.168.1.100 开放了 80, 443, 22 端口

3. recon_nmap(target="192.168.1.100", scan_type="service")
   → 识别服务版本: Apache 2.4.49, OpenSSH 8.2

4. exec_tool("nikto", "-h http://192.168.1.100")
   → 发现 Web 漏洞

5. exec_tool("sqlmap", "-u http://192.168.1.100/page?id=1 --batch")
   → 确认 SQL 注入

6. terminal_create(name="msf")
   → 创建 Metasploit 交互终端

7. terminal_exec(session_id, "msfconsole")
   → 启动 Metasploit Framework

8. terminal_send_input(session_id, "use exploit/multi/http/apache_normalize_path_rce")
   → 加载利用模块

9. terminal_send_input(session_id, "set RHOSTS 192.168.1.100")
   → 配置目标

10. terminal_send_input(session_id, "exploit")
    → 执行攻击

11. code_create("report.py", "<生成报告的脚本>", executable=True)
    → AI 编写自定义报告生成脚本

12. code_execute("report.py")
    → 生成渗透测试报告
```

---

## 实施路线

### Phase 1 — MVP 基础框架（1-2 周）

- [x] 项目骨架搭建 + FastMCP Server 初始化
- [ ] `exec_tool` 通用工具执行引擎
- [ ] `list_kali_tools` / `tool_help` 工具发现
- [ ] API Key 认证
- [ ] 审计日志
- [ ] MCP Inspector 集成测试

### Phase 2 — 终端管理（1-2 周）

- [ ] PTY 会话创建 / 销毁 / 读写
- [ ] ANSI 转义码清洗
- [ ] Shell 监听器
- [ ] 会话超时与资源回收

### Phase 3 — CodeForge + 高级工具封装（1-2 周）

- [ ] 文件创建 / 编辑 / 执行
- [ ] 工作空间管理
- [ ] Top 20 工具结构化封装（nmap、sqlmap、hydra、metasploit 等）
- [ ] 工具输出解析器

### Phase 4 — 生产化（1 周）

- [ ] Resource & Prompt 模板
- [ ] TLS 加密
- [ ] 速率限制 & 命令黑名单完善
- [ ] 完整文档

---

## 依赖清单

```toml
# pyproject.toml [project.dependencies]
dependencies = [
    "mcp[cli]>=1.0.0",
    "pydantic>=2.0",
    "aiofiles>=24.0",
    "pyyaml>=6.0",
    "uvicorn>=0.30",
    "pyjwt>=2.8",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
]
```

---

## 许可证

MIT License

---

## 免责声明

KaliMcp 仅供授权安全测试和教育用途。使用者必须确保在合法授权范围内使用本工具。未经授权对计算机系统进行渗透测试属于违法行为。
