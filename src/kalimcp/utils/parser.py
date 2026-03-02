"""Tool output parsing — nmap XML, generic format detection, truncation."""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional

logger = logging.getLogger("kalimcp.parser")

MAX_DISPLAY_LINES = 500
TRUNCATION_KEEP = 100  # lines to keep from head and tail

# ---------------------------------------------------------------------------
# Generic format detection & parsing
# ---------------------------------------------------------------------------


def detect_format(text: str) -> str:
    """Heuristic: return 'json', 'xml', or 'text'."""
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return "json"
        except json.JSONDecodeError:
            pass
    if stripped.startswith("<?xml") or stripped.startswith("<"):
        try:
            ET.fromstring(stripped)
            return "xml"
        except ET.ParseError:
            pass
    return "text"


def parse_output(text: str, preferred_format: str = "text") -> str:
    """Try to parse *text* according to *preferred_format*; fall back to raw."""
    fmt = detect_format(text) if preferred_format == "auto" else preferred_format
    try:
        if fmt == "json":
            obj = json.loads(text)
            return json.dumps(obj, indent=2, ensure_ascii=False)
        if fmt == "xml":
            return parse_nmap_xml(text) or text
    except Exception as e:
        logger.debug("parse_output fallback: %s", e)
    return smart_truncate(text)


# ---------------------------------------------------------------------------
# nmap XML parser
# ---------------------------------------------------------------------------


def parse_nmap_xml(xml_text: str) -> Optional[str]:
    """Parse nmap XML output into structured JSON summary."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    if root.tag != "nmaprun":
        return None

    result: dict[str, Any] = {
        "scanner": root.get("scanner", "nmap"),
        "args": root.get("args", ""),
        "start_time": root.get("startstr", ""),
        "hosts": [],
    }

    for host_elem in root.findall("host"):
        host: dict[str, Any] = {"status": "", "addresses": [], "hostnames": [], "ports": [], "os": []}

        status = host_elem.find("status")
        if status is not None:
            host["status"] = status.get("state", "")

        for addr in host_elem.findall("address"):
            host["addresses"].append({"addr": addr.get("addr", ""), "type": addr.get("addrtype", "")})

        hostnames_elem = host_elem.find("hostnames")
        if hostnames_elem is not None:
            for hn in hostnames_elem.findall("hostname"):
                host["hostnames"].append(hn.get("name", ""))

        ports_elem = host_elem.find("ports")
        if ports_elem is not None:
            for port in ports_elem.findall("port"):
                port_info: dict[str, Any] = {
                    "port": int(port.get("portid", 0)),
                    "protocol": port.get("protocol", ""),
                }
                state = port.find("state")
                if state is not None:
                    port_info["state"] = state.get("state", "")
                service = port.find("service")
                if service is not None:
                    port_info["service"] = service.get("name", "")
                    port_info["product"] = service.get("product", "")
                    port_info["version"] = service.get("version", "")
                host["ports"].append(port_info)

        os_elem = host_elem.find("os")
        if os_elem is not None:
            for osmatch in os_elem.findall("osmatch"):
                host["os"].append({
                    "name": osmatch.get("name", ""),
                    "accuracy": osmatch.get("accuracy", ""),
                })

        result["hosts"].append(host)

    # Summary from runstats
    runstats = root.find("runstats/finished")
    if runstats is not None:
        result["elapsed"] = runstats.get("elapsed", "")
        result["summary"] = runstats.get("summary", "")

    return json.dumps(result, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Smart truncation
# ---------------------------------------------------------------------------


def smart_truncate(text: str, max_lines: int = MAX_DISPLAY_LINES) -> str:
    """Keep head + tail if text exceeds *max_lines*."""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    keep = TRUNCATION_KEEP
    head = lines[:keep]
    tail = lines[-keep:]
    omitted = len(lines) - 2 * keep
    return "\n".join(head) + f"\n\n... [{omitted} lines omitted] ...\n\n" + "\n".join(tail)
