# Kali-Mcp-Toolkit — Kali Linux MCP Server

> 将 Kali Linux 500+ 安全工具通过 [Model Context Protocol](https://modelcontextprotocol.io/) 暴露给 AI 模型，实现 **AI 驱动的渗透测试与安全审计**。

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-1.0-purple.svg)](https://modelcontextprotocol.io/)

---

## 核心能力

| 模块 | 功能 | 关键特性 |
|------|------|----------|
| **Tool Engine** | 执行 Kali 工具 | 60+ 工具目录、12 大分类、风险分级、输出解析 |
| **Terminal Manager** | 交互式终端 | PTY 会话、异步读写、正则等待、反弹 Shell 监听 |
| **CodeForge** | 代码编辑/执行 | 12 种语言、沙箱工作区、依赖安装 |
| **Resources** | MCP 资源暴露 | 系统信息、工具目录、网络接口、工作区文件 |
| **Prompts** | 工作流模板 | 信息收集、Web 渗透、内网渗透、CTF、应急响应 |

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                   AI Client                      │
│         (Claude / Warp / 自定义客户端)            │
└───────────────┬─────────────────────────────────┘
                │  MCP Protocol (stdio / HTTP)
┌───────────────▼─────────────────────────────────┐
│               KaliMcp Server                     │
│  ┌──────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ Auth     │ │ Sanitizer │ │ Rate Limiter   │  │
│  │ (JWT/Key)│ │ (输入过滤) │ │ (速率限制)     │  │
│  └────┬─────┘ └─────┬─────┘ └───────┬────────┘  │
│       └─────────────┼───────────────┘            │
│  ┌──────────────────▼──────────────────────────┐ │
│  │              Tool Engine                     │ │
│  │  exec_tool · list_kali_tools · tool_help    │ │
│  └──────────────────┬──────────────────────────┘ │
│  ┌──────────┐ ┌─────▼─────┐ ┌────────────────┐  │
│  │ Terminal  │ │  Process  │ │   CodeForge    │  │
│  │ Manager  │ │  Executor │ │   Editor/Exec  │  │
│  └──────────┘ └───────────┘ └────────────────┘  │
│  ┌──────────────────────────────────────────────┐│
│  │          Audit Logger (JSON Lines)           ││
│  └──────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

---

## 技术栈

- **Python 3.11+** — 类型注解、asyncio
- **FastMCP** — MCP 协议服务端框架
- **Pydantic v2** — 配置校验与数据模型
- **uvicorn** — HTTP 传输层
- **pty + asyncio** — 伪终端异步会话
- **PyJWT** — JWT 认证
- **PyYAML / aiofiles** — 配置加载与异步文件 I/O

---

## 项目结构

```
KaliMcp/
├── pyproject.toml                  # 构建配置 & 依赖
├── config/
│   ├── default.yaml                # 默认配置文件
│   └── tools_catalog.yaml          # Kali 工具目录 (60+ 工具 × 12 分类)
├── src/kalimcp/
│   ├── __init__.py                 # 版本号
│   ├── config.py                   # Pydantic v2 配置模型 + YAML 加载 + 环境变量覆盖
│   ├── auth.py                     # API Key / JWT 认证、作用域、速率限制
│   ├── server.py                   # FastMCP 组装、所有 MCP 工具/资源/提示注册、CLI
│   ├── tools/
│   │   ├── __init__.py             # KaliToolInfo / ToolCatalog 数据模型
│   │   ├── tool_engine.py          # exec_tool / list_kali_tools / tool_help 核心引擎
│   │   ├── recon.py                # 信息收集 (nmap, whois, dig)
│   │   ├── vuln.py                 # 漏洞扫描 (nikto, openvas)
│   │   ├── webapp.py               # Web 渗透 (sqlmap, gobuster, ffuf, whatweb)
│   │   ├── password.py             # 密码攻击 (hydra, john, hashcat)
│   │   ├── exploit.py              # 漏洞利用 (msfconsole, searchsploit)
│   │   ├── wireless.py             # 无线攻击 (aircrack-ng)
│   │   ├── sniff.py                # 嗅探/欺骗 (tcpdump, wireshark)
│   │   ├── post_exploit.py         # 后渗透 (mimikatz, empire)
│   │   ├── forensic.py             # 取证分析 (volatility, autopsy)
│   │   ├── social.py               # 社会工程 (setoolkit)
│   │   ├── crypto.py               # 密码学 (openssl, gpg)
│   │   └── reverse.py              # 逆向工程 (ghidra, radare2)
│   ├── terminal/
│   │   ├── ansi.py                 # ANSI 转义码清理
│   │   ├── pty_session.py          # PTY 伪终端会话 (RingBuffer)
│   │   ├── manager.py              # 多会话生命周期管理 + 超时回收
│   │   └── listener.py             # 反弹 Shell 监听器 (默认关闭)
│   ├── codeforge/
│   │   ├── workspace.py            # 路径安全 (符号链接解析、大小限制)
│   │   ├── editor.py               # 文件创建 / 编辑 (search-replace) / 读取
│   │   └── executor.py             # 代码执行 (12 种语言) + 依赖安装
│   ├── utils/
│   │   ├── audit.py                # 异步 JSON Lines 审计日志 + 按大小轮转
│   │   ├── sanitizer.py            # 白名单、Shell 元字符防御、路径穿越防护
│   │   ├── process.py              # 异步子进程 (信号量并发、超时 SIGTERM→SIGKILL)
│   │   └── parser.py               # nmap XML 解析、格式自动检测、输出截断
│   ├── resources/
│   │   └── system.py               # MCP Resources (系统信息、工具目录、网络接口)
│   └── prompts/
│       └── workflows.py            # 6 个中文渗透测试工作流模板
├── tests/
│   ├── conftest.py                 # pytest fixtures
│   ├── test_security.py            # 安全测试 (17 cases)
│   ├── test_tool_engine.py         # 工具引擎测试 (11 cases)
│   ├── test_terminal.py            # 终端测试 (9 cases)
│   └── test_codeforge.py           # CodeForge 测试 (7 cases)
├── deploy/
│   └── kalimcp.service             # systemd 服务文件
└── scripts/
    └── install.sh                  # 一键部署脚本
```

---

## 快速开始

### 环境要求

- **Kali Linux** (或任何已安装 Kali 工具的 Linux)
- **Python ≥ 3.11**
- 需要安装目标 Kali 工具 (如 `nmap`, `nikto`, `sqlmap` 等)

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/trymonoly/KaliMcp.git
cd KaliMcp

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装项目 (含开发依赖)
pip install -e ".[dev]"
```

### 一键部署 (推荐)

```bash
# 自动创建目录、安装依赖、配置 systemd 服务
sudo bash scripts/install.sh
```

### 配置

编辑 `config/default.yaml`：

```yaml
auth:
  api_keys:
    - key: "你的安全密钥"      # 务必修改！
      name: "my-key"
      scopes: ["read", "execute", "admin"]

security:
  enable_high_risk_tools: false  # 高风险工具默认关闭
  enable_shell_listener: false   # 反弹 Shell 默认关闭
  target_whitelist: []           # 限制可攻击的目标 IP/CIDR
```

也支持环境变量覆盖（双下划线分隔）：

```bash
export KALIMCP_SERVER__PORT=9090
export KALIMCP_SECURITY__COMMAND_TIMEOUT=600
```

### 启动

```bash
# stdio 模式 (本地客户端直连)
kalimcp stdio

# HTTP 模式 (远程 / 多客户端)
kalimcp serve --host 0.0.0.0 --port 8443
```

### systemd 服务

```bash
sudo systemctl enable kalimcp
sudo systemctl start kalimcp
sudo journalctl -u kalimcp -f  # 查看日志
```

---

## 客户端集成

### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "kalimcp": {
      "command": "kalimcp",
      "args": ["stdio"],
      "env": {
        "KALIMCP_AUTH__ENABLED": "false"
      }
    }
  }
}
```

### Warp Agent

Warp 原生支持 MCP — 在 MCP 设置中添加：

```json
{
  "kalimcp": {
    "command": "kalimcp",
    "args": ["stdio"]
  }
}
```
远端配置 MCP（宿主机通过网络连接 Kali 虚拟机）：
```
{
  "kalimcp": {
    "command": "npx",
    "args": [
      "mcp-remote",
      "http://192.168.138.139:8443/mcp",
      "--allow-http"
    ]
  }
}
```

> **注意：** `mcp-remote` 默认要求 HTTPS，连接 HTTP 地址必须加 `--allow-http` 标志。


### Python 客户端

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command="kalimcp", args=["stdio"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 列出工具
            tools = await session.list_tools()

            # 执行 nmap 扫描
            result = await session.call_tool("exec_tool", {
                "tool_name": "nmap",
                "arguments": "-sV -T4 192.168.1.1",
                "timeout": 120,
            })
            print(result.content[0].text)
```

---

## MCP 工具一览

### Tool Engine
| 工具 | 说明 |
|------|------|
| `exec_tool` | 执行任意已注册的 Kali 工具 |
| `list_kali_tools` | 列出可用工具（按分类筛选） |
| `tool_help` | 获取工具帮助信息 |

### Terminal Manager
| 工具 | 说明 |
|------|------|
| `terminal_create` | 创建交互式 PTY 终端会话 |
| `terminal_exec` | 在会话中执行命令 |
| `terminal_read` | 读取终端输出缓冲区 |
| `terminal_send` | 向终端发送原始输入 |
| `terminal_list` | 列出所有活跃会话 |
| `terminal_kill` | 终止会话 |
| `reverse_listener_start` | 启动反弹 Shell 监听器 |
| `reverse_listener_stop` | 停止监听器 |

### CodeForge
| 工具 | 说明 |
|------|------|
| `code_create` | 在工作区创建文件 |
| `code_edit` | 编辑文件 (search-replace) |
| `code_read` | 读取文件内容 |
| `code_exec` | 执行代码 (12 种语言) |
| `code_install_deps` | 安装依赖包 (需开启) |

### Resources
| 资源 URI | 说明 |
|----------|------|
| `kali://system/info` | 系统信息 (OS、内核、内存) |
| `kali://tools/catalog` | 完整工具目录 |
| `kali://network/interfaces` | 网络接口列表 |
| `kali://workspace/{path}` | 工作区文件内容 |

### Prompts
| 名称 | 说明 |
|------|------|
| `pentest_recon` | 信息收集标准流程 |
| `pentest_webapp` | Web 应用渗透测试 |
| `pentest_network` | 内网渗透标准流程 |
| `ctf_solve` | CTF 解题辅助 |
| `incident_response` | 应急响应流程 |
| `vuln_assessment` | 漏洞评估报告 |

---

## 安全设计

### 多层防护

1. **认证层** — API Key + JWT 双模式认证，作用域 (read / execute / admin) 精细控制
2. **输入过滤** — 白名单校验、Shell 元字符拦截、路径穿越防护、参数长度限制
3. **速率限制** — 可配置 RPM 限流，防止滥用
4. **进程隔离** — 信号量控制并发数、超时自动 SIGTERM→SIGKILL、输出大小截断
5. **审计日志** — 所有操作异步写入 JSON Lines 日志，支持按大小自动轮转
6. **高风险隔离** — 高风险工具 / 反弹 Shell / 依赖安装默认关闭，需显式启用

### 危险命令阻断

默认阻断以下危险模式：

- `rm -rf /`
- `mkfs`
- `dd if=/dev/zero`
- Fork 炸弹 `:(){:|:&};:`

可在 `config/default.yaml` 的 `security.blocked_commands` 中自定义。

---

## AI 工作流示例

以下展示 AI 如何使用 KaliMcp 完成一次完整的 Web 渗透测试：

```
用户: 对 192.168.1.100 进行全面的 Web 渗透测试

AI 执行流程:
1. [exec_tool] nmap -sV -sC -p- 192.168.1.100    → 发现 80/443 端口
2. [exec_tool] whatweb 192.168.1.100               → 识别 WordPress 5.x
3. [exec_tool] nikto -h 192.168.1.100              → 发现 XSS + 目录泄露
4. [exec_tool] gobuster dir -u http://...          → 发现 /admin, /backup
5. [exec_tool] sqlmap -u "http://...?id=1"         → 确认 SQL 注入
6. [code_create] report.md                          → 生成渗透测试报告
```

---

## 工具分类

KaliMcp 在 `config/tools_catalog.yaml` 中维护了 **60+ 工具**，覆盖 **12 大安全分类**：

| 分类 | 工具示例 | 风险等级 |
|------|----------|----------|
| **recon** (信息收集) | nmap, whois, dig, theharvester, amass | 🟢 低 |
| **vuln** (漏洞扫描) | nikto, openvas, wpscan | 🟡 中 |
| **webapp** (Web 渗透) | sqlmap, gobuster, ffuf, whatweb, burpsuite | 🟡 中 |
| **password** (密码攻击) | hydra, john, hashcat, medusa | 🔴 高 |
| **wireless** (无线攻击) | aircrack-ng, reaver, wifite | 🔴 高 |
| **exploit** (漏洞利用) | msfconsole, searchsploit | 🔴 高 |
| **sniff** (嗅探/欺骗) | tcpdump, wireshark, ettercap, responder | 🔴 高 |
| **post** (后渗透) | mimikatz, empire, bloodhound | 🔴 高 |
| **forensic** (取证) | volatility, autopsy, binwalk, foremost | 🟢 低 |
| **social** (社工) | setoolkit, gophish | 🔴 高 |
| **crypto** (密码学) | openssl, gpg, hashid, hash-identifier | 🟢 低 |
| **reverse** (逆向) | ghidra, radare2, gdb, objdump | 🟡 中 |

---

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check src/ tests/
```

### 测试覆盖

- `test_security.py` — 输入过滤、危险命令阻断、路径穿越 (17 cases)
- `test_tool_engine.py` — 工具执行、目录查询、权限校验 (11 cases)
- `test_terminal.py` — PTY 会话、ANSI 清理、会话生命周期 (9 cases)
- `test_codeforge.py` — 文件操作、代码执行、路径安全 (7 cases)

---

## 许可证

[MIT License](LICENSE)

---

## 🎵 Vibe Coding

本项目 **100% 由 Vibe Coding 开发** — 全部代码、配置、测试和文档均由 AI 在人类自然语言指导下生成，未手动编写任何一行代码。这是 AI 辅助开发范式的一次完整实践。

---

## ⚠️ 免责声明

本项目仅供 **合法的安全测试和教育目的** 使用。使用者必须：

1. 获得目标系统的明确授权
2. 遵守当地法律法规
3. 仅在授权范围内使用

**未经授权对计算机系统进行渗透测试是违法行为，作者不承担任何因滥用本工具而导致的法律责任。**
