"""CDC ingest. Incomplete on purpose."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_batch(batch_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for p in sorted(batch_dir.glob("*.jsonl")):
        rows.extend(iter_jsonl(p))
    return rows
