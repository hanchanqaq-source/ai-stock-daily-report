from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / ".github" / "scripts" / "check_release_assets.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_release_assets", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_assets(module, root: Path, tag: str = "v3.21.1") -> None:
    for name in module.expected_asset_names(tag):
        (root / name).write_bytes(b"asset")

    portable_name = f"股票基金质量分析系统-Portable-{tag}.zip"
    portable_bytes = b"portable zip"
    (root / portable_name).write_bytes(portable_bytes)
    digest = hashlib.sha256(portable_bytes).hexdigest()
    (root / f"{portable_name}.sha256").write_text(
        f"{digest}  {portable_name}\n",
        encoding="utf-8",
    )
    installer_name = f"daily-stock-analysis-windows-installer-{tag}.exe"
    (root / "latest.yml").write_text(
        f"version: {tag[1:]}\npath: {installer_name}\n",
        encoding="utf-8",
    )


def test_complete_release_asset_set_passes(tmp_path: Path) -> None:
    module = _load_module()
    _create_assets(module, tmp_path)

    module.verify_assets(tmp_path, "v3.21.1")


def test_missing_release_asset_is_rejected(tmp_path: Path) -> None:
    module = _load_module()
    _create_assets(module, tmp_path)
    (tmp_path / "daily-stock-analysis-macos-arm64-v3.21.1.dmg").unlink()

    with pytest.raises(ValueError, match="missing release assets"):
        module.verify_assets(tmp_path, "v3.21.1")


def test_portable_checksum_mismatch_is_rejected(tmp_path: Path) -> None:
    module = _load_module()
    _create_assets(module, tmp_path)
    checksum = tmp_path / "股票基金质量分析系统-Portable-v3.21.1.zip.sha256"
    checksum.write_text(f"{'0' * 64}  股票基金质量分析系统-Portable-v3.21.1.zip\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        module.verify_assets(tmp_path, "v3.21.1")
