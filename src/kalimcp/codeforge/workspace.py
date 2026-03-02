"""Workspace management — path security, size limits, directory organisation."""

from __future__ import annotations

from pathlib import Path

from kalimcp.config import get_config
from kalimcp.utils.sanitizer import SanitisationError


def get_workspace_root() -> Path:
    """Return the resolved workspace root directory."""
    cfg = get_config().workspace
    root = Path(cfg.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_workspace_path(relative_path: str) -> Path:
    """Resolve *relative_path* within the workspace, blocking traversal.

    Raises ``SanitisationError`` if the resolved path escapes the workspace.
    """
    root = get_workspace_root()
    target = (root / relative_path).resolve()

    if not str(target).startswith(str(root)):
        raise SanitisationError(
            f"Path traversal detected: '{relative_path}' resolves to '{target}' which is outside workspace '{root}'.",
            code="path_traversal",
        )
    return target


def check_file_size(path: Path) -> None:
    """Raise if *path* exceeds the configured max file size."""
    cfg = get_config().workspace
    max_bytes = cfg.max_file_size_mb * 1_048_576
    if path.exists() and path.stat().st_size > max_bytes:
        raise SanitisationError(
            f"File '{path.name}' ({path.stat().st_size} bytes) exceeds limit ({max_bytes} bytes).",
            code="file_too_large",
        )


def ensure_parent(path: Path) -> None:
    """Create parent directories for *path* (within workspace)."""
    root = get_workspace_root()
    parent = path.parent
    if not str(parent).startswith(str(root)):
        raise SanitisationError("Cannot create directories outside workspace.", code="path_traversal")
    parent.mkdir(parents=True, exist_ok=True)
