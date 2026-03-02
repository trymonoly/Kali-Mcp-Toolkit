# KaliMcp 功能实现任务报告

> 基于 README.md 架构文档拆分，用于开发进度同步与验收管理

---

## 任务字段约定

每条任务建议在项目管理工具（Jira/飞书/Notion）中维护以下字段：

- **任务ID**：唯一标识（如 M1-01）
- **优先级**：P0 必须 / P1 重要 / P2 增强
- **状态**：Todo / Doing / Blocked / Done
- **负责人**、**预计工时**
- **依赖任务ID**
- **验收标准**：必须可验证
- **关联模块/文件**
- **测试覆盖**：单测/集测/E2E

---

## 里程碑总览与关键路径

### M1 / Phase 1 — MVP 基础框架（P0，1-2 周）

关键路径：配置 → 安全校验 → 进程执行 → `exec_tool` → Server 启动 → Inspector 集测

### M2 / Phase 2 — 终端管理（P1，1-2 周）

关键路径：ANSI 清洗 → PTY Session → Manager → MCP Tools → 超时回收

### M3 / Phase 3 — CodeForge + 高频工具结构化封装（P1，1-2 周）

关键路径：Workspace → 文件编辑 → 执行器 → 输出解析 → Top 工具封装

### M4 / Phase 4 — 生产化（P2，1 周）

Resources / Prompts、TLS、速率限制、部署脚本、完整文档

---

## M1（P0）基础框架与 Tool Engine

### M1-01 项目可执行入口与启动形态

- **模块/文件**：`pyproject.toml`，`src/kalimcp/server.py`
- **依赖**：无
- **工作内容**：
  - 配置 CLI entrypoint：`kalimcp serve`（HTTP）与 `kalimcp stdio`（本地）
  - 支持 `--host / --port / --config / --reload` 参数
  - uvicorn 集成，开发模式支持热重载
- **验收标准**：
  - [ ] 本地可启动并监听 MCP Streamable HTTP endpoint
  - [ ] stdio 模式可被 MCP 客户端初始化并列出工具
  - [ ] `--help` 输出完整参数说明

---

### M1-02 配置系统（YAML → Pydantic v2）

- **模块/文件**：`src/kalimcp/config.py`，`config/default.yaml`
- **依赖**：无
- **工作内容**：
  - 定义 Pydantic v2 配置模型：ServerConfig / AuthConfig / SecurityConfig / WorkspaceConfig / LoggingConfig
  - YAML 加载 → Pydantic 校验
  - 支持环境变量覆盖（推荐）
  - 配置单例管理（全局可获取）
- **验收标准**：
  - [ ] 配置缺失/类型错误时报错清晰（含字段路径）
  - [ ] `default.yaml` 可完整加载为类型安全对象
  - [ ] 环境变量可覆盖 YAML 中的值

---

### M1-03 Kali 工具目录（catalog）与数据模型

- **模块/文件**：`config/tools_catalog.yaml`，`src/kalimcp/tools/__init__.py`
- **依赖**：M1-02
- **工作内容**：
  - 设计 `KaliToolInfo` 数据模型：工具名、分类前缀、描述、是否允许执行、风险级别、默认参数模板
  - 12 个分类：recon / vuln / webapp / password / wireless / exploit / sniff / post / forensic / social / crypto / reverse
  - catalog YAML 加载与内存缓存
  - 工具存在性校验接口（供 exec_tool 调用）
- **验收标准**：
  - [ ] 可按分类读取工具列表
  - [ ] catalog 中不存在的工具无法被执行（与 M1-06 联动）
  - [ ] 数据模型有完整的类型定义

---

### M1-04 认证与授权（API Key + scopes）

- **模块/文件**：`src/kalimcp/auth.py`
- **依赖**：M1-02
- **工作内容**：
  - 解析 HTTP Header `Authorization: Bearer <key>`
  - API Key 配置：name + scopes（read / execute / admin）
  - 在 MCP Tool 调用前做 scope 校验（中间件或装饰器）
  - stdio 模式下的认证策略（可跳过或使用本地 Key）
  - 可选扩展：JWT 支持（带过期时间）
- **验收标准**：
  - [ ] 未认证请求返回 401
  - [ ] scope 不足返回 403
  - [ ] 认证上下文（key name / scopes）可传递给审计模块
  - [ ] stdio 模式不因认证阻塞

---

### M1-05 审计日志（JSON Lines）

- **模块/文件**：`src/kalimcp/utils/audit.py`
- **依赖**：M1-02，M1-04
- **工作内容**：
  - 统一审计事件模型：timestamp / api_key_name / action / module（tool/terminal/codeforge）/ params_summary / result_summary / duration_ms / source_ip
  - 异步写入 JSON Lines 文件（路径来自配置）
  - 日志轮转策略（按大小或按天）
- **验收标准**：
  - [ ] 任一 MCP Tool 调用都会产生审计事件
  - [ ] 日志格式为 JSON Lines，结构稳定
  - [ ] 不因审计写入阻塞主流程

---

### M1-06 输入清洗与安全防护

- **模块/文件**：`src/kalimcp/utils/sanitizer.py`
- **依赖**：M1-02，M1-03
- **工作内容**：
  - **工具白名单**：只允许 catalog 中已注册工具
  - **参数校验**：禁止危险 shell 拼接，核心原则 → `subprocess` 不走 `shell=True`
  - **破坏性命令拦截**：模式匹配 `rm -rf /`、`mkfs`、`dd if=/dev/zero`、fork bomb 等
  - **路径穿越防护**：workspace 外路径一律拒绝（含符号链接解析）
  - **参数长度限制**：防止超长参数消耗资源
- **验收标准**：
  - [ ] 命令注入样例被拒绝（有单测覆盖）
  - [ ] 路径穿越样例被拒绝（含 `../`、符号链接）
  - [ ] 合法命令参数可正常通过（不过度误杀）
  - [ ] 黑名单命令返回明确错误信息

---

### M1-07 异步进程执行器

- **模块/文件**：`src/kalimcp/utils/process.py`
- **依赖**：M1-06
- **工作内容**：
  - 基于 `asyncio.create_subprocess_exec` 执行外部工具
  - 超时终止策略：SIGTERM → 等待 → SIGKILL
  - 并发上限（默认 10）与排队/拒绝机制（Semaphore）
  - stdout / stderr 采集，输出大小限制（防止 OOM）
  - 资源限制：通过 `resource.setrlimit` 或 `prlimit` 设置 CPU / 内存上限
- **验收标准**：
  - [ ] 超时任务可被可靠终止，返回可辨识的超时错误
  - [ ] 并发不超过配置上限（压测或单测验证）
  - [ ] 超大输出被截断而非打爆内存

---

### M1-08 Tool Engine：`exec_tool` 通用执行接口

- **模块/文件**：`src/kalimcp/tools/tool_engine.py`
- **依赖**：M1-04，M1-05，M1-06，M1-07
- **工作内容**：
  - 实现 MCP Tool：`exec_tool(tool_name, arguments, timeout, output_format)`
  - 调用链：鉴权 → 白名单校验 → 参数清洗 → 进程执行 → 输出处理 → 审计记录
  - `output_format` 支持 text / json / xml（按工具能力选择）
- **验收标准**：
  - [ ] 可执行合法工具（如 `nmap` 基础扫描）并返回结果
  - [ ] 非白名单工具被拒绝且有审计记录
  - [ ] 危险参数被拦截且有审计记录
  - [ ] 超时和错误有明确返回

---

### M1-09 Tool Engine：工具发现与帮助

- **模块/文件**：`src/kalimcp/tools/tool_engine.py`
- **依赖**：M1-03，M1-04，M1-05
- **工作内容**：
  - `list_kali_tools(category)` — 按分类或全部列出，返回 `list[KaliToolInfo]`
  - `tool_help(tool_name)` — 优先 `--help`，回退 `man`，输出清洗与截断
- **验收标准**：
  - [ ] list 返回结构化工具信息，支持按 12 个分类过滤
  - [ ] help 输出被截断/清洗，避免超大文本
  - [ ] 不存在的工具返回明确错误

---

### M1-10 MCP Server 组装与注册

- **模块/文件**：`src/kalimcp/server.py`
- **依赖**：M1-02，M1-04，M1-08，M1-09
- **工作内容**：
  - FastMCP server 初始化
  - 注册 Tool Engine 的所有 MCP Tool
  - HTTP 传输（uvicorn + Streamable HTTP）与 stdio 传输双模式
  - 认证中间件挂载
- **验收标准**：
  - [ ] MCP Inspector 可连通
  - [ ] `tools/list` 返回所有已注册工具
  - [ ] 可成功调用 `exec_tool` 并获得结果
  - [ ] stdio 模式同样可用

---

### M1-11 Phase 1 测试基线

- **模块/文件**：`tests/test_tool_engine.py`，`tests/test_security.py`
- **依赖**：M1-06，M1-07，M1-08，M1-09
- **工作内容**：
  - 安全校验测试：命令注入、黑名单拦截、白名单校验、路径穿越
  - 进程执行器测试：超时终止、并发限制、输出截断
  - Tool Engine 测试：正常执行、错误码、输出格式
  - 工具发现测试：分类过滤、help 截断
- **验收标准**：
  - [ ] `pytest` 一键跑通全部测试
  - [ ] 核心安全逻辑 100% 有覆盖
  - [ ] 无偶现失败

---

## M2（P1）Terminal Manager

### M2-01 ANSI 转义码清洗

- **模块/文件**：`src/kalimcp/terminal/ansi.py`
- **依赖**：无
- **工作内容**：
  - 清洗 ANSI 转义码：颜色、光标移动、清屏、滚动等
  - 输出纯文本，保留有意义的换行与空格
- **验收标准**：
  - [ ] 输出无残留转义序列
  - [ ] 文本内容可读且格式合理
  - [ ] 覆盖常见终端程序（bash/zsh/metasploit）输出

---

### M2-02 PTY Session 基础能力

- **模块/文件**：`src/kalimcp/terminal/pty_session.py`
- **依赖**：M2-01
- **工作内容**：
  - `pty.openpty()` + `asyncio.subprocess` 创建独立伪终端
  - 异步读写接口
  - `wait_for` 机制：基于正则匹配等待特定输出模式
  - 可配置 cols / rows（终端尺寸）
- **验收标准**：
  - [ ] 可创建 bash 会话并执行命令
  - [ ] 可驱动交互式程序（如 python REPL）
  - [ ] `wait_for` 可正确匹配输出模式并返回

---

### M2-03 Ring Buffer（环形缓冲区）

- **模块/文件**：`src/kalimcp/terminal/pty_session.py`（或独立 util）
- **依赖**：M2-02
- **工作内容**：
  - 环形缓冲区实现，保留最近 10,000 行
  - 支持按行数读取最近输出
  - 线程安全（asyncio 场景下的并发读写）
- **验收标准**：
  - [ ] 超过容量后正确覆盖旧数据
  - [ ] 不阻塞正常读写
  - [ ] 内存占用可控

---

### M2-04 Terminal Manager（多会话管理）

- **模块/文件**：`src/kalimcp/terminal/manager.py`
- **依赖**：M2-02，M2-03，M1-05
- **工作内容**：
  - 会话生命周期：create / list / kill
  - 最大并发会话数限制（默认 20）
  - 会话元数据：session_id / name / shell / created_at / last_active_at
  - 所有管理操作进入审计日志
- **验收标准**：
  - [ ] 可同时管理多个独立会话
  - [ ] 超出上限时拒绝创建，返回明确错误
  - [ ] kill 可正确释放子进程与 PTY 资源

---

### M2-05 MCP Tools：terminal_* 系列注册

- **模块/文件**：`src/kalimcp/terminal/manager.py`，`src/kalimcp/server.py`
- **依赖**：M2-04，M1-04
- **工作内容**：
  - 注册 MCP Tool：`terminal_create / terminal_exec / terminal_read / terminal_send_input / terminal_list / terminal_kill`
  - `terminal_exec` 加超时与输出限制
  - 权限校验：execute scope
- **验收标准**：
  - [ ] MCP Inspector 可完成完整链路：创建 → 执行 → 读取 → 销毁
  - [ ] 未授权请求被拒绝
  - [ ] 不存在的 session_id 返回明确错误

---

### M2-06 会话超时回收

- **模块/文件**：`src/kalimcp/terminal/manager.py`
- **依赖**：M2-04
- **工作内容**：
  - 后台定时任务：检测并清理超过 `session_timeout`（默认 30 分钟）无操作的会话
  - 释放子进程与 PTY 资源
  - 超时回收事件记录审计
- **验收标准**：
  - [ ] 超时时间可通过配置调整
  - [ ] 超时会话被自动释放（含所有子进程）
  - [ ] 回收事件有审计记录

---

### M2-07 Shell Listener（反弹 Shell 监听器）

- **模块/文件**：`src/kalimcp/terminal/listener.py`
- **依赖**：M2-04，M1-04，M1-06，M1-05
- **⚠️ 高风险能力，建议默认关闭**
- **工作内容**：
  - `shell_listener_start(port, protocol, handler)` — 启动监听器
  - `shell_listener_list()` — 列出活跃监听器
  - 安全约束：
    - 必须 admin scope
    - 绑定地址限制（仅内网/VPN）
    - 端口白名单
    - 强审计记录
    - 功能开关默认关闭
- **验收标准**：
  - [ ] 功能开关关闭时，调用返回明确错误
  - [ ] 开启后需 admin scope 才能操作
  - [ ] 启动/停止均记录审计
  - [ ] 端口/地址受限

---

### M2-08 终端模块测试

- **模块/文件**：`tests/test_terminal.py`
- **依赖**：M2-05，M2-06
- **工作内容**：
  - 交互式执行测试
  - `wait_for` 正则匹配测试
  - ANSI 清洗测试（多种终端程序输出样本）
  - 超时回收测试
  - 会话上限测试
- **验收标准**：
  - [ ] 测试稳定可重复（无偶现失败）
  - [ ] 覆盖核心生命周期与边界场景

---

## M3（P1）CodeForge + 高频工具结构化封装

### M3-01 Workspace 管理

- **模块/文件**：`src/kalimcp/codeforge/workspace.py`
- **依赖**：M1-02，M1-06
- **工作内容**：
  - 工作空间根目录：`/opt/kalimcp/workspace/`（来自配置）
  - 子目录组织策略（按任务/时间），规则文档化
  - 文件大小限制（默认 50MB）
  - 路径安全校验（含符号链接解析 `realpath`）
- **验收标准**：
  - [ ] 任何文件操作越界直接拒绝
  - [ ] 符号链接穿越被阻止
  - [ ] 超出文件大小限制时返回明确错误

---

### M3-02 文件创建/编辑/读取

- **模块/文件**：`src/kalimcp/codeforge/editor.py`
- **依赖**：M3-01，M1-05
- **工作内容**：
  - `code_create(file_path, content, language, executable)` — 创建文件/脚本
  - `code_edit(file_path, edits)` — search/replace patch 列表编辑
  - `code_read(file_path, start_line, end_line)` — 按行读取
  - 可执行位设置（`chmod +x`）
  - 所有操作记录审计
- **验收标准**：
  - [ ] 创建、修改、读取文件均正常工作
  - [ ] 编辑操作的 search 不匹配时返回明确错误
  - [ ] 有审计记录

---

### M3-03 代码执行器

- **模块/文件**：`src/kalimcp/codeforge/executor.py`
- **依赖**：M1-07，M3-01
- **工作内容**：
  - `code_execute(file_path, args, timeout, stdin_data)` — 执行脚本/程序
  - 解释器选择策略：按文件扩展名（.py → python3, .sh → bash, .rb → ruby 等）或显式 language 参数
  - 输出限制与超时复用 M1-07 进程执行器
  - 返回 `ExecutionResult`：exit_code / stdout / stderr / duration
- **验收标准**：
  - [ ] Python / Bash 脚本可执行
  - [ ] 超时可控，超时后进程被终止
  - [ ] stdin_data 可正确传入
  - [ ] 返回结构化执行结果

---

### M3-04 依赖安装（⚠️ 高风险，需 admin scope）

- **模块/文件**：`src/kalimcp/codeforge/executor.py`
- **依赖**：M1-04，M1-06，M1-05
- **工作内容**：
  - `code_install_deps(packages, manager)` — 支持 pip / apt / npm / gem / go
  - 包名格式校验（防注入）
  - 必须 admin scope
  - 建议默认关闭（功能开关）
  - 强审计记录
- **验收标准**：
  - [ ] 非 admin scope 返回 403
  - [ ] 功能开关关闭时返回明确错误
  - [ ] 合法包名可安装并记录审计
  - [ ] 非法包名（含特殊字符）被拒绝

---

### M3-05 工具输出解析器

- **模块/文件**：`src/kalimcp/utils/parser.py`
- **依赖**：M1-07
- **工作内容**：
  - nmap XML → 结构化模型（hosts / ports / services / os_detection）
  - 通用解析框架：text / json / xml 输出自动识别
  - 超长输出截断策略（保留头尾 + 摘要）
  - 解析失败时返回原始片段（受限长度）+ 错误信息
- **验收标准**：
  - [ ] nmap XML 解析稳定，覆盖常见扫描类型
  - [ ] 解析失败不崩溃，返回可定位的错误
  - [ ] 超长输出被合理截断

---

### M3-06 高频低风险工具结构化封装

- **模块/文件**：`src/kalimcp/tools/recon.py`，`src/kalimcp/tools/vuln.py`，`src/kalimcp/tools/webapp.py`
- **依赖**：M1-08，M3-05
- **优先封装清单**（信息收集/资产探测类）：
  - `recon_nmap` — 网络扫描（quick/full/vuln/os/service 模式）
  - `recon_whois` — 域名信息查询
  - `recon_dig` — DNS 查询
  - `recon_theharvester` — 邮箱/子域名收集
  - `vuln_nikto` — Web 服务器漏洞扫描
  - `webapp_gobuster` — 目录/文件爆破
  - `webapp_sqlmap` — SQL 注入检测
- **工作内容**：
  - 每个工具：结构化输入参数 + Pydantic 输出模型
  - 内部调用 `exec_tool` 或直接调用进程执行器
  - 输出经过对应解析器处理
- **验收标准**：
  - [ ] 调用不需要手写长命令行参数
  - [ ] 返回字段稳定，可被上层工作流消费
  - [ ] 每个封装有基本的集成测试

---

### M3-07 高风险工具封装（密码攻击/利用框架等）

- **模块/文件**：`src/kalimcp/tools/password.py`，`src/kalimcp/tools/exploit.py`，`src/kalimcp/tools/wireless.py`，`src/kalimcp/tools/sniff.py`，`src/kalimcp/tools/post_exploit.py`，`src/kalimcp/tools/forensic.py`，`src/kalimcp/tools/social.py`，`src/kalimcp/tools/crypto.py`，`src/kalimcp/tools/reverse.py`
- **依赖**：M1-04，M1-06，M1-05，M1-07
- **⚠️ 建议实现但默认关闭**
- **工作内容**：
  - 按需实现各分类的高频工具封装
  - 额外安全约束：
    - 功能开关默认关闭
    - 必须 admin scope
    - 目标范围白名单（可配置允许的 IP/网段）
    - 更严格的速率与并发限制
    - 强审计记录
- **验收标准**：
  - [ ] 功能开关关闭时不可调用
  - [ ] 开启后必须通过目标/参数策略校验
  - [ ] 所有调用有完整审计

---

### M3-08 CodeForge 与工具封装测试

- **模块/文件**：`tests/test_codeforge.py`，`tests/test_tools_*.py`
- **依赖**：M3-02，M3-03，M3-05，M3-06
- **工作内容**：
  - Workspace 路径限制测试
  - 文件创建/编辑正确性测试
  - 代码执行超时测试
  - 输出解析正确性测试（含异常输入）
  - 结构化工具封装集成测试
- **验收标准**：
  - [ ] 核心链路有可重复的自动化测试
  - [ ] 安全相关场景有覆盖

---

## M4（P2）生产化

### M4-01 MCP Resources

- **模块/文件**：`src/kalimcp/resources/system.py`
- **依赖**：M1-02，M1-03，M3-01
- **工作内容**：
  - `kali://system/info` — 系统版本、内核、已安装工具数量
  - `kali://tools/catalog` — 完整工具目录及分类
  - `kali://network/interfaces` — 网络接口信息（名称/IP/MAC/状态）
  - `kali://workspace/{path}` — 工作空间文件内容
- **验收标准**：
  - [ ] 可通过 MCP Resource 协议访问所有 4 类资源
  - [ ] 返回结构化 JSON 数据
  - [ ] workspace resource 受路径安全限制

---

### M4-02 MCP Prompts：工作流模板库

- **模块/文件**：`src/kalimcp/prompts/workflows.py`
- **依赖**：M1-09，M3-06，M2-05
- **工作内容**：
  - 预置模板：
    - `pentest_recon` — 信息收集标准流程
    - `pentest_webapp` — Web 应用渗透测试
    - `pentest_network` — 内网渗透标准流程
    - `ctf_solve` — CTF 解题辅助
    - `incident_response` — 应急响应流程
    - `vuln_assessment` — 漏洞评估报告
  - 每个模板：描述、步骤、涉及工具、参数模板
- **验收标准**：
  - [ ] 模板可被 MCP Prompt 协议列出与读取
  - [ ] 步骤中引用的工具在系统中均已注册
  - [ ] 模板内容对 AI 友好（清晰、可执行）

---

### M4-03 速率限制与任务排队

- **模块/文件**：中间件层（`src/kalimcp/auth.py` 或独立 `src/kalimcp/middleware.py`）
- **依赖**：M1-04，M1-07
- **工作内容**：
  - 每分钟最大请求数限制（默认 60，可配置）
  - 按 API Key 独立计数
  - 大任务排队策略（队列上限 + 拒绝策略）
  - 返回标准 429 Too Many Requests + Retry-After header
- **验收标准**：
  - [ ] 超限返回 429
  - [ ] 队列不会无限增长（有上限与拒绝策略）
  - [ ] 不同 API Key 独立限速

---

### M4-04 TLS 支持

- **模块/文件**：`src/kalimcp/server.py`，`config/default.yaml`
- **依赖**：M1-10
- **工作内容**：
  - 支持配置 SSL 证书路径（cert_file / key_file）
  - uvicorn SSL 参数传递
  - 文档说明自签名证书生成方法
- **验收标准**：
  - [ ] 配置证书后可 HTTPS 启动
  - [ ] 无证书时仍可 HTTP 启动（开发模式）
  - [ ] 文档说明清晰

---

### M4-05 systemd 服务与部署脚本

- **模块/文件**：`deploy/kalimcp.service`，`scripts/install.sh`
- **依赖**：M4-04
- **工作内容**：
  - systemd service 文件模板
  - 安装脚本：创建目录、虚拟环境、安装依赖、生成 API Key、配置服务
  - 健康检查命令
- **验收标准**：
  - [ ] 按文档可一键部署
  - [ ] 服务开机自启
  - [ ] `systemctl status kalimcp` 可查看健康状态
  - [ ] 日志可通过 `journalctl` 查看

---

### M4-06 完整文档与接入示例

- **模块/文件**：`README.md`（更新），可选 `docs/` 目录
- **依赖**：全功能基本完成
- **工作内容**：
  - 部署指南（含 TLS 配置）
  - 配置参考文档（所有字段说明）
  - 客户端接入指南：Claude Desktop / Warp Agent / 自定义 Python 客户端
  - API 参考：所有 MCP Tool / Resource / Prompt 的参数与返回值
  - 安全最佳实践
  - 常见问题排查
- **验收标准**：
  - [ ] 新人可按文档完成：部署 → 配置 → Inspector 验证 → 客户端接入
  - [ ] 所有公开接口有文档说明

---

## 并行开发建议

根据依赖关系，可按以下方式分配并行开发：

### 开发线 A — 平台主线（P0 关键路径）

M1-02 → M1-04 → M1-05 → M1-06 → M1-07 → M1-08 → M1-10 → M1-11

### 开发线 B — 工具目录与封装

M1-03 → M1-09 → M3-05 → M3-06 → M3-07

### 开发线 C — 终端管理

M2-01 → M2-02 → M2-03 → M2-04 → M2-05 → M2-06 → M2-07 → M2-08

### 开发线 D — CodeForge

M3-01 → M3-02 → M3-03 → M3-04 → M3-08

### 开发线 E — 生产化

M4-01 → M4-02 → M4-03 → M4-04 → M4-05 → M4-06

> **注意**：开发线 B/C/D 均依赖开发线 A 的 M1-02 ~ M1-07 完成后才能完全启动；开发线 E 依赖 M1-M3 大部分完成。

---

## 任务依赖关系图（简化）

```
M1-02 ──┬── M1-03 ──── M1-09
        ├── M1-04 ──── M1-05
        └── M1-06 ──── M1-07 ──── M1-08 ──── M1-10 ──── M1-11
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
                 M2-04          M3-01           M3-05
                   │              │               │
                 M2-05          M3-02           M3-06
                   │              │               │
                 M2-06          M3-03           M3-07
                   │              │
                 M2-07          M3-04
                   │              │
                 M2-08          M3-08
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼              ▼
                 M4-01         M4-02          M4-03
                                                │
                                              M4-04
                                                │
                                              M4-05
                                                │
                                              M4-06
```

---

## 总计

- **M1**：11 个任务（P0，基础框架必须全部完成）
- **M2**：8 个任务（P1，终端管理）
- **M3**：8 个任务（P1，CodeForge + 工具封装）
- **M4**：6 个任务（P2，生产化）
- **合计**：**33 个任务**
