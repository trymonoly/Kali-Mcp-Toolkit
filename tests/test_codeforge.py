"""CodeForge tests — workspace path security, file creation/edit/read."""

from __future__ import annotations

import json

import pytest

from kalimcp.auth import AuthContext
from kalimcp.codeforge.editor import create_file, edit_file, read_file
from kalimcp.codeforge.workspace import resolve_workspace_path
from kalimcp.utils.sanitizer import SanitisationError


# ── Workspace path security ─────────────────────────────────────────


class TestWorkspaceSecurity:
    def test_resolve_normal(self, workspace):
        path = resolve_workspace_path("test.txt")
        assert str(workspace) in str(path)

    def test_reject_traversal(self):
        with pytest.raises(SanitisationError, match="traversal"):
            resolve_workspace_path("../../../etc/shadow")

    def test_reject_absolute_path(self):
        with pytest.raises(SanitisationError, match="traversal"):
            resolve_workspace_path("/etc/passwd")


# ── File operations ─────────────────────────────────────────────────


class TestFileOperations:
    @pytest.mark.asyncio
    async def test_create_and_read(self, workspace):
        auth = AuthContext(scopes=["read", "execute"])
        result = await create_file("hello.py", "print('hello')", auth=auth)
        data = json.loads(result)
        assert data["status"] == "created"

        content = await read_file("hello.py", auth=auth)
        assert "print('hello')" in content

    @pytest.mark.asyncio
    async def test_edit_file(self, workspace):
        auth = AuthContext(scopes=["read", "execute"])
        await create_file("edit_me.txt", "foo bar baz", auth=auth)

        result = await edit_file(
            "edit_me.txt",
            [{"search": "bar", "replace": "qux"}],
            auth=auth,
        )
        data = json.loads(result)
        assert data["applied"] == 1

        content = await read_file("edit_me.txt", auth=auth)
        assert "qux" in content
        assert "bar" not in content

    @pytest.mark.asyncio
    async def test_edit_search_not_found(self, workspace):
        auth = AuthContext(scopes=["read", "execute"])
        await create_file("stable.txt", "content here", auth=auth)

        result = await edit_file(
            "stable.txt",
            [{"search": "nonexistent", "replace": "x"}],
            auth=auth,
        )
        data = json.loads(result)
        assert "warnings" in data

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, workspace):
        auth = AuthContext(scopes=["read"])
        result = await read_file("nope.txt", auth=auth)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_read_line_range(self, workspace):
        auth = AuthContext(scopes=["read", "execute"])
        content = "\n".join(f"line{i}" for i in range(20))
        await create_file("lines.txt", content, auth=auth)

        result = await read_file("lines.txt", start_line=5, end_line=10, auth=auth)
        lines = result.strip().splitlines()
        assert len(lines) == 5
        assert "line5" in lines[0]
