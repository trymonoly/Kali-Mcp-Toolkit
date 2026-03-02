"""CodeForge Executor — run scripts and install dependencies."""

from __future__ import annotations

import json
import shlex
from typing import Optional

from kalimcp.auth import AuthContext, AuthError, require_scope
from kalimcp.codeforge.workspace import resolve_workspace_path
from kalimcp.config import get_config
from kalimcp.utils.audit import AuditEvent, get_audit_logger
from kalimcp.utils.process import get_executor
from kalimcp.utils.sanitizer import SanitisationError, validate_package_name

# ---------------------------------------------------------------------------
# Interpreter mapping
# ---------------------------------------------------------------------------

_INTERPRETER_MAP: dict[str, list[str]] = {
    ".py": ["python3"],
    ".sh": ["bash"],
    ".bash": ["bash"],
    ".rb": ["ruby"],
    ".pl": ["perl"],
    ".js": ["node"],
    ".ts": ["npx", "ts-node"],
    ".php": ["php"],
    ".lua": ["lua"],
    ".go": ["go", "run"],
    ".r": ["Rscript"],
    ".R": ["Rscript"],
}

# Manager → install command template
_PKG_MANAGER_CMD: dict[str, list[str]] = {
    "pip": ["pip", "install"],
    "apt": ["apt-get", "install", "-y"],
    "npm": ["npm", "install", "-g"],
    "gem": ["gem", "install"],
    "go": ["go", "install"],
}


# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------


async def execute_code(
    file_path: str,
    *,
    args: str = "",
    timeout: int = 120,
    stdin_data: str = "",
    auth: Optional[AuthContext] = None,
) -> str:
    """Execute a script/program from the workspace."""
    auth = auth or AuthContext()
    require_scope(auth, "execute")
    audit = get_audit_logger()

    try:
        target = resolve_workspace_path(file_path)
        if not target.exists():
            return json.dumps({"error": f"File not found: {file_path}"})

        # Determine interpreter
        suffix = target.suffix.lower()
        interpreter = _INTERPRETER_MAP.get(suffix)

        if interpreter:
            cmd = interpreter + [str(target)]
        else:
            cmd = [str(target)]

        # Append extra args
        if args.strip():
            cmd.extend(shlex.split(args))

        executor = get_executor()
        result = await executor.execute(
            cmd,
            timeout=timeout,
            stdin_data=stdin_data if stdin_data else None,
            cwd=str(target.parent),
        )

        await audit.log(AuditEvent(
            action="code_execute",
            module="codeforge",
            params_summary=f"path={file_path} timeout={timeout}",
            result_summary=f"exit={result.exit_code} dur={result.duration_ms:.0f}ms",
            api_key_name=auth.key_name,
            duration_ms=result.duration_ms,
            success=result.exit_code == 0,
        ))

        return json.dumps({
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": round(result.duration_ms, 1),
            "timed_out": result.timed_out,
            "truncated": result.truncated,
        }, ensure_ascii=False)

    except SanitisationError as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Dependency installation
# ---------------------------------------------------------------------------


async def install_deps(
    packages: list[str],
    *,
    manager: str = "pip",
    auth: Optional[AuthContext] = None,
) -> str:
    """Install packages using the specified package manager (admin scope required)."""
    auth = auth or AuthContext()
    cfg = get_config().security
    audit = get_audit_logger()

    # Feature gate
    if not cfg.enable_install_deps:
        return json.dumps({"error": "Dependency installation is disabled. Set security.enable_install_deps=true."})

    # Admin scope
    try:
        require_scope(auth, "admin")
    except AuthError as e:
        return json.dumps({"error": str(e)})

    # Validate manager
    if manager not in _PKG_MANAGER_CMD:
        return json.dumps({"error": f"Unknown package manager: '{manager}'. Supported: {list(_PKG_MANAGER_CMD.keys())}"})

    # Validate package names
    for pkg in packages:
        try:
            validate_package_name(pkg)
        except SanitisationError as e:
            return json.dumps({"error": f"Invalid package '{pkg}': {e}"})

    cmd = _PKG_MANAGER_CMD[manager] + packages
    executor = get_executor()
    result = await executor.execute(cmd, timeout=300)

    await audit.log(AuditEvent(
        action="code_install_deps",
        module="codeforge",
        params_summary=f"manager={manager} packages={packages}",
        result_summary=f"exit={result.exit_code}",
        api_key_name=auth.key_name,
        duration_ms=result.duration_ms,
        success=result.exit_code == 0,
    ))

    return json.dumps({
        "exit_code": result.exit_code,
        "stdout": result.stdout[:5000],
        "stderr": result.stderr[:2000],
        "packages": packages,
        "manager": manager,
    }, ensure_ascii=False)
