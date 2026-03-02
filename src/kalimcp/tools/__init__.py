"""Kali tool catalog — data model, YAML loader, and in-memory cache."""

from __future__ import annotations

import functools
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums & Models
# ---------------------------------------------------------------------------

VALID_CATEGORIES = (
    "recon", "vuln", "webapp", "password", "wireless",
    "exploit", "sniff", "post", "forensic", "social",
    "crypto", "reverse",
)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CategoryInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    description: str


class KaliToolInfo(BaseModel):
    """Data model for a single Kali tool."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Tool binary name")
    category: str = Field(..., description="Category key (recon, vuln, …)")
    description: str = Field(default="", description="Short description")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    allowed: bool = Field(default=True, description="Whether execution is permitted")
    default_args_template: str = Field(default="", description="Default arguments template")


class ToolCatalog(BaseModel):
    """In-memory representation of the full catalog."""

    categories: dict[str, CategoryInfo] = Field(default_factory=dict)
    tools: list[KaliToolInfo] = Field(default_factory=list)

    # ----- query helpers -----

    def get_tool(self, name: str) -> Optional[KaliToolInfo]:
        for t in self.tools:
            if t.name == name:
                return t
        return None

    def is_allowed(self, name: str) -> bool:
        tool = self.get_tool(name)
        return tool is not None and tool.allowed

    def list_by_category(self, category: str) -> list[KaliToolInfo]:
        return [t for t in self.tools if t.category == category]

    def list_all(self) -> list[KaliToolInfo]:
        return list(self.tools)


# ---------------------------------------------------------------------------
# Catalog loading (cached)
# ---------------------------------------------------------------------------

_DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[3] / "config" / "tools_catalog.yaml"


@functools.lru_cache(maxsize=1)
def load_catalog(path: str | Path | None = None) -> ToolCatalog:
    """Load the tool catalog YAML and return a validated ``ToolCatalog``."""
    p = Path(path) if path else _DEFAULT_CATALOG_PATH
    if not p.exists():
        return ToolCatalog()
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    categories = {
        k: CategoryInfo(**v) for k, v in raw.get("categories", {}).items()
    }
    tools = [KaliToolInfo(**t) for t in raw.get("tools", [])]
    return ToolCatalog(categories=categories, tools=tools)


def get_catalog() -> ToolCatalog:
    """Convenience accessor — returns the cached catalog."""
    return load_catalog()
