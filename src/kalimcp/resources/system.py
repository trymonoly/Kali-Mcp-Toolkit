"""MCP Resource implementations — system info, catalog, network interfaces, workspace files."""

from __future__ import annotations

import json
import platform
import subprocess

from kalimcp.codeforge.workspace import resolve_workspace_path
from kalimcp.tools import get_catalog
from kalimcp.utils.sanitizer import SanitisationError


async def get_system_info() -> str:
    """Return Kali system information as JSON."""
    catalog = get_catalog()
    info = {
        "hostname": platform.node(),
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "total_tools_in_catalog": len(catalog.tools),
    }
    # Try to get Kali version
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["distro"] = line.split("=", 1)[1].strip().strip('"')
    except FileNotFoundError:
        info["distro"] = "Unknown (not Kali?)"

    # Kernel
    try:
        info["kernel"] = subprocess.check_output(["uname", "-r"], text=True).strip()
    except Exception:
        info["kernel"] = platform.release()

    return json.dumps(info, indent=2)


async def get_tools_catalog() -> str:
    """Return the full tool catalog as JSON."""
    catalog = get_catalog()
    data = {
        "categories": {k: v.model_dump() for k, v in catalog.categories.items()},
        "tools": [t.model_dump() for t in catalog.tools],
        "total": len(catalog.tools),
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


async def get_network_interfaces() -> str:
    """Return network interface information as JSON."""
    try:
        result = subprocess.check_output(
            ["ip", "-j", "addr", "show"],
            text=True,
            timeout=5,
        )
        return result
    except FileNotFoundError:
        # Fallback for systems without `ip`
        try:
            result = subprocess.check_output(["ifconfig"], text=True, timeout=5)
            return result
        except Exception:
            return json.dumps({"error": "Cannot retrieve network interface info."})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def get_workspace_file(path: str) -> str:
    """Read a workspace file (path-restricted)."""
    try:
        target = resolve_workspace_path(path)
        if not target.exists():
            return json.dumps({"error": f"File not found: {path}"})
        if target.is_dir():
            items = [p.name for p in target.iterdir()]
            return json.dumps({"type": "directory", "items": items})
        return target.read_text(encoding="utf-8", errors="replace")
    except SanitisationError as e:
        return json.dumps({"error": str(e)})
