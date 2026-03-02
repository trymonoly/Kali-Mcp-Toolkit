"""Structured wrappers for reconnaissance tools (nmap, whois, dig, theHarvester)."""

from __future__ import annotations

from typing import Literal, Optional

from kalimcp.auth import AuthContext
from kalimcp.tools.tool_engine import exec_tool


async def recon_nmap(
    target: str,
    scan_type: Literal["quick", "full", "vuln", "os", "service"] = "quick",
    ports: str = "1-1000",
    extra_args: str = "",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Run nmap with pre-configured scan profiles, returning structured results.

    Args:
        target: Target IP/hostname/CIDR
        scan_type: Scan profile — quick, full, vuln, os, service
        ports: Port range
        extra_args: Additional nmap flags
    """
    profiles = {
        "quick": f"-sV -T4 -p {ports} -oX -",
        "full": f"-sV -sC -O -T4 -p- -oX -",
        "vuln": f"--script vuln -p {ports} -oX -",
        "os": f"-O -sV -T4 -p {ports} -oX -",
        "service": f"-sV -sC -T4 -p {ports} -oX -",
    }
    args = f"{profiles[scan_type]} {extra_args} {target}".strip()
    return await exec_tool("nmap", args, timeout=600, output_format="xml", _auth=_auth)


async def recon_whois(
    target: str,
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Query WHOIS information for a domain or IP."""
    return await exec_tool("whois", target, timeout=30, _auth=_auth)


async def recon_dig(
    target: str,
    record_type: str = "ANY",
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """DNS lookup using dig.

    Args:
        target: Domain name
        record_type: DNS record type (A, AAAA, MX, NS, TXT, ANY, …)
    """
    return await exec_tool("dig", f"{target} {record_type}", timeout=30, _auth=_auth)


async def recon_theharvester(
    domain: str,
    source: str = "all",
    limit: int = 200,
    *,
    _auth: Optional[AuthContext] = None,
) -> str:
    """Harvest emails, subdomains, and names from public sources.

    Args:
        domain: Target domain
        source: Data source (all, google, bing, linkedin, …)
        limit: Max results
    """
    return await exec_tool(
        "theHarvester",
        f"-d {domain} -b {source} -l {limit}",
        timeout=300,
        _auth=_auth,
    )
