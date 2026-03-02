"""Sniffing & spoofing tool wrappers."""

from __future__ import annotations

from typing import Optional

from kalimcp.auth import AuthContext
from kalimcp.tools.tool_engine import exec_tool


async def sniff_tshark(
    interface: str = "eth0",
    count: int = 100,
    capture_filter: str = "",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Capture packets with tshark.

    Args:
        interface: Network interface
        count: Number of packets to capture
        capture_filter: BPF capture filter
        extra_args: Additional flags
    """
    args = f"-i {interface} -c {count}"
    if capture_filter:
        args += f" -f '{capture_filter}'"
    if extra_args:
        args += f" {extra_args}"
    return await exec_tool("tshark", args, timeout=120, _auth=_auth)


async def sniff_tcpdump(
    interface: str = "eth0",
    count: int = 50,
    capture_filter: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Capture packets with tcpdump."""
    args = f"-i {interface} -c {count}"
    if capture_filter:
        args += f" {capture_filter}"
    return await exec_tool("tcpdump", args, timeout=120, _auth=_auth)
