"""Acceptance tests for the CDC lakehouse pipeline. Do not weaken these tests."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def workspace(tmp_path: Path):
    incoming = tmp_path / "incoming"
    lake = tmp_path / "lake" / "customers"
    meta = tmp_path / "meta"
    quarantine = tmp_path / "quarantine"
    shutil.copytree(ROOT / "data" / "incoming", incoming)
    shutil.copytree(ROOT / "meta", meta)
    lake.mkdir(parents=True)
    quarantine.mkdir(parents=True)
    return incoming, lake, meta, quarantine


def _run(incoming, lake, meta, quarantine):
    from src.pipeline.cli import main

    rc = main(
        [
            "run",
            "--incoming",
            str(incoming),
            "--lake",
            str(lake.parent),
            "--meta",
            str(meta),
            "--quarantine",
            str(quarantine),
        ]
    )
    assert rc == 0


def test_end_to_end_semantics(workspace):
    incoming, lake, meta, quarantine = workspace
    _run(incoming, lake, meta, quarantine)

    # idempotent
    _run(incoming, lake, meta, quarantine)

    df = pd.concat([pd.read_parquet(p) for p in lake.glob("*.parquet")], ignore_index=True)
    assert set(df["customer_id"]) == {"c2"}  # c1 deleted, c3/c4 quarantined
    row = df.set_index("customer_id").loc["c2"]
    assert row["email"] == "b2@x.com"  # late e7 must NOT override fresher e4
    assert row["tier"] == "gold"
    assert "is_deleted" in df.columns
    assert int(row.get("is_deleted", 0)) == 0

    # quarantine contains dq failures and duplicate event_id
    qfiles = list(quarantine.rglob("*.jsonl"))
    assert qfiles, "quarantine output missing"
    qrows = []
    for qp in qfiles:
        for line in qp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                qrows.append(json.loads(line))
    reasons = {r.get("_dq_reason") for r in qrows}
    assert "balance_non_negative_on_upsert" in reasons or any(r.get("customer_id") == "c3" for r in qrows)
    assert "email_required_unless_delete" in reasons or any(r.get("customer_id") == "c4" for r in qrows)
    assert "event_id_unique_in_batch" in reasons or sum(1 for r in qrows if r.get("event_id") == "e4") >= 1

    # schema evolution persisted
    reg = (meta / "schema_registry.yaml").read_text(encoding="utf-8")
    assert "tier" in reg

    # checkpoints for both batches
    assert (meta / "checkpoints" / "batch_001.json").exists()
    assert (meta / "checkpoints" / "batch_002.json").exists()
