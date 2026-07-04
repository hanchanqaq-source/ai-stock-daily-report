#!/usr/bin/env python3
"""Run the public-safe example personal radar demo."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.personal_radar import load_demo_personal_radar, render_personal_radar_markdown


def main() -> int:
    radar = load_demo_personal_radar()
    print(render_personal_radar_markdown(radar))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
