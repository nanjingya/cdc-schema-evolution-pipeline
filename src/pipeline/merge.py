"""Lake merge / upsert.

Merge semantics:
- primary key from the registry (``customer_id``)
- events are ordered by ``event_ts``; the newest event per primary key wins
- ``op == 'D'`` is a soft delete: the row is kept during the merge with
  ``is_deleted=True`` and filtered out of the published lake snapshot, while
  the ``is_deleted`` column remains part of the lake schema
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_lake(lake_dir: Path) -> pd.DataFrame:
    files = sorted(lake_dir.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def upsert(lake_df: pd.DataFrame, events_df: pd.DataFrame, pk: list[str]) -> pd.DataFrame:
    """Apply events to the lake snapshot, newest ``event_ts`` wins per pk."""
    combined = pd.concat([lake_df, events_df], ignore_index=True)
    combined = combined.sort_values("event_ts", kind="mergesort")
    combined = combined.drop_duplicates(subset=pk, keep="last")
    return combined.reset_index(drop=True)


def publish_snapshot(merged: pd.DataFrame) -> pd.DataFrame:
    """Rows visible in the lake: soft-deleted rows are removed, the
    ``is_deleted`` column is kept."""
    if "is_deleted" not in merged.columns:
        return merged
    visible = merged[~merged["is_deleted"].fillna(False).astype(bool)]
    return visible.reset_index(drop=True)
