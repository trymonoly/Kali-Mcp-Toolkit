"""Tool engine tests — catalog loading, list, help, exec_tool."""

from __future__ import annotations

import pytest

from kalimcp.auth import AuthContext
from kalimcp.tools import VALID_CATEGORIES, get_catalog, load_catalog
from kalimcp.tools.tool_engine import exec_tool, list_kali_tools, tool_help


# ── Catalog ─────────────────────────────────────────────────────────


class TestCatalog:
    def test_catalog_loads(self):
        catalog = get_catalog()
        assert len(catalog.tools) > 0

    def test_all_categories_present(self):
        catalog = get_catalog()
        present = {t.category for t in catalog.tools}
        for cat in VALID_CATEGORIES:
            assert cat in present, f"Category '{cat}' has no tools"

    def test_get_tool(self):
        catalog = get_catalog()
        tool = catalog.get_tool("nmap")
        assert tool is not None
        assert tool.name == "nmap"
        assert tool.category == "recon"

    def test_get_missing_tool(self):
        catalog = get_catalog()
        assert catalog.get_tool("nonexistent") is None

    def test_is_allowed(self):
        catalog = get_catalog()
        assert catalog.is_allowed("nmap")
        assert not catalog.is_allowed("nonexistent")

    def test_list_by_category(self):
        catalog = get_catalog()
        recon = catalog.list_by_category("recon")
        assert len(recon) > 0
        assert all(t.category == "recon" for t in recon)


# ── list_kali_tools ─────────────────────────────────────────────────


class TestListKaliTools:
    @pytest.mark.asyncio
    async def test_list_all(self):
        auth = AuthContext(scopes=["read"])
        result = await list_kali_tools("all", _auth=auth)
        assert "nmap" in result
        assert "信息收集" in result or "Reconnaissance" in result

    @pytest.mark.asyncio
    async def test_list_by_category(self):
        auth = AuthContext(scopes=["read"])
        result = await list_kali_tools("recon", _auth=auth)
        assert "nmap" in result
        assert "sqlmap" not in result

    @pytest.mark.asyncio
    async def test_list_invalid_category(self):
        auth = AuthContext(scopes=["read"])
        result = await list_kali_tools("invalid_cat", _auth=auth)
        assert "Error" in result


# ── exec_tool ───────────────────────────────────────────────────────


class TestExecTool:
    @pytest.mark.asyncio
    async def test_rejected_unknown_tool(self):
        auth = AuthContext(scopes=["read", "execute"])
        result = await exec_tool("fake_tool_xyz", "", _auth=auth)
        assert "Error" in result
        assert "not registered" in result

    @pytest.mark.asyncio
    async def test_rejected_injection(self):
        auth = AuthContext(scopes=["read", "execute"])
        result = await exec_tool("nmap", "192.168.1.1; rm -rf /", _auth=auth)
        assert "Error" in result


# ── tool_help ───────────────────────────────────────────────────────


class TestToolHelp:
    @pytest.mark.asyncio
    async def test_help_unknown_tool(self):
        auth = AuthContext(scopes=["read"])
        result = await tool_help("nonexistent_tool_xyz", _auth=auth)
        assert "not in the catalog" in result
