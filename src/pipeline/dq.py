"""Data quality rules.

Rules come from ``dq_rules`` in the schema registry. Two kinds are supported:

- row expressions, e.g. ``op == 'D' or balance >= 0`` — evaluated per row with
  the row's fields as variables (``null``/``true``/``false`` are also bound);
- uniqueness rules, e.g. ``event_id unique`` — within one batch only the first
  occurrence of the field value is kept, later duplicates are quarantined.

A row that fails any rule is moved to quarantine with ``_dq_reason`` set to the
rule name.
"""
from __future__ import annotations

_EVAL_GLOBALS = {"__builtins__": {}, "null": None, "true": True, "false": False}


def _eval_row_expr(expr: str, row: dict) -> bool:
    return bool(eval(expr, _EVAL_GLOBALS, dict(row)))  # noqa: S307 - sandboxed globals


def split_quarantine(rows: list[dict], rules: list[dict]) -> tuple[list[dict], list[dict]]:
    row_rules: list[tuple[str, str]] = []
    unique_rules: list[tuple[str, str]] = []
    for rule in rules or []:
        name = str(rule.get("name", "dq_rule"))
        expr = str(rule.get("expr", "")).strip()
        if expr.endswith("unique"):
            field = expr.split()[0]
            unique_rules.append((name, field))
        elif expr:
            row_rules.append((name, expr))

    seen: dict[str, set] = {field: set() for _, field in unique_rules}
    good: list[dict] = []
    bad: list[dict] = []
    for row in rows:
        reason = None
        for name, field in unique_rules:
            key = row.get(field)
            if key in seen[field]:
                reason = name
                break
            seen[field].add(key)
        if reason is None:
            for name, expr in row_rules:
                try:
                    ok = _eval_row_expr(expr, row)
                except Exception:
                    ok = False  # missing/invalid field values fail the rule
                if not ok:
                    reason = name
                    break
        if reason is None:
            good.append(row)
        else:
            bad.append({**row, "_dq_reason": reason})
    return good, bad
