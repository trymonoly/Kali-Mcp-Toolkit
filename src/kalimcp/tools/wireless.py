"""Wireless attack tool wrappers (high-risk, default disabled)."""

from __future__ import annotations

import json
from typing import Optional

from kalimcp.auth import AuthContext, AuthError, require_scope
from kalimcp.config import get_config
from kalimcp.tools.tool_engine import exec_tool


def _check_high_risk(auth: AuthContext) -> Optional[str]:
    cfg = get_config().security
    if not cfg.enable_high_risk_tools:
        return json.dumps({"error": "High-risk tools are disabled."})
    try:
        require_scope(auth, "admin")
    except AuthError as e:
        return json.dumps({"error": str(e)})
    return None


async def wireless_aircrack(
    cap_file: str,
    wordlist: str = "/usr/share/wordlists/rockyou.txt",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Crack WPA/WPA2 keys from a capture file."""
    auth = _auth or AuthContext()
    err = _check_high_risk(auth)
    if err:
        return err
    args = f"-w {wordlist} {extra_args} {cap_file}"
    return await exec_tool("aircrack-ng", args, timeout=3600, _auth=auth)
