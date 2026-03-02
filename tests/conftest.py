"""Shared pytest fixtures for KaliMcp tests."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalimcp.config import AppConfig, init_config


@pytest.fixture(autouse=True)
def _reset_config(tmp_path):
    """Provide a clean config for each test with workspace in tmp_path."""
    os.environ["KALIMCP_WORKSPACE__ROOT"] = str(tmp_path / "workspace")
    os.environ["KALIMCP_LOGGING__AUDIT_LOG"] = str(tmp_path / "audit.log")
    os.environ["KALIMCP_AUTH__ENABLED"] = "false"
    cfg = init_config()  # Load defaults + env overrides
    (tmp_path / "workspace").mkdir(exist_ok=True)
    yield cfg
    # Cleanup env vars
    for key in list(os.environ):
        if key.startswith("KALIMCP_"):
            del os.environ[key]


@pytest.fixture
def workspace(tmp_path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    return ws
