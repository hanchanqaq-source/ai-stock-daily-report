"""Public-safe dynamic account page model helpers.

The page model is read-only. It derives page visibility from the account group
assets in memory and never mutates asset status, reads private configuration, or
connects to reports, notifications, databases, or external data sources.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.account_groups import validate_account_group
from src.asset_model import build_asset_public_safe_view, is_active_asset, scan_asset_for_sensitive_values
from src.holding_watch_compare import build_holding_watch_comparison

PAGE_ORDER = (
    "overview",
    "funds",
    "stocks",
    "companies",
    "themes",
    "watching",
    "holding_vs_watching",
    "history",
    "settings",
    "empty_state",
)
PAGE_LABELS = {
    "overview": "总览",
    "funds": "基金分析",
    "stocks": "股票分析",
    "companies": "企业观察",
    "themes": "主题 / 行业观察",
    "watching": "收藏 / 观察",
    "holding_vs_watching": "持有 vs 收藏",
    "history": "历史记录",
    "settings": "设置",
    "empty_state": "请添加资产",
}
FUND_TYPES = frozenset({"fund", "etf"})
STOCK_TYPES = frozenset({"stock"})
COMPANY_TYPES = frozenset({"company"})
THEME_TYPES = frozenset({"industry", "theme", "index"})
HISTORY_STATUSES = frozenset({"cleared", "archived"})


def _assets(group: dict[str, Any]) -> list[dict[str, Any]]:
    validate_account_group(group)
    return list(group.get("assets", []))


def _active_assets(group: dict[str, Any]) -> list[dict[str, Any]]:
    return [asset for asset in _assets(group) if is_active_asset(asset)]


def _safe_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_asset_public_safe_view(asset) for asset in assets]


def _count_by_status(assets: list[dict[str, Any]], status: str) -> int:
    return sum(1 for asset in assets if asset.get("status") == status)


def _active_assets_by_types(group: dict[str, Any], asset_types: frozenset[str]) -> list[dict[str, Any]]:
    return [asset for asset in _active_assets(group) if asset.get("type") in asset_types]


def _history_assets(group: dict[str, Any]) -> list[dict[str, Any]]:
    return [asset for asset in _assets(group) if asset.get("status") in HISTORY_STATUSES]


def build_asset_counts(group: dict[str, Any]) -> dict[str, int]:
    assets = _assets(group)
    active_assets = [asset for asset in assets if is_active_asset(asset)]
    return {
        "total": sum(1 for asset in assets if asset.get("status") != "deleted"),
        "active": len(active_assets),
        "holding": _count_by_status(assets, "holding"),
        "watching": _count_by_status(assets, "watching"),
        "cleared": _count_by_status(assets, "cleared"),
        "archived": _count_by_status(assets, "archived"),
        "deleted": _count_by_status(assets, "deleted"),
        "fund": len([asset for asset in active_assets if asset.get("type") in FUND_TYPES]),
        "stock": len([asset for asset in active_assets if asset.get("type") in STOCK_TYPES]),
        "company": len([asset for asset in active_assets if asset.get("type") in COMPANY_TYPES]),
        "theme": len([asset for asset in active_assets if asset.get("type") in THEME_TYPES]),
    }


def get_visible_pages_for_account(group: dict[str, Any]) -> list[str]:
    counts = build_asset_counts(group)
    if counts["active"] == 0:
        pages = ["empty_state"]
        if counts["cleared"] > 0 or counts["archived"] > 0:
            pages.append("history")
        return pages

    pages = ["overview"]
    if counts["fund"] > 0:
        pages.append("funds")
    if counts["stock"] > 0:
        pages.append("stocks")
    if counts["company"] > 0:
        pages.append("companies")
    if counts["theme"] > 0:
        pages.append("themes")
    if counts["watching"] > 0:
        pages.append("watching")
    if counts["holding"] > 0 and counts["watching"] > 0:
        pages.append("holding_vs_watching")
    if counts["cleared"] > 0 or counts["archived"] > 0:
        pages.append("history")
    return [page for page in PAGE_ORDER if page in pages]


def filter_assets_for_page(group: dict[str, Any], page_key: str) -> list[dict[str, Any]]:
    if page_key == "funds":
        assets = _active_assets_by_types(group, FUND_TYPES)
    elif page_key == "stocks":
        assets = _active_assets_by_types(group, STOCK_TYPES)
    elif page_key == "companies":
        assets = _active_assets_by_types(group, COMPANY_TYPES)
    elif page_key == "themes":
        assets = _active_assets_by_types(group, THEME_TYPES)
    elif page_key == "watching":
        assets = [asset for asset in _active_assets(group) if asset.get("status") == "watching"]
    elif page_key == "history":
        assets = _history_assets(group)
    elif page_key == "holding_vs_watching":
        assets = [asset for asset in _active_assets(group) if asset.get("status") in {"holding", "watching"}]
    else:
        assets = []
    return _safe_assets(assets)


def _page_data(group: dict[str, Any], page_key: str, asset_types: frozenset[str] | None = None) -> dict[str, Any]:
    raw_assets = _active_assets_by_types(group, asset_types or frozenset()) if asset_types else []
    assets = _safe_assets(raw_assets)
    return {
        "page_key": page_key,
        "label": PAGE_LABELS[page_key],
        "asset_count": len(assets),
        "holding_count": _count_by_status(raw_assets, "holding"),
        "watching_count": _count_by_status(raw_assets, "watching"),
        "assets": assets,
    }


def build_overview_page_data(group: dict[str, Any]) -> dict[str, Any]:
    counts = build_asset_counts(group)
    return {"page_key": "overview", "label": PAGE_LABELS["overview"], "asset_counts": counts, "summary": "账户动态页面总览。"}


def build_fund_page_data(group: dict[str, Any]) -> dict[str, Any]:
    return _page_data(group, "funds", FUND_TYPES)


def build_stock_page_data(group: dict[str, Any]) -> dict[str, Any]:
    return _page_data(group, "stocks", STOCK_TYPES)


def build_company_page_data(group: dict[str, Any]) -> dict[str, Any]:
    return _page_data(group, "companies", COMPANY_TYPES)


def build_theme_page_data(group: dict[str, Any]) -> dict[str, Any]:
    return _page_data(group, "themes", THEME_TYPES)


def build_watching_page_data(group: dict[str, Any]) -> dict[str, Any]:
    assets = [asset for asset in _active_assets(group) if asset.get("status") == "watching"]
    return {"page_key": "watching", "label": PAGE_LABELS["watching"], "asset_count": len(assets), "assets": _safe_assets(assets)}


def build_history_page_data(group: dict[str, Any]) -> dict[str, Any]:
    assets = _history_assets(group)
    return {
        "page_key": "history",
        "label": PAGE_LABELS["history"],
        "cleared_count": _count_by_status(assets, "cleared"),
        "archived_count": _count_by_status(assets, "archived"),
        "assets": _safe_assets(assets),
    }


def build_empty_state_page_data(group: dict[str, Any]) -> dict[str, Any]:
    validate_account_group(group)
    return {
        "page_key": "empty_state",
        "label": PAGE_LABELS["empty_state"],
        "message": "当前账户暂无持有或收藏资产，请先添加基金、股票或企业。",
    }


def build_holding_vs_watching_page_data(group: dict[str, Any]) -> dict[str, Any]:
    comparison = build_holding_watch_comparison(group)
    return {"page_key": "holding_vs_watching", "label": PAGE_LABELS["holding_vs_watching"], "comparison": comparison}


def build_page_tabs(group: dict[str, Any]) -> list[dict[str, Any]]:
    tabs = []
    for page in get_visible_pages_for_account(group):
        tab = {"key": page, "label": PAGE_LABELS[page], "enabled": True, "reason": _page_reason(page)}
        assets = filter_assets_for_page(group, page)
        if page not in {"overview", "empty_state", "holding_vs_watching"}:
            tab["asset_count"] = len(assets)
        tabs.append(tab)
    return tabs


def _page_reason(page_key: str) -> str:
    return {
        "overview": "账户总览默认显示",
        "funds": "账户中存在基金资产",
        "stocks": "账户中存在股票资产",
        "companies": "账户中存在企业资产",
        "themes": "账户中存在主题、行业或指数资产",
        "watching": "账户中存在收藏资产",
        "holding_vs_watching": "账户中同时存在持有和收藏资产",
        "history": "账户中存在已清仓或归档资产",
        "empty_state": "账户中暂无持有或收藏资产",
        "settings": "账户设置入口",
    }[page_key]


def _build_page_data(group: dict[str, Any], page_key: str) -> dict[str, Any]:
    builders = {
        "overview": build_overview_page_data,
        "funds": build_fund_page_data,
        "stocks": build_stock_page_data,
        "companies": build_company_page_data,
        "themes": build_theme_page_data,
        "watching": build_watching_page_data,
        "holding_vs_watching": build_holding_vs_watching_page_data,
        "history": build_history_page_data,
        "empty_state": build_empty_state_page_data,
    }
    return builders[page_key](group)


def build_account_page_model(group: dict[str, Any]) -> dict[str, Any]:
    original = deepcopy(group)
    validate_account_group(group)
    visible_pages = get_visible_pages_for_account(group)
    model = {
        "account_id": group.get("account_id"),
        "account_name": group.get("account_name"),
        "status": "empty" if visible_pages and visible_pages[0] == "empty_state" else "available",
        "visible_pages": visible_pages,
        "default_page": visible_pages[0],
        "tabs": build_page_tabs(group),
        "asset_counts": build_asset_counts(group),
        "pages": {page: _build_page_data(group, page) for page in visible_pages},
        "warnings": scan_asset_for_sensitive_values(group),
    }
    if group != original:
        raise RuntimeError("build_account_page_model must not mutate group")
    validate_page_model(model)
    return model


def validate_page_model(model: dict[str, Any]) -> None:
    if not isinstance(model, dict):
        raise ValueError("page model must be an object")
    visible_pages = model.get("visible_pages")
    if not isinstance(visible_pages, list) or not visible_pages:
        raise ValueError("visible_pages must be a non-empty list")
    if model.get("default_page") != visible_pages[0]:
        raise ValueError("default_page must be the first visible page")
    if any(page not in PAGE_ORDER for page in visible_pages):
        raise ValueError("visible_pages contains an unsupported page key")
    if visible_pages == ["empty_state"] or visible_pages == ["empty_state", "history"]:
        expected_order = visible_pages
    else:
        expected_order = [page for page in PAGE_ORDER if page in visible_pages]
    if list(visible_pages) != expected_order:
        raise ValueError("visible_pages order is unstable")
    findings = scan_asset_for_sensitive_values(model)
    if findings:
        raise ValueError("page model contains sensitive values: " + "; ".join(findings))
