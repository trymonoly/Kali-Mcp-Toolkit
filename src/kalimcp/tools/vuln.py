"""Structured wrappers for vulnerability analysis tools."""

from __future__ import annotations

from typing import Optional

from kalimcp.auth import AuthContext
from kalimcp.tools.tool_engine import exec_tool


async def vuln_nikto(
    target: str,
    tuning: str = "",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Run nikto web-server vulnerability scanner.

    Args:
        target: Target URL (e.g. http://192.168.1.100)
        tuning: Nikto tuning options
        extra_args: Additional flags
    """
    args = f"-h {target}"
    if tuning:
        args += f" -Tuning {tuning}"
    if extra_args:
        args += f" {extra_args}"
    return await exec_tool("nikto", args, timeout=600, _auth=_auth)


async def vuln_wpscan(
    url: str,
    enumerate: str = "vp,vt,u",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Scan WordPress sites for vulnerabilities.

    Args:
        url: WordPress site URL
        enumerate: Enumeration options (vp=vulnerable plugins, vt=themes, u=users)
        extra_args: Additional flags
    """
    args = f"--url {url} -e {enumerate} --no-banner"
    if extra_args:
        args += f" {extra_args}"
    return await exec_tool("wpscan", args, timeout=600, _auth=_auth)
