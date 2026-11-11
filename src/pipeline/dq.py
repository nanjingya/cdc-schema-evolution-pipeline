"""Data quality. Incomplete on purpose."""
from __future__ import annotations

from collections import Counter


def split_quarantine(rows: list[dict], rules: list[dict]) -> tuple[list[dict], list[dict]]:
    # TODO: implement real rule evaluation; currently only drops empty email naively
    good, bad = [], []
    seen = Counter()
    for r in rows:
        seen[r.get("event_id")] += 1
        if r.get("op") != "D" and not r.get("email"):
            bad.append({**r, "_dq_reason": "email_required_unless_delete"})
        else:
            good.append(r)
    # duplicates not handled yet
    return good, bad
