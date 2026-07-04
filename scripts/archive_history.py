#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI for generating monthly market-history archive summaries."""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.history_archive import generate_delete_candidates, generate_monthly_archive  # noqa: E402


def _latest_month() -> str:
    history_dir = ROOT / "data" / "history"
    dates = []
    if history_dir.exists():
        for path in history_dir.glob("market_snapshot_*.json"):
            value = path.stem.removeprefix("market_snapshot_")
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                continue
            if parsed <= date.today():
                dates.append(parsed)
    target = max(dates) if dates else date.today()
    return target.strftime("%Y-%m")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate history archive summaries without deleting important files.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--month", help="Month to archive, format YYYY-MM")
    group.add_argument("--latest-month", action="store_true", help="Archive the latest month found in data/history")
    parser.add_argument("--generate-delete-candidates", action="store_true", help="Generate delete candidate checklist without deleting files")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        month = args.month or (_latest_month() if args.latest_month else None)
        if month:
            generate_monthly_archive(month)
        if args.generate_delete_candidates:
            generate_delete_candidates()
        if not month and not args.generate_delete_candidates:
            parser.print_help()
        return 0
    except Exception as exc:  # pragma: no cover
        print(f"[HISTORY_ARCHIVE] failed error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
