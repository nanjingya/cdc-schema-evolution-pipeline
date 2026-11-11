"""Checkpoint / manifest. Incomplete on purpose."""
from __future__ import annotations

import json
from pathlib import Path


def already_processed(meta_dir: Path, batch_id: str) -> bool:
    p = meta_dir / "checkpoints" / f"{batch_id}.json"
    return p.exists()


def write_checkpoint(meta_dir: Path, batch_id: str, payload: dict) -> None:
    p = meta_dir / "checkpoints" / f"{batch_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
