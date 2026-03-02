"""Password attack tool wrappers (high-risk, require admin scope + feature flag)."""

from __future__ import annotations

import json
from typing import Optional

from kalimcp.auth import AuthContext, AuthError, require_scope
from kalimcp.config import get_config
from kalimcp.tools.tool_engine import exec_tool


def _check_high_risk(auth: AuthContext) -> Optional[str]:
    cfg = get_config().security
    if not cfg.enable_high_risk_tools:
        return json.dumps({"error": "High-risk tools are disabled. Set security.enable_high_risk_tools=true."})
    try:
        require_scope(auth, "admin")
    except AuthError as e:
        return json.dumps({"error": str(e)})
    return None


async def password_hydra(
    target: str,
    service: str = "ssh",
    username: str = "admin",
    wordlist: str = "/usr/share/wordlists/rockyou.txt",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Network login brute-forcer."""
    auth = _auth or AuthContext()
    err = _check_high_risk(auth)
    if err:
        return err
    args = f"-l {username} -P {wordlist} {extra_args} {target} {service}"
    return await exec_tool("hydra", args, timeout=600, _auth=auth)


async def password_john(
    hash_file: str,
    wordlist: str = "/usr/share/wordlists/rockyou.txt",
    format: str = "",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """John the Ripper password cracker."""
    auth = _auth or AuthContext()
    err = _check_high_risk(auth)
    if err:
        return err
    args = hash_file
    if wordlist:
        args += f" --wordlist={wordlist}"
    if format:
        args += f" --format={format}"
    if extra_args:
        args += f" {extra_args}"
    return await exec_tool("john", args, timeout=1800, _auth=auth)


async def password_hashcat(
    hash_file: str,
    hash_type: int = 0,
    wordlist: str = "/usr/share/wordlists/rockyou.txt",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Hashcat GPU password recovery."""
    auth = _auth or AuthContext()
    err = _check_high_risk(auth)
    if err:
        return err
    args = f"-m {hash_type} {hash_file} {wordlist}"
    if extra_args:
        args += f" {extra_args}"
    return await exec_tool("hashcat", args, timeout=3600, _auth=auth)
