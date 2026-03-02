"""Structured wrappers for web application testing tools."""

from __future__ import annotations

from typing import Literal, Optional

from kalimcp.auth import AuthContext
from kalimcp.tools.tool_engine import exec_tool


async def webapp_gobuster(
    url: str,
    mode: Literal["dir", "dns", "vhost", "fuzz"] = "dir",
    wordlist: str = "/usr/share/wordlists/dirb/common.txt",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Directory / DNS / vhost busting with gobuster.

    Args:
        url: Target URL
        mode: Gobuster mode (dir, dns, vhost, fuzz)
        wordlist: Path to wordlist
        extra_args: Additional flags
    """
    args = f"{mode} -u {url} -w {wordlist}"
    if extra_args:
        args += f" {extra_args}"
    return await exec_tool("gobuster", args, timeout=600, _auth=_auth)


async def webapp_sqlmap(
    url: str,
    data: str = "",
    level: int = 1,
    risk: int = 1,
    batch: bool = True,
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Automatic SQL injection detection with sqlmap.

    Args:
        url: Target URL with parameter (e.g. http://target/page?id=1)
        data: POST data
        level: Detection level (1-5)
        risk: Risk level (1-3)
        batch: Auto-answer prompts
        extra_args: Additional flags
    """
    args = f"-u {url} --level={level} --risk={risk}"
    if data:
        args += f" --data={data}"
    if batch:
        args += " --batch"
    if extra_args:
        args += f" {extra_args}"
    return await exec_tool("sqlmap", args, timeout=600, _auth=_auth)


async def webapp_ffuf(
    url: str,
    wordlist: str = "/usr/share/wordlists/dirb/common.txt",
    filter_code: str = "404",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Fast web fuzzing with ffuf.

    Args:
        url: Target URL with FUZZ keyword (e.g. http://target/FUZZ)
        wordlist: Path to wordlist
        filter_code: HTTP status codes to filter out
        extra_args: Additional flags
    """
    args = f"-u {url} -w {wordlist} -fc {filter_code}"
    if extra_args:
        args += f" {extra_args}"
    return await exec_tool("ffuf", args, timeout=600, _auth=_auth)


async def webapp_whatweb(
    target: str,
    aggression: int = 1,
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Identify web technologies with whatweb.

    Args:
        target: Target URL
        aggression: Aggression level (1=stealthy, 3=aggressive)
    """
    return await exec_tool("whatweb", f"-a {aggression} {target}", timeout=60, _auth=_auth)
