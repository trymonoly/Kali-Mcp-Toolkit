"""Security tests — sanitiser, path traversal, command injection, whitelist."""

from __future__ import annotations

import pytest

from kalimcp.auth import AuthContext, AuthError, authenticate_request, require_scope, verify_api_key
from kalimcp.config import init_config
from kalimcp.utils.sanitizer import SanitisationError, validate_arguments, validate_tool_name, validate_workspace_path


# ── Tool whitelist ──────────────────────────────────────────────────


class TestToolWhitelist:
    def test_valid_tool(self):
        validate_tool_name("nmap")  # should not raise

    def test_unknown_tool_rejected(self):
        with pytest.raises(SanitisationError, match="not registered"):
            validate_tool_name("totally_fake_tool")

    def test_case_sensitive(self):
        # 'nmap' exists, 'NMAP' does not
        with pytest.raises(SanitisationError):
            validate_tool_name("NMAP")


# ── Argument sanitisation ───────────────────────────────────────────


class TestArgumentSanitisation:
    def test_normal_args(self):
        tokens = validate_arguments("-sV -T4 192.168.1.1")
        assert tokens == ["-sV", "-T4", "192.168.1.1"]

    def test_empty_args(self):
        assert validate_arguments("") == []

    def test_shell_injection_semicolon(self):
        with pytest.raises(SanitisationError, match="metacharacters"):
            validate_arguments("-sV 192.168.1.1; rm -rf /")

    def test_shell_injection_pipe(self):
        with pytest.raises(SanitisationError, match="metacharacters"):
            validate_arguments("target | cat /etc/passwd")

    def test_shell_injection_backtick(self):
        with pytest.raises(SanitisationError, match="metacharacters"):
            validate_arguments("`whoami`")

    def test_shell_injection_dollar(self):
        with pytest.raises(SanitisationError, match="metacharacters"):
            validate_arguments("$(whoami)")

    def test_blocked_command_rm_rf(self):
        with pytest.raises(SanitisationError, match="Blocked"):
            validate_arguments("rm -rf /")

    def test_blocked_command_mkfs(self):
        with pytest.raises(SanitisationError, match="Blocked"):
            validate_arguments("mkfs /dev/sda")

    def test_blocked_fork_bomb(self):
        with pytest.raises(SanitisationError, match="Blocked"):
            validate_arguments(":(){:|:&};:")

    def test_argument_too_long(self):
        with pytest.raises(SanitisationError, match="exceeds maximum length"):
            validate_arguments("A" * 5000)

    def test_quoted_args(self):
        tokens = validate_arguments('--output "my file.txt"')
        assert tokens == ["--output", "my file.txt"]


# ── Path traversal ──────────────────────────────────────────────────


class TestPathTraversal:
    def test_normal_path(self, workspace):
        # Should resolve within workspace
        path = validate_workspace_path("test.py")
        assert str(workspace) in str(path)

    def test_traversal_dotdot(self):
        with pytest.raises(SanitisationError, match="traversal"):
            validate_workspace_path("../../etc/passwd")

    def test_traversal_absolute(self):
        with pytest.raises(SanitisationError, match="traversal"):
            validate_workspace_path("/etc/passwd")

    def test_nested_path(self, workspace):
        path = validate_workspace_path("subdir/test.py")
        assert str(workspace) in str(path)


# ── Auth ────────────────────────────────────────────────────────────


class TestAuth:
    def test_stdio_mode_bypasses_auth(self):
        ctx = authenticate_request(is_stdio=True)
        assert ctx.is_stdio
        assert "admin" in ctx.scopes

    def test_require_scope_pass(self):
        ctx = AuthContext(scopes=["read", "execute"])
        require_scope(ctx, "execute")  # should not raise

    def test_require_scope_fail(self):
        ctx = AuthContext(scopes=["read"])
        with pytest.raises(AuthError):
            require_scope(ctx, "admin")

    def test_auth_disabled(self):
        ctx = authenticate_request(authorization=None, is_stdio=False)
        assert ctx.key_name == "auth_disabled"
