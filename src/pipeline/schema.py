"""Schema registry load/evolve helpers.

Evolution semantics (driven by ``evolution_rules`` in the registry):
- new columns are added as nullable columns when ``allow_add_nullable_columns``
- numeric types may only widen (e.g. int32 -> int64) per ``allow_type_widen``
- columns are never dropped (``forbid_drop_columns``)
- narrowing a type is rejected (``forbid_type_narrow``)
"""
from __future__ import annotations

from pathlib import Path

import yaml


def load_registry(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_registry(path: Path, registry: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(registry, f, sort_keys=False, allow_unicode=True)


def _infer_value_type(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int64"
    if isinstance(value, float):
        return "float64"
    return "string"


def observe_fields(rows: list[dict]) -> dict[str, str]:
    """Infer a {field: type} mapping from a batch of JSON rows."""
    values: dict[str, list] = {}
    for row in rows:
        for key, val in row.items():
            values.setdefault(key, []).append(val)
    observed: dict[str, str] = {}
    for key, vals in values.items():
        types = {_infer_value_type(v) for v in vals if v is not None}
        if not types:
            observed[key] = "string"
        elif types == {"int64", "float64"}:
            observed[key] = "float64"
        elif len(types) == 1:
            observed[key] = types.pop()
        else:
            observed[key] = "string"
    return observed


def evolve_schema(registry: dict, observed_fields: dict) -> tuple[dict, bool]:
    """Merge observed fields into the registry.

    Returns ``(new_registry, changed)``. ``version`` is bumped only when the
    field set or a field type actually changes. Raises ``ValueError`` when an
    observed change violates the evolution rules.
    """
    rules = registry.get("evolution_rules", {}) or {}
    allow_add = rules.get("allow_add_nullable_columns", True)
    widen = rules.get("allow_type_widen", {}) or {}
    forbid_narrow = rules.get("forbid_type_narrow", True)

    fields = dict(registry.get("fields", {}) or {})
    changed = False
    for name, obs_type in observed_fields.items():
        if name not in fields:
            if not allow_add:
                raise ValueError(f"schema evolution: new column not allowed: {name}")
            fields[name] = obs_type  # new columns are nullable by definition
            changed = True
            continue
        cur = fields[name]
        if cur == obs_type:
            continue
        # ISO-8601 strings are the wire representation of timestamps.
        if cur == "timestamp" and obs_type == "string":
            continue
        if obs_type in (widen.get(cur) or []):
            fields[name] = obs_type  # allowed widen
            changed = True
            continue
        if cur in (widen.get(obs_type) or []):
            continue  # observed narrower type; keep the wider registered type
        if forbid_narrow:
            raise ValueError(
                f"schema evolution: type change not allowed for {name}: {cur} -> {obs_type}"
            )
    out = dict(registry)
    out["fields"] = fields
    if changed:
        out["version"] = int(registry.get("version", 1)) + 1
    return out, changed
