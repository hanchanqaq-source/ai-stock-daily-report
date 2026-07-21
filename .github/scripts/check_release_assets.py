"""Check the desktop Release asset names, sizes, metadata, and Portable checksum."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def expected_asset_names(tag: str) -> set[str]:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError(f"unsupported release tag: {tag}")
    installer = f"daily-stock-analysis-windows-installer-{tag}.exe"
    portable = f"股票基金质量分析系统-Portable-{tag}.zip"
    return {
        installer,
        f"{installer}.blockmap",
        f"daily-stock-analysis-windows-noinstall-{tag}.zip",
        portable,
        f"{portable}.sha256",
        f"daily-stock-analysis-macos-x64-{tag}.dmg",
        f"daily-stock-analysis-macos-arm64-{tag}.dmg",
        "latest.yml",
    }


def verify_assets(asset_dir: Path, tag: str) -> None:
    expected = expected_asset_names(tag)
    missing = sorted(name for name in expected if not (asset_dir / name).is_file())
    if missing:
        raise ValueError(f"missing release assets: {', '.join(missing)}")

    empty = sorted(name for name in expected if (asset_dir / name).stat().st_size <= 0)
    if empty:
        raise ValueError(f"empty release assets: {', '.join(empty)}")

    portable_name = f"股票基金质量分析系统-Portable-{tag}.zip"
    checksum_path = asset_dir / f"{portable_name}.sha256"
    checksum_line = checksum_path.read_text(encoding="utf-8").strip()
    checksum_match = re.fullmatch(r"([0-9a-fA-F]{64})\s{2}(.+)", checksum_line)
    if not checksum_match or checksum_match.group(2) != portable_name:
        raise ValueError("Portable checksum file must contain the exact ZIP filename")
    actual_hash = hashlib.sha256((asset_dir / portable_name).read_bytes()).hexdigest()
    if actual_hash.lower() != checksum_match.group(1).lower():
        raise ValueError("Portable ZIP SHA-256 does not match its checksum file")

    version = tag[1:]
    installer_name = f"daily-stock-analysis-windows-installer-{tag}.exe"
    latest_text = (asset_dir / "latest.yml").read_text(encoding="utf-8")
    if not re.search(rf"(?m)^version:\s*['\"]?{re.escape(version)}['\"]?\s*$", latest_text):
        raise ValueError("latest.yml version does not match the release tag")
    if installer_name not in latest_text:
        raise ValueError("latest.yml does not reference the expected Windows installer")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_release_assets.py ASSET_DIR RELEASE_TAG")
    asset_dir = Path(sys.argv[1]).resolve()
    verify_assets(asset_dir, sys.argv[2])
    print(f"Release asset contract passed for {sys.argv[2]}")


if __name__ == "__main__":
    main()
