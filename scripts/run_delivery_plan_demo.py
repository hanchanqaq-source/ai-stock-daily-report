#!/usr/bin/env python3
"""Print the public-safe multi-user delivery dry-run demo."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.user_report_dispatcher import load_demo_delivery_plan, render_delivery_plan_markdown


def main() -> int:
    plan = load_demo_delivery_plan()
    print(render_delivery_plan_markdown(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
