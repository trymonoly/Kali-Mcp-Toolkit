"""Tool Engine — exec_tool, list_kali_tools, tool_help MCP tools."""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from kalimcp.auth import AuthContext, require_scope
from kalimcp.tools import VALID_CATEGORIES, KaliToolInfo, get_catalog
from kalimcp.utils.audit import AuditEvent, get_audit_logger
from kalimcp.utils.parser import parse_output
from kalimcp.utils.process import ProcessResult, get_executor
from kalimcp.utils.sanitizer import SanitisationError, validate_arguments, validate_tool_name

logger = logging.getLogger("kalimcp.tool_engine")

# ---------------------------------------------------------------------------
# Core execution
# ---------------------------------------------------------------------------


async def _run_tool(
    tool_name: str,
    arguments: str,
    timeout: int,
    output_format: str,
    auth: AuthContext,
) -> str:
    """Internal pipeline: whitelist → sanitise → execute → parse → audit."""
    audit = get_audit_logger()
    start = time.time()
    params_summary = f"{tool_name} {arguments[:200]}"

    try:
        # 1. Whitelist
        validate_tool_name(tool_name)

        # 2. Auth
        require_scope(auth, "execute")

        # 3. Sanitise arguments
        tokens = validate_arguments(arguments)

        # 4. Execute
        cmd = [tool_name] + tokens
        result: ProcessResult = await get_executor().execute(cmd, timeout=timeout)

        # 5. Parse output
        raw = result.stdout or result.stderr
        if output_format in ("json", "xml"):
            parsed = parse_output(raw, preferred_format=output_format)
        else:
            parsed = parse_output(raw, preferred_format="text")

        duration_ms = (time.time() - start) * 1000

        # Build response
        response_parts = []
        if result.timed_out:
            response_parts.append(f"⚠️ Command timed out after {timeout}s.")
        if result.exit_code != 0 and not result.timed_out:
            response_parts.append(f"Exit code: {result.exit_code}")
        if result.stderr and result.stdout:
            response_parts.append(f"--- STDOUT ---\n{parsed}")
            response_parts.append(f"--- STDERR ---\n{result.stderr[:2000]}")
        else:
            response_parts.append(parsed)
        if result.truncated:
            response_parts.append("[output was truncated]")

        output_text = "\n".join(response_parts)

        await audit.log(AuditEvent(
            api_key_name=auth.key_name,
            action="exec_tool",
            module="tool",
            params_summary=params_summary,
            result_summary=output_text[:500],
            duration_ms=duration_ms,
            source_ip=auth.source_ip,
            success=result.exit_code == 0,
        ))

        return output_text

    except (SanitisationError, Exception) as e:
        duration_ms = (time.time() - start) * 1000
        error_msg = str(e)
        await audit.log(AuditEvent(
            api_key_name=auth.key_name,
            action="exec_tool",
            module="tool",
            params_summary=params_summary,
            duration_ms=duration_ms,
            source_ip=auth.source_ip,
            success=False,
            error=error_msg,
        ))
        return f"Error: {error_msg}"


# ---------------------------------------------------------------------------
# MCP Tool functions (registered by server.py)
# ---------------------------------------------------------------------------


async def exec_tool(
    tool_name: str,
    arguments: str = "",
    timeout: int = 300,
    output_format: str = "text",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Execute any Kali tool and return the result.

    Args:
        tool_name: Tool binary name (e.g. 'nmap')
        arguments: Command-line arguments
        timeout: Max execution time in seconds
        output_format: 'text', 'json', or 'xml'
    """
    auth = _auth or AuthContext()
    return await _run_tool(tool_name, arguments, timeout, output_format, auth)


async def list_kali_tools(
    category: str = "all",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """List available Kali tools, optionally filtered by category.

    Args:
        category: One of the 12 categories (recon, vuln, webapp, …) or 'all'
    """
    auth = _auth or AuthContext()
    require_scope(auth, "read")

    catalog = get_catalog()

    if category == "all":
        tools = catalog.list_all()
    elif category in VALID_CATEGORIES:
        tools = catalog.list_by_category(category)
    else:
        return f"Error: Unknown category '{category}'. Valid: {', '.join(VALID_CATEGORIES)}"

    if not tools:
        return f"No tools found for category '{category}'."

    # Group by category for 'all'
    if category == "all":
        grouped: dict[str, list[KaliToolInfo]] = {}
        for t in tools:
            grouped.setdefault(t.category, []).append(t)
        lines = []
        for cat_key in VALID_CATEGORIES:
            cat_tools = grouped.get(cat_key, [])
            if not cat_tools:
                continue
            cat_info = catalog.categories.get(cat_key)
            label = cat_info.label if cat_info else cat_key
            lines.append(f"\n## {label}")
            for t in cat_tools:
                risk = f"[{t.risk_level.value}]"
                lines.append(f"  - {t.name} {risk} — {t.description}")
        return "\n".join(lines)
    else:
        cat_info = catalog.categories.get(category)
        label = cat_info.label if cat_info else category
        lines = [f"## {label}"]
        for t in tools:
            risk = f"[{t.risk_level.value}]"
            lines.append(f"  - {t.name} {risk} — {t.description}")
        return "\n".join(lines)


async def tool_help(
    tool_name: str,
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Get help text for a Kali tool (--help or man fallback).

    Args:
        tool_name: Tool binary name
    """
    auth = _auth or AuthContext()
    require_scope(auth, "read")

    catalog = get_catalog()
    tool = catalog.get_tool(tool_name)
    if tool is None:
        return f"Error: Tool '{tool_name}' is not in the catalog."

    executor = get_executor()

    # Try --help first
    result = await executor.execute([tool_name, "--help"], timeout=15)
    text = result.stdout or result.stderr

    if not text.strip() or result.exit_code == 127:
        # Fallback to man page
        result = await executor.execute(["man", "-P", "cat", tool_name], timeout=15)
        text = result.stdout or result.stderr

    if not text.strip():
        return f"No help available for '{tool_name}'. The tool may not be installed."

    # Truncate
    lines = text.splitlines()
    if len(lines) > 200:
        text = "\n".join(lines[:200]) + f"\n\n... [{len(lines) - 200} lines truncated]"

    return text
