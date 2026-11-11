"""CLI entry for the CDC schema-evolution lakehouse pipeline.

Usage:
    python -m src.pipeline.cli run --incoming <dir> --lake <dir> \
        --meta <dir> --quarantine <dir>

For every ``batch_*`` directory under ``--incoming`` (processed in name order,
skipping batches that already have a checkpoint):

1. evolve the schema registry with any new columns (widen-only types);
2. quarantine events that arrive later than ``watermark.lateness`` relative to
   the batch's max ``event_ts`` (``_dq_reason=late_event``);
3. evaluate ``dq_rules`` and quarantine failures;
4. upsert surviving events into ``<lake>/<entity>/`` ordered by ``event_ts``
   (``op=D`` soft-deletes; newer events override older ones);
5. write ``meta/checkpoints/<batch_id>.json`` and
   ``meta/manifests/<batch_id>.json``.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .checkpoint import already_processed, write_checkpoint
from .dq import split_quarantine
from .ingest import load_batch
from .merge import publish_snapshot, read_lake, upsert
from .schema import evolve_schema, load_registry, observe_fields, save_registry

_LATENESS_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ms|s|m|h|d)\s*$", re.IGNORECASE)
_LATENESS_UNITS = {
    "ms": timedelta(milliseconds=1),
    "s": timedelta(seconds=1),
    "m": timedelta(minutes=1),
    "h": timedelta(hours=1),
    "d": timedelta(days=1),
}


def _parse_lateness(value) -> timedelta:
    match = _LATENESS_RE.match(str(value))
    if not match:
        raise ValueError(f"invalid watermark lateness: {value!r}")
    amount = float(match.group(1))
    return _LATENESS_UNITS[match.group(2).lower()] * amount


def _split_late_events(rows: list[dict], field: str, lateness: timedelta) -> tuple[list[dict], list[dict]]:
    """Split off rows whose event_ts lags the batch max by more than ``lateness``."""
    if not rows:
        return [], []
    stamps = pd.to_datetime([r.get(field) for r in rows], utc=True, errors="coerce")
    threshold = stamps.max() - lateness
    on_time: list[dict] = []
    late: list[dict] = []
    for row, ts in zip(rows, stamps):
        if pd.notna(ts) and ts < threshold:
            late.append({**row, "_dq_reason": "late_event"})
        else:
            on_time.append(row)
    return on_time, late


def _write_quarantine(quarantine_dir: Path, batch_id: str, rows: list[dict]) -> str | None:
    if not rows:
        return None
    path = quarantine_dir / f"{batch_id}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(path)


def _write_manifest(meta_dir: Path, batch_id: str, payload: dict) -> None:
    path = meta_dir / "manifests" / f"{batch_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_pipeline(incoming: Path, lake: Path, meta: Path, quarantine: Path) -> None:
    registry_path = meta / "schema_registry.yaml"
    registry = load_registry(registry_path)
    entity = registry.get("entity", "customers")
    pk = list(registry.get("primary_key", ["customer_id"]))
    watermark = registry.get("watermark", {}) or {}
    wm_field = watermark.get("field", "event_ts")
    lateness = _parse_lateness(watermark.get("lateness", "0s"))

    lake_dir = lake / entity
    lake_dir.mkdir(parents=True, exist_ok=True)
    quarantine.mkdir(parents=True, exist_ok=True)

    if incoming.exists():
        batch_dirs = sorted(
            p for p in incoming.iterdir() if p.is_dir() and p.name.startswith("batch_")
        )
    else:
        batch_dirs = []

    for batch_dir in batch_dirs:
        batch_id = batch_dir.name
        if already_processed(meta, batch_id):
            continue  # idempotent: checkpoint exists -> skip

        input_files = [str(p) for p in sorted(batch_dir.glob("*.jsonl"))]
        rows = load_batch(batch_dir)

        # 1. schema evolution (add nullable columns, widen-only types)
        registry, changed = evolve_schema(registry, observe_fields(rows))
        if changed:
            save_registry(registry_path, registry)

        # 2. watermark: quarantine events late by more than `lateness`
        on_time, quarantined = _split_late_events(rows, wm_field, lateness)

        # 3. data quality rules
        good, bad = split_quarantine(on_time, registry.get("dq_rules", []))
        quarantined.extend(bad)

        # 4. merge into the lake (ordered upsert + soft delete)
        outputs: list[str] = []
        if good:
            events_df = pd.DataFrame(good)
            events_df[wm_field] = pd.to_datetime(events_df[wm_field], utc=True)
            events_df["is_deleted"] = events_df["op"].eq("D")
            merged = upsert(read_lake(lake_dir), events_df, pk)
            out_path = lake_dir / f"{entity}.parquet"
            publish_snapshot(merged).to_parquet(out_path, index=False)
            outputs.append(str(out_path))

        quarantine_file = _write_quarantine(quarantine, batch_id, quarantined)

        # 5. checkpoint + manifest
        processed_at = datetime.now(timezone.utc).isoformat()
        write_checkpoint(
            meta,
            batch_id,
            {
                "batch_id": batch_id,
                "processed_at": processed_at,
                "row_in": len(rows),
                "row_out": len(good),
                "quarantine_count": len(quarantined),
            },
        )
        _write_manifest(
            meta,
            batch_id,
            {
                "batch_id": batch_id,
                "processed_at": processed_at,
                "inputs": input_files,
                "outputs": outputs,
                "quarantine_file": quarantine_file,
                "schema_version": registry.get("version"),
            },
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cdc-pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--incoming", type=Path, required=True)
    run.add_argument("--lake", type=Path, required=True)
    run.add_argument("--meta", type=Path, required=True)
    run.add_argument("--quarantine", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.cmd == "run":
        run_pipeline(args.incoming, args.lake, args.meta, args.quarantine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
