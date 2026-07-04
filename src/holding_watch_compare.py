"""Public-safe holding vs watching comparison helpers.

This module only reads an account group in memory. It does not read private
configuration, persist results, mutate asset status, or connect to reports,
notifications, data sources, SQLite, or LLM providers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any

from src.account_groups import validate_account_group
from src.asset_model import (
    ALLOWED_ASSET_STATUSES,
    build_asset_public_safe_view,
    is_holding_asset,
    is_watching_asset,
)

_NON_ADVICE_NOTICE = "本报告只做观察，不构成交易建议。"


def _safe_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_asset_public_safe_view(asset) for asset in assets]


def split_holding_and_watching_assets(group: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return current holding and watching assets; ignore cleared/archived/deleted."""

    validate_account_group(group)
    assets = group.get("assets", [])
    return {
        "holding": [deepcopy(asset) for asset in assets if is_holding_asset(asset)],
        "watching": [deepcopy(asset) for asset in assets if is_watching_asset(asset)],
    }


def count_assets_by_status(group: dict[str, Any]) -> dict[str, int]:
    """Count all allowed statuses without including them in current comparison."""

    validate_account_group(group)
    counts = {status: 0 for status in ALLOWED_ASSET_STATUSES}
    for asset in group.get("assets", []):
        status = asset.get("status")
        if status in counts:
            counts[status] += 1
    return counts


def collect_asset_tags(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect tag frequency and asset IDs in stable order."""

    tag_counts: Counter[str] = Counter()
    tag_assets: dict[str, list[str]] = defaultdict(list)
    for asset in assets:
        asset_id = asset.get("asset_id")
        seen_in_asset: set[str] = set()
        for tag in asset.get("tags", []) or []:
            if not isinstance(tag, str) or not tag or tag in seen_in_asset:
                continue
            seen_in_asset.add(tag)
            tag_counts[tag] += 1
            if isinstance(asset_id, str):
                tag_assets[tag].append(asset_id)
    return [
        {"tag": tag, "count": count, "asset_ids": tag_assets[tag]}
        for tag, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def compare_tag_sets(holding_tags: list[dict[str, Any]], watching_tags: list[dict[str, Any]]) -> dict[str, list[str]]:
    holding_set = {item["tag"] for item in holding_tags}
    watching_set = {item["tag"] for item in watching_tags}
    return {
        "common_tags": sorted(holding_set & watching_set),
        "holding_only_tags": sorted(holding_set - watching_set),
        "watching_only_tags": sorted(watching_set - holding_set),
    }


def build_empty_comparison(group: dict[str, Any], reason: str) -> dict[str, Any]:
    validate_account_group(group)
    counts = count_assets_by_status(group)
    return {
        "account_id": group.get("account_id"),
        "account_name": group.get("account_name"),
        "status": "empty",
        "summary": reason,
        "asset_counts": counts,
        "holding": {"assets": [], "tags": [], "top_tags": [], "risk_signals": [], "watch_points": []},
        "watching": {"assets": [], "tags": [], "top_tags": [], "risk_signals": [], "watch_points": []},
        "comparison": {
            "common_tags": [],
            "holding_only_tags": [],
            "watching_only_tags": [],
            "watching_hotter_than_holding": False,
            "holding_risk_higher_than_watching": False,
            "observations": [reason, _NON_ADVICE_NOTICE],
        },
        "data_warnings": [reason],
    }


def extract_market_context_from_existing_signals(signals: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """Normalize optional existing structured signals; never fetch or infer data."""

    if not isinstance(signals, dict):
        return {"hot_tags": [], "risk_tags": []}
    return {
        "hot_tags": [tag for tag in signals.get("hot_tags", []) if isinstance(tag, str)],
        "risk_tags": [tag for tag in signals.get("risk_tags", []) if isinstance(tag, str)],
    }


def _tag_names(tags: list[dict[str, Any]]) -> list[str]:
    return [item["tag"] for item in tags]


def _watch_points(kind: str, top_tags: list[str], market_context: dict[str, list[str]]) -> list[str]:
    points: list[str] = []
    if top_tags:
        label = "持有" if kind == "holding" else "收藏"
        points.append(f"观察{label}资产标签集中度：{', '.join(top_tags)}。")
    hot = sorted(set(top_tags) & set(market_context.get("hot_tags", [])))
    risk = sorted(set(top_tags) & set(market_context.get("risk_tags", [])))
    if hot and kind == "watching":
        points.append("收藏资产标签中出现已有强势方向信号，仅作为观察，不代表交易建议。")
    if risk:
        label = "持有" if kind == "holding" else "收藏"
        points.append(f"{label}资产标签中出现已有风险信号方向，后续观察风险是否扩散。")
    return points


def build_holding_watch_comparison(group: dict[str, Any], market_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a structured holding vs watching comparison for a public-safe group."""

    validate_account_group(group)
    split = split_holding_and_watching_assets(group)
    holding_assets = split["holding"]
    watching_assets = split["watching"]
    if not holding_assets and not watching_assets:
        return build_empty_comparison(group, "当前没有持有或收藏资产可对比。")

    counts = count_assets_by_status(group)
    context = extract_market_context_from_existing_signals(market_context)
    holding_tags = collect_asset_tags(holding_assets)
    watching_tags = collect_asset_tags(watching_assets)
    tag_comparison = compare_tag_sets(holding_tags, watching_tags)
    holding_top = _tag_names(holding_tags[:5])
    watching_top = _tag_names(watching_tags[:5])
    holding_risks = sorted(set(holding_top) & set(context["risk_tags"]))
    watching_risks = sorted(set(watching_top) & set(context["risk_tags"]))
    observations: list[str] = []
    data_warnings: list[str] = []
    if not watching_assets:
        data_warnings.append("当前没有收藏资产可对比。")
    if not holding_assets:
        data_warnings.append("当前没有持有资产可对比。")
    if tag_comparison["common_tags"]:
        observations.append("持有和收藏存在共同关注方向，说明账户关注方向较集中。")
    if tag_comparison["watching_only_tags"] or tag_comparison["holding_only_tags"]:
        observations.append("持有方向和收藏方向存在差异，后续可观察轮动是否扩散。")
    if holding_risks:
        observations.append("持有资产标签中出现已有风险信号方向，后续观察风险是否扩散。")
    if not observations:
        observations.append("当前仅基于资产数量和标签进行对比观察。")

    hotter = bool(set(watching_top) & set(context["hot_tags"])) and not bool(set(holding_top) & set(context["hot_tags"]))
    risk_higher = len(holding_risks) > len(watching_risks)
    summary = f"持有资产主要集中在{('、'.join(holding_top) if holding_top else '暂无标签')}；收藏资产主要集中在{('、'.join(watching_top) if watching_top else '暂无标签')}。"
    return {
        "account_id": group.get("account_id"),
        "account_name": group.get("account_name"),
        "status": "available" if holding_assets and watching_assets else "insufficient_data",
        "summary": summary,
        "asset_counts": counts,
        "holding": {
            "assets": _safe_assets(holding_assets),
            "tags": holding_tags,
            "top_tags": holding_top,
            "risk_signals": holding_risks,
            "watch_points": _watch_points("holding", holding_top, context),
        },
        "watching": {
            "assets": _safe_assets(watching_assets),
            "tags": watching_tags,
            "top_tags": watching_top,
            "risk_signals": watching_risks,
            "watch_points": _watch_points("watching", watching_top, context),
        },
        "comparison": {
            **tag_comparison,
            "watching_hotter_than_holding": hotter,
            "holding_risk_higher_than_watching": risk_higher,
            "observations": observations,
        },
        "data_warnings": data_warnings,
    }


def _format_list(items: list[str]) -> str:
    return "、".join(items) if items else "暂无"


def render_holding_watch_comparison_markdown(result: dict[str, Any]) -> str:
    """Render a demo markdown report without trading instructions or private money fields."""

    counts = result.get("asset_counts", {})
    holding = result.get("holding", {})
    watching = result.get("watching", {})
    comparison = result.get("comparison", {})
    lines = [
        "# 持有 vs 收藏对比 Demo",
        "",
        "## 1. 账户概览",
        f"- 账户：{result.get('account_name') or result.get('account_id') or '示例账户'}",
        f"- 持有资产数量：{counts.get('holding', 0)}",
        f"- 收藏资产数量：{counts.get('watching', 0)}",
        f"- 已清仓资产数量：{counts.get('cleared', 0)}",
        "",
        "## 2. 持有资产方向",
        f"- 主要标签：{_format_list(holding.get('top_tags', []))}",
        f"- 观察点：{_format_list(holding.get('watch_points', []))}",
        "",
        "## 3. 收藏资产方向",
        f"- 主要标签：{_format_list(watching.get('top_tags', []))}",
        f"- 观察点：{_format_list(watching.get('watch_points', []))}",
        "",
        "## 4. 差异观察",
        f"- 共同方向：{_format_list(comparison.get('common_tags', []))}",
        f"- 仅持有方向：{_format_list(comparison.get('holding_only_tags', []))}",
        f"- 仅收藏方向：{_format_list(comparison.get('watching_only_tags', []))}",
        f"- 观察重点：{_format_list(comparison.get('observations', []))}",
        "",
        "## 5. 风险与数据说明",
        f"- 数据不足说明：{_format_list(result.get('data_warnings', []))}",
        f"- 风险提示：{_format_list(holding.get('risk_signals', []) + watching.get('risk_signals', []))}",
        f"- {_NON_ADVICE_NOTICE}",
    ]
    return "\n".join(lines) + "\n"
