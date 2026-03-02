"""KaliMcp Server — FastMCP assembly, tool registration, CLI entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from kalimcp import __version__
from kalimcp.config import get_config, init_config

# ---------------------------------------------------------------------------
# Lifespan — start/stop shared services
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """Initialise audit logger and other singletons."""
    from kalimcp.utils.audit import get_audit_logger

    audit = get_audit_logger()
    await audit.start()
    yield {}
    await audit.stop()


# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "kalimcp",
    lifespan=_lifespan,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


# ---------------------------------------------------------------------------
# Helper: resolve auth context from MCP request context
# ---------------------------------------------------------------------------


def _auth_from_ctx(ctx: Context | None = None):
    """Best-effort extraction of AuthContext.

    In stdio mode we return a full-access context.
    """
    from kalimcp.auth import AuthContext

    # Default — stdio / unauthenticated
    return AuthContext(key_name="stdio_local", scopes=["read", "execute", "admin"], is_stdio=True)


# ===================================================================
# MCP TOOLS — Tool Engine
# ===================================================================


@mcp.tool(
    name="exec_tool",
    annotations={
        "title": "Execute Kali Tool",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def mcp_exec_tool(
    tool_name: str,
    arguments: str = "",
    timeout: int = 300,
    output_format: str = "text",
) -> str:
    """Execute any registered Kali tool and return the output.

    Args:
        tool_name: Kali tool binary name (e.g. 'nmap', 'nikto')
        arguments: Command-line arguments string
        timeout: Maximum execution time in seconds (default 300)
        output_format: Output format — 'text', 'json', or 'xml'
    """
    from kalimcp.tools.tool_engine import exec_tool

    return await exec_tool(tool_name, arguments, timeout, output_format, _auth=_auth_from_ctx())


@mcp.tool(
    name="list_kali_tools",
    annotations={
        "title": "List Kali Tools",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def mcp_list_kali_tools(category: str = "all") -> str:
    """List available Kali tools, optionally filtered by category.

    Categories: recon, vuln, webapp, password, wireless, exploit, sniff, post, forensic, social, crypto, reverse

    Args:
        category: Category filter or 'all'
    """
    from kalimcp.tools.tool_engine import list_kali_tools

    return await list_kali_tools(category, _auth=_auth_from_ctx())


@mcp.tool(
    name="tool_help",
    annotations={
        "title": "Tool Help",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def mcp_tool_help(tool_name: str) -> str:
    """Get usage / help text for a specific Kali tool (--help or man).

    Args:
        tool_name: Tool binary name
    """
    from kalimcp.tools.tool_engine import tool_help

    return await tool_help(tool_name, _auth=_auth_from_ctx())


# ===================================================================
# MCP TOOLS — Terminal Manager
# ===================================================================


@mcp.tool(
    name="terminal_create",
    annotations={"title": "Create Terminal", "readOnlyHint": False, "destructiveHint": False},
)
async def mcp_terminal_create(
    name: str = "",
    shell: str = "/bin/bash",
    cols: int = 120,
    rows: int = 40,
) -> str:
    """Create a new interactive PTY terminal session.

    Args:
        name: Human-readable session name
        shell: Shell binary path
        cols: Terminal width
        rows: Terminal height
    """
    from kalimcp.terminal.manager import get_terminal_manager

    mgr = get_terminal_manager()
    session = await mgr.create(name=name, shell=shell, cols=cols, rows=rows)
    return session


@mcp.tool(
    name="terminal_exec",
    annotations={"title": "Terminal Execute", "readOnlyHint": False, "destructiveHint": False},
)
async def mcp_terminal_exec(
    session_id: str,
    command: str,
    wait_for: str = "",
    timeout: int = 30,
) -> str:
    """Execute a command in an existing terminal session.

    Args:
        session_id: Session ID from terminal_create
        command: Command to execute
        wait_for: Regex pattern to wait for in output
        timeout: Seconds to wait
    """
    from kalimcp.terminal.manager import get_terminal_manager

    mgr = get_terminal_manager()
    return await mgr.exec_command(session_id, command, wait_for=wait_for, timeout=timeout)


@mcp.tool(
    name="terminal_read",
    annotations={"title": "Read Terminal", "readOnlyHint": True, "destructiveHint": False},
)
async def mcp_terminal_read(session_id: str, lines: int = 50) -> str:
    """Read the latest output from a terminal session buffer.

    Args:
        session_id: Session ID
        lines: Number of recent lines to return
    """
    from kalimcp.terminal.manager import get_terminal_manager

    mgr = get_terminal_manager()
    return await mgr.read_output(session_id, lines=lines)


@mcp.tool(
    name="terminal_send_input",
    annotations={"title": "Send Terminal Input", "readOnlyHint": False, "destructiveHint": False},
)
async def mcp_terminal_send_input(
    session_id: str,
    data: str,
    press_enter: bool = True,
) -> str:
    """Send raw input to a terminal session (for interactive programs).

    Args:
        session_id: Session ID
        data: Text to send
        press_enter: Append newline after data
    """
    from kalimcp.terminal.manager import get_terminal_manager

    mgr = get_terminal_manager()
    return await mgr.send_input(session_id, data, press_enter=press_enter)


@mcp.tool(
    name="terminal_list",
    annotations={"title": "List Terminals", "readOnlyHint": True, "destructiveHint": False},
)
async def mcp_terminal_list() -> str:
    """List all active terminal sessions."""
    from kalimcp.terminal.manager import get_terminal_manager

    mgr = get_terminal_manager()
    return await mgr.list_sessions()


@mcp.tool(
    name="terminal_kill",
    annotations={"title": "Kill Terminal", "readOnlyHint": False, "destructiveHint": True},
)
async def mcp_terminal_kill(session_id: str) -> str:
    """Destroy a terminal session and free resources.

    Args:
        session_id: Session ID to kill
    """
    from kalimcp.terminal.manager import get_terminal_manager

    mgr = get_terminal_manager()
    return await mgr.kill(session_id)


# ===================================================================
# MCP TOOLS — Shell Listener
# ===================================================================


@mcp.tool(
    name="shell_listener_start",
    annotations={"title": "Start Shell Listener", "readOnlyHint": False, "destructiveHint": False},
)
async def mcp_shell_listener_start(
    port: int,
    protocol: str = "tcp",
    handler: str = "raw",
) -> str:
    """Start a reverse-shell listener (requires admin scope, must be enabled in config).

    Args:
        port: Port to listen on
        protocol: 'tcp' or 'udp'
        handler: 'raw', 'meterpreter', or 'web'
    """
    from kalimcp.terminal.listener import get_listener_manager

    mgr = get_listener_manager()
    return await mgr.start_listener(port=port, protocol=protocol, handler=handler, auth=_auth_from_ctx())


@mcp.tool(
    name="shell_listener_list",
    annotations={"title": "List Shell Listeners", "readOnlyHint": True, "destructiveHint": False},
)
async def mcp_shell_listener_list() -> str:
    """List all active reverse-shell listeners."""
    from kalimcp.terminal.listener import get_listener_manager

    mgr = get_listener_manager()
    return await mgr.list_listeners(auth=_auth_from_ctx())


@mcp.tool(
    name="shell_listener_stop",
    annotations={"title": "Stop Shell Listener", "readOnlyHint": False, "destructiveHint": True},
)
async def mcp_shell_listener_stop(listener_id: str) -> str:
    """Stop a reverse-shell listener.

    Args:
        listener_id: Listener ID to stop
    """
    from kalimcp.terminal.listener import get_listener_manager

    mgr = get_listener_manager()
    return await mgr.stop_listener(listener_id)


@mcp.tool(
    name="shell_connection_list",
    annotations={"title": "List Shell Connections", "readOnlyHint": True, "destructiveHint": False},
)
async def mcp_shell_connection_list() -> str:
    """List all active reverse-shell connections."""
    from kalimcp.terminal.listener import get_listener_manager

    mgr = get_listener_manager()
    return await mgr.list_connections(auth=_auth_from_ctx())


@mcp.tool(
    name="shell_connection_exec",
    annotations={"title": "Execute on Shell Connection", "readOnlyHint": False, "destructiveHint": False},
)
async def mcp_shell_connection_exec(
    conn_id: str,
    command: str,
    timeout: int = 15,
) -> str:
    """Execute a command on a reverse-shell connection and return output.

    Args:
        conn_id: Connection ID (from shell_connection_list)
        command: Command to execute on the remote shell
        timeout: Seconds to wait for output
    """
    from kalimcp.terminal.listener import get_listener_manager

    mgr = get_listener_manager()
    return await mgr.exec_on_connection(conn_id, command, timeout=timeout, auth=_auth_from_ctx())


@mcp.tool(
    name="shell_connection_read",
    annotations={"title": "Read Shell Connection Output", "readOnlyHint": True, "destructiveHint": False},
)
async def mcp_shell_connection_read(conn_id: str, lines: int = 100) -> str:
    """Read the output buffer of a reverse-shell connection.

    Args:
        conn_id: Connection ID
        lines: Number of recent lines to return
    """
    from kalimcp.terminal.listener import get_listener_manager

    mgr = get_listener_manager()
    return await mgr.read_connection(conn_id, lines=lines, auth=_auth_from_ctx())


# ===================================================================
# MCP TOOLS — CodeForge
# ===================================================================


@mcp.tool(
    name="code_create",
    annotations={"title": "Create File", "readOnlyHint": False, "destructiveHint": False},
)
async def mcp_code_create(
    file_path: str,
    content: str,
    language: str = "python",
    executable: bool = False,
) -> str:
    """Create a new file/script in the workspace.

    Args:
        file_path: Relative path inside workspace
        content: File content
        language: Language hint (python, bash, ruby, …)
        executable: Set executable permission
    """
    from kalimcp.codeforge.editor import create_file

    return await create_file(file_path, content, language=language, executable=executable, auth=_auth_from_ctx())


@mcp.tool(
    name="code_edit",
    annotations={"title": "Edit File", "readOnlyHint": False, "destructiveHint": False},
)
async def mcp_code_edit(
    file_path: str,
    edits: list[dict],
) -> str:
    """Edit an existing file using search/replace patches.

    Args:
        file_path: Relative path inside workspace
        edits: List of {search: str, replace: str} patches
    """
    from kalimcp.codeforge.editor import edit_file

    return await edit_file(file_path, edits, auth=_auth_from_ctx())


@mcp.tool(
    name="code_read",
    annotations={"title": "Read File", "readOnlyHint": True, "destructiveHint": False},
)
async def mcp_code_read(
    file_path: str,
    start_line: int = 0,
    end_line: int = -1,
) -> str:
    """Read file content from the workspace.

    Args:
        file_path: Relative path inside workspace
        start_line: Start line (0-based)
        end_line: End line (-1 = EOF)
    """
    from kalimcp.codeforge.editor import read_file

    return await read_file(file_path, start_line=start_line, end_line=end_line, auth=_auth_from_ctx())


@mcp.tool(
    name="code_execute",
    annotations={"title": "Execute Code", "readOnlyHint": False, "destructiveHint": False},
)
async def mcp_code_execute(
    file_path: str,
    args: str = "",
    timeout: int = 120,
    stdin_data: str = "",
) -> str:
    """Execute a script/program from the workspace.

    Args:
        file_path: Relative path inside workspace
        args: Arguments to pass
        timeout: Max seconds
        stdin_data: Data to pipe to stdin
    """
    from kalimcp.codeforge.executor import execute_code

    return await execute_code(file_path, args=args, timeout=timeout, stdin_data=stdin_data, auth=_auth_from_ctx())


@mcp.tool(
    name="code_install_deps",
    annotations={"title": "Install Dependencies", "readOnlyHint": False, "destructiveHint": True},
)
async def mcp_code_install_deps(
    packages: list[str],
    manager: str = "pip",
) -> str:
    """Install packages (requires admin scope, must be enabled in config).

    Args:
        packages: Package names to install
        manager: Package manager — pip, apt, npm, gem, or go
    """
    from kalimcp.codeforge.executor import install_deps

    return await install_deps(packages, manager=manager, auth=_auth_from_ctx())


# ===================================================================
# MCP RESOURCES
# ===================================================================


@mcp.resource("kali://system/info")
async def resource_system_info() -> str:
    """System version, kernel, installed tool count."""
    from kalimcp.resources.system import get_system_info

    return await get_system_info()


@mcp.resource("kali://tools/catalog")
async def resource_tools_catalog() -> str:
    """Complete tool catalog with categories."""
    from kalimcp.resources.system import get_tools_catalog

    return await get_tools_catalog()


@mcp.resource("kali://network/interfaces")
async def resource_network_interfaces() -> str:
    """Network interface information."""
    from kalimcp.resources.system import get_network_interfaces

    return await get_network_interfaces()


@mcp.resource("kali://workspace/{path}")
async def resource_workspace_file(path: str) -> str:
    """Workspace file content (path-restricted)."""
    from kalimcp.resources.system import get_workspace_file

    return await get_workspace_file(path)


# ===================================================================
# MCP PROMPTS
# ===================================================================


@mcp.prompt(name="pentest_recon")
async def prompt_pentest_recon() -> str:
    """信息收集标准流程 — Reconnaissance workflow."""
    from kalimcp.prompts.workflows import get_prompt

    return get_prompt("pentest_recon")


@mcp.prompt(name="pentest_webapp")
async def prompt_pentest_webapp() -> str:
    """Web 应用渗透测试工作流。"""
    from kalimcp.prompts.workflows import get_prompt

    return get_prompt("pentest_webapp")


@mcp.prompt(name="pentest_network")
async def prompt_pentest_network() -> str:
    """内网渗透标准流程。"""
    from kalimcp.prompts.workflows import get_prompt

    return get_prompt("pentest_network")


@mcp.prompt(name="ctf_solve")
async def prompt_ctf_solve() -> str:
    """CTF 解题辅助工作流。"""
    from kalimcp.prompts.workflows import get_prompt

    return get_prompt("ctf_solve")


@mcp.prompt(name="incident_response")
async def prompt_incident_response() -> str:
    """应急响应流程。"""
    from kalimcp.prompts.workflows import get_prompt

    return get_prompt("incident_response")


@mcp.prompt(name="vuln_assessment")
async def prompt_vuln_assessment() -> str:
    """漏洞评估报告工作流。"""
    from kalimcp.prompts.workflows import get_prompt

    return get_prompt("vuln_assessment")


# ===================================================================
# CLI entry point
# ===================================================================


def cli() -> None:
    """CLI entry point: ``kalimcp serve`` / ``kalimcp stdio``."""
    parser = argparse.ArgumentParser(
        prog="kalimcp",
        description="KaliMcp — Kali Linux MCP Server",
    )
    parser.add_argument("--version", action="version", version=f"kalimcp {__version__}")

    sub = parser.add_subparsers(dest="command")

    # --- serve ---
    serve_p = sub.add_parser("serve", help="Start HTTP (Streamable HTTP) server")
    serve_p.add_argument("--host", default=None, help="Bind address (default from config)")
    serve_p.add_argument("--port", type=int, default=None, help="Listen port (default from config)")
    serve_p.add_argument("--config", default=None, help="Path to YAML config file")
    serve_p.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")

    # --- stdio ---
    stdio_p = sub.add_parser("stdio", help="Run in stdio transport mode (local)")
    stdio_p.add_argument("--config", default=None, help="Path to YAML config file")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Init config
    config_path = getattr(args, "config", None)
    if config_path is None:
        default_path = Path(__file__).resolve().parents[2] / "config" / "default.yaml"
        if default_path.exists():
            config_path = str(default_path)
    cfg = init_config(config_path)

    # Logging
    logging.basicConfig(
        level=getattr(logging, cfg.logging.level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    log = logging.getLogger("kalimcp")
    log.info("============================================")
    log.info("       Kali-Mcp-Toolkit  v%s", __version__)
    log.info("============================================")

    if args.command == "stdio":
        log.info("Starting in stdio transport mode ...")
        mcp.run(transport="stdio")

    elif args.command == "serve":
        host = args.host or cfg.server.host
        port = args.port or cfg.server.port

        log.info("Starting HTTP server on %s:%s ...", host, port)

        # Set host/port on FastMCP settings (run() does not accept them
        # for streamable-http transport in current mcp SDK versions).
        mcp.settings.host = host
        mcp.settings.port = port

        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    cli()
