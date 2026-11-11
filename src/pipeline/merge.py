"""Lake merge / upsert. Incomplete on purpose."""
from __future__ import annotations

from pathlib import Path
import pandas as pd


def read_lake(lake_dir: Path) -> pd.DataFrame:
    files = list(lake_dir.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def upsert(lake_df: pd.DataFrame, events: list[dict], pk: list[str]) -> pd.DataFrame:
    # BUG: ignores event_ts ordering and soft deletes; last row wins only within batch list order
    df = pd.DataFrame(events)
    if lake_df.empty:
        return df
    out = pd.concat([lake_df, df], ignore_index=True)
    return out.drop_duplicates(subset=pk, keep="last")
