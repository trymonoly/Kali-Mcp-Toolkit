"""CodeForge Editor — file creation, search/replace editing, line-range reading."""

from __future__ import annotations

import json
import os
import stat
from typing import Optional

from kalimcp.auth import AuthContext, require_scope
from kalimcp.codeforge.workspace import check_file_size, ensure_parent, resolve_workspace_path
from kalimcp.utils.audit import AuditEvent, get_audit_logger
from kalimcp.utils.sanitizer import SanitisationError


async def create_file(
    file_path: str,
    content: str,
    *,
    language: str = "python",
    executable: bool = False,
    auth: Optional[AuthContext] = None,
) -> str:
    """Create a new file inside the workspace."""
    auth = auth or AuthContext()
    require_scope(auth, "execute")

    try:
        target = resolve_workspace_path(file_path)
        ensure_parent(target)

        target.write_text(content, encoding="utf-8")

        if executable:
            st = target.stat()
            target.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP)

        check_file_size(target)

        await get_audit_logger().log(AuditEvent(
            action="code_create",
            module="codeforge",
            params_summary=f"path={file_path} lang={language} exec={executable}",
            api_key_name=auth.key_name,
        ))

        return json.dumps({
            "status": "created",
            "path": str(target),
            "size": target.stat().st_size,
            "executable": executable,
        })

    except SanitisationError as e:
        return json.dumps({"error": str(e)})


async def edit_file(
    file_path: str,
    edits: list[dict],
    *,
    auth: Optional[AuthContext] = None,
) -> str:
    """Apply search/replace patches to a workspace file."""
    auth = auth or AuthContext()
    require_scope(auth, "execute")

    try:
        target = resolve_workspace_path(file_path)
        if not target.exists():
            return json.dumps({"error": f"File not found: {file_path}"})

        content = target.read_text(encoding="utf-8")
        applied = 0
        errors = []

        for i, edit in enumerate(edits):
            search = edit.get("search", "")
            replace = edit.get("replace", "")
            if not search:
                errors.append(f"Edit #{i}: empty search string")
                continue
            if search not in content:
                errors.append(f"Edit #{i}: search string not found")
                continue
            content = content.replace(search, replace, 1)
            applied += 1

        target.write_text(content, encoding="utf-8")
        check_file_size(target)

        await get_audit_logger().log(AuditEvent(
            action="code_edit",
            module="codeforge",
            params_summary=f"path={file_path} edits={len(edits)} applied={applied}",
            api_key_name=auth.key_name,
        ))

        result = {"status": "edited", "path": str(target), "applied": applied}
        if errors:
            result["warnings"] = errors
        return json.dumps(result)

    except SanitisationError as e:
        return json.dumps({"error": str(e)})


async def read_file(
    file_path: str,
    *,
    start_line: int = 0,
    end_line: int = -1,
    auth: Optional[AuthContext] = None,
) -> str:
    """Read workspace file content, optionally by line range."""
    auth = auth or AuthContext()
    require_scope(auth, "read")

    try:
        target = resolve_workspace_path(file_path)
        if not target.exists():
            return json.dumps({"error": f"File not found: {file_path}"})

        check_file_size(target)
        lines = target.read_text(encoding="utf-8").splitlines()

        if end_line == -1:
            end_line = len(lines)
        selected = lines[start_line:end_line]

        # Number lines for display
        numbered = [f"{start_line + i + 1:4d}| {line}" for i, line in enumerate(selected)]
        return "\n".join(numbered)

    except SanitisationError as e:
        return json.dumps({"error": str(e)})
