"""CLI entry. Incomplete on purpose — must be completed to satisfy acceptance tests."""
from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--incoming", type=Path, required=True)
    run.add_argument("--lake", type=Path, required=True)
    run.add_argument("--meta", type=Path, required=True)
    run.add_argument("--quarantine", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.cmd == "run":
        raise NotImplementedError(
            "Implement end-to-end CDC run: schema evolution, watermark/late data, DQ quarantine, "
            "ordered upsert with soft-delete, idempotent checkpoint/manifest, parquet lake write."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
