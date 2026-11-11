"""Schema registry load/merge helpers. Incomplete on purpose."""
from __future__ import annotations

from pathlib import Path
import yaml


def load_registry(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def evolve_schema(registry: dict, observed_fields: dict) -> dict:
    # BUG/TODO: currently blindly overwrites types; must implement widen-only rules
    fields = dict(registry.get("fields", {}))
    fields.update(observed_fields)
    registry = dict(registry)
    registry["fields"] = fields
    registry["version"] = int(registry.get("version", 1)) + 1
    return registry
