"""Pre-built security testing workflow templates (MCP Prompts)."""

from __future__ import annotations

_PROMPTS: dict[str, str] = {
    "pentest_recon": """# 信息收集标准流程 — Reconnaissance Workflow

## 目标
对指定目标进行全面的信息收集，为后续渗透测试提供基础数据。

## 步骤

### 1. 被动信息收集
- 使用 `recon_whois` 查询域名注册信息
- 使用 `recon_dig` 枚举 DNS 记录 (A, AAAA, MX, NS, TXT)
- 使用 `recon_theharvester` 收集邮箱和子域名

### 2. 主动扫描
- 使用 `recon_nmap` 进行快速端口扫描 (scan_type="quick")
- 对发现的开放端口进行服务版本识别 (scan_type="service")
- 如需要，进行操作系统检测 (scan_type="os")

### 3. Web 资产识别
- 使用 `webapp_whatweb` 识别 Web 技术栈
- 使用 `webapp_gobuster` 进行目录枚举

### 4. 整理报告
- 汇总所有发现：IP、端口、服务、版本、域名、子域名
- 标记潜在攻击面
- 使用 `code_create` 生成结构化报告

## 涉及工具
nmap, whois, dig, theHarvester, whatweb, gobuster
""",

    "pentest_webapp": """# Web 应用渗透测试工作流

## 目标
对 Web 应用进行全面安全测试，发现常见漏洞。

## 步骤

### 1. 信息收集
- `webapp_whatweb` — 识别技术栈和框架
- `webapp_gobuster` — 目录和文件枚举
- `recon_nmap` (scan_type="service") — 服务版本识别

### 2. 漏洞扫描
- `vuln_nikto` — Web 服务器漏洞扫描
- 如果是 WordPress：`vuln_wpscan` — WordPress 专项扫描

### 3. 注入测试
- `webapp_sqlmap` — SQL 注入检测
- 手动检查 XSS、CSRF、SSRF 等

### 4. 模糊测试
- `webapp_ffuf` — 参数和路径模糊测试

### 5. 报告
- 记录所有发现的漏洞
- 评估风险等级
- 提供修复建议

## 涉及工具
whatweb, gobuster, nikto, wpscan, sqlmap, ffuf, nmap
""",

    "pentest_network": """# 内网渗透标准流程

## 目标
在获得初始访问后，进行内网横向移动和权限提升。

## 步骤

### 1. 内网信息收集
- `recon_nmap` — 扫描内网存活主机和服务
- `exec_tool("enum4linux", ...)` — Windows/Samba 枚举

### 2. 漏洞利用
- 根据发现的服务版本搜索已知漏洞
- `exploit_searchsploit` — 搜索 Exploit-DB
- 使用 Terminal Manager 操作 Metasploit

### 3. 权限提升
- Linux: 运行 linpeas 检查提权向量
- Windows: 检查服务配置、计划任务、弱权限

### 4. 横向移动
- 使用获取的凭据尝试访问其他主机
- 使用 `password_hydra` 进行凭据测试

### 5. 数据收集与报告
- 记录所有获得访问的系统
- 评估影响范围
- 生成渗透测试报告

## 涉及工具
nmap, enum4linux, searchsploit, msfconsole, hydra, linpeas
""",

    "ctf_solve": """# CTF 解题辅助工作流

## 流程

### 1. 题目分析
- 阅读题目描述，识别类别 (Web, Pwn, Crypto, Forensic, Misc, Reverse)
- 下载相关文件

### 2. 按类别使用工具

#### Web 题
- `webapp_gobuster` — 目录枚举
- `webapp_sqlmap` — SQL 注入
- 手动检查源码、Cookie、HTTP Header

#### Forensic 题
- `forensic_binwalk` — 分析文件结构
- `forensic_exiftool` — 查看元数据
- `forensic_steghide` — 隐写提取
- `exec_tool("strings", ...)` — 提取字符串

#### Crypto 题
- `crypto_hashid` — 识别哈希类型
- `code_create` + `code_execute` — 编写解密脚本

#### Reverse 题
- `reverse_objdump` — 反汇编
- `reverse_strings` — 提取字符串
- `reverse_file` — 文件类型识别

### 3. 提交 Flag
- 验证 flag 格式
- 记录解题过程

## 涉及工具
gobuster, sqlmap, binwalk, exiftool, steghide, hashid, objdump, strings, file
""",

    "incident_response": """# 应急响应流程

## 目标
快速定位安全事件的影响范围并进行遏制。

## 步骤

### 1. 初步评估
- 确认事件类型（入侵、恶意软件、数据泄露等）
- `recon_nmap` — 快速扫描受影响网段
- 查看系统日志

### 2. 证据收集
- 使用 `terminal_create` 创建终端进行实时分析
- 收集网络流量：`sniff_tcpdump` 或 `sniff_tshark`
- 文件分析：`forensic_binwalk`, `forensic_exiftool`
- 进程分析：`exec_tool("ps", "auxf")`

### 3. 恶意指标识别 (IoC)
- 可疑 IP/域名
- 可疑文件哈希
- 异常进程和网络连接

### 4. 遏制
- 隔离受影响系统
- 阻断恶意通信

### 5. 恢复与报告
- 使用 `code_create` 编写恢复脚本
- 生成事件报告

## 涉及工具
nmap, tcpdump, tshark, binwalk, exiftool, terminal commands
""",

    "vuln_assessment": """# 漏洞评估报告工作流

## 目标
对目标系统进行全面漏洞评估并生成结构化报告。

## 步骤

### 1. 资产发现
- `recon_nmap` (scan_type="full") — 全端口扫描
- 记录所有开放端口和服务版本

### 2. 漏洞扫描
- `vuln_nikto` — Web 漏洞扫描
- `recon_nmap` (scan_type="vuln") — nmap 漏洞脚本扫描
- 对已知服务版本搜索 CVE

### 3. 漏洞验证
- 对扫描发现的漏洞进行手动验证
- 确认误报

### 4. 风险评级
- 按 CVSS 评分分级
- 评估业务影响

### 5. 报告生成
- 使用 `code_create` 编写报告生成脚本
- 输出包含：漏洞详情、风险等级、修复建议、时间线

## 涉及工具
nmap, nikto, searchsploit, code_create, code_execute
""",
}


def get_prompt(name: str) -> str:
    """Return prompt template by name, or an error message."""
    if name in _PROMPTS:
        return _PROMPTS[name]
    available = ", ".join(_PROMPTS.keys())
    return f"Error: Unknown prompt '{name}'. Available prompts: {available}"


def list_prompts() -> list[str]:
    """Return all available prompt names."""
    return list(_PROMPTS.keys())
