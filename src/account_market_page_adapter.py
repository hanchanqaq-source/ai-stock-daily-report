"""Attach offline market / NAV summaries to the dynamic account page model.

This adapter only reshapes the fixture/model-only output from
``account_realtime_summary`` for page consumption. It does not fetch real market
sources, persist values, mutate assets, or generate trading advice.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from src.account_page_model import build_account_page_model, validate_page_model
from src.account_realtime_summary import build_account_realtime_summary
from src.fund_nav_provider import FundNavProvider
from src.realtime_quote_provider import QuoteProvider

DISCLAIMER = "本页面模型只做展示结构，不构成交易建议。"
MARKET_DISCLAIMER = "本阶段为 mock / fixture 数据，不代表真实行情。"
FUND_DISCLAIMER = "场外基金不支持真正实时价格，盘中估算仅供观察，最终以基金公司公布净值为准。"
BASE_WARNING = "本阶段为 mock / fixture 数据，不代表真实行情或真实基金净值。"
ALLOWED_DATA_MODES = {"fixture_only", "model_only", "mixed_fixture_only"}
QUOTE_TYPES = {"stock", "etf", "index"}
STATUS_KEYS = ("available_count", "unsupported_count", "provider_error_count", "invalid_request_count")


def _results(summary: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [item for item in summary.get("results") or [] if isinstance(item, Mapping)]


def _asset(item: Mapping[str, Any]) -> Mapping[str, Any]:
    asset = item.get("asset") or {}
    return asset if isinstance(asset, Mapping) else {}


def _status_counts(results: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "available_count": sum(1 for item in results if item.get("data_status") == "available"),
        "unsupported_count": sum(1 for item in results if item.get("data_status") == "unsupported"),
        "provider_error_count": sum(1 for item in results if item.get("data_status") == "provider_error"),
        "invalid_request_count": sum(1 for item in results if item.get("data_status") == "invalid_request"),
    }


def _section_status(counts: Mapping[str, int]) -> str:
    total = sum(int(counts.get(key, 0)) for key in STATUS_KEYS)
    if total <= 0:
        return "empty"
    if int(counts.get("available_count", 0)) == total:
        return "available"
    if int(counts.get("available_count", 0)) > 0:
        return "partial_available"
    return "empty"


def _safe_result(item: Mapping[str, Any]) -> dict[str, Any]:
    asset = _asset(item)
    return {
        "asset": {
            "asset_id": asset.get("asset_id"),
            "type": asset.get("type"),
            "code": asset.get("code"),
            "name": asset.get("name"),
            "market": asset.get("market"),
            "status": asset.get("status"),
        },
        "result_kind": item.get("result_kind"),
        "data_status": item.get("data_status"),
        "source_status": item.get("source_status"),
        "fixture_only": bool(item.get("fixture_only")),
        "has_real_market_data": False,
        "reason": item.get("reason") or "",
    }


def _base_section(summary: Mapping[str, Any], results: list[Mapping[str, Any]], *, include_results: bool = True) -> dict[str, Any]:
    counts = _status_counts(results)
    section = {
        "status": _section_status(counts),
        "data_mode": summary.get("data_mode") if summary.get("data_mode") in ALLOWED_DATA_MODES else "model_only",
        "has_real_market_data": False,
        **counts,
        "result_count": len(results),
        "disclaimer": MARKET_DISCLAIMER,
    }
    if include_results:
        section["results"] = [_safe_result(item) for item in results]
    return section


def filter_market_results_for_page(market_summary: Mapping[str, Any], page_key: str) -> list[dict[str, Any]]:
    """Return page-specific market results without mutating the summary."""

    results = _results(market_summary)
    if page_key == "funds":
        filtered = [item for item in results if item.get("result_kind") == "fund_nav" and _asset(item).get("type") == "fund"]
    elif page_key == "stocks":
        filtered = [item for item in results if item.get("result_kind") == "realtime_quote" and _asset(item).get("type") in QUOTE_TYPES]
    elif page_key == "watching":
        filtered = [item for item in results if _asset(item).get("status") == "watching"]
    elif page_key in {"overview", "holding_vs_watching"}:
        filtered = results
    else:
        filtered = []
    return [dict(item) for item in filtered]


def build_overview_market_section(market_summary: Mapping[str, Any]) -> dict[str, Any]:
    section = _base_section(market_summary, filter_market_results_for_page(market_summary, "overview"), include_results=False)
    section["status"] = market_summary.get("status") if market_summary.get("status") in {"available", "partial_available", "empty"} else section["status"]
    return section


def build_funds_market_section(market_summary: Mapping[str, Any]) -> dict[str, Any]:
    section = _base_section(market_summary, filter_market_results_for_page(market_summary, "funds"))
    section["description"] = "场外基金展示净值 / 估算净值框架摘要，最终以基金公司公布净值为准。"
    return section


def build_stocks_market_section(market_summary: Mapping[str, Any]) -> dict[str, Any]:
    section = _base_section(market_summary, filter_market_results_for_page(market_summary, "stocks"))
    section["description"] = "股票 / ETF / 官方指数展示行情框架摘要。"
    return section


def build_watching_market_section(market_summary: Mapping[str, Any]) -> dict[str, Any]:
    section = _base_section(market_summary, filter_market_results_for_page(market_summary, "watching"))
    section["description"] = "收藏资产单独展示行情 / 净值状态摘要。"
    return section


def build_holding_vs_watching_market_section(market_summary: Mapping[str, Any]) -> dict[str, Any]:
    results = filter_market_results_for_page(market_summary, "holding_vs_watching")
    holding = [item for item in results if _asset(item).get("status") == "holding"]
    watching = [item for item in results if _asset(item).get("status") == "watching"]
    return {
        "status": _section_status(_status_counts(results)),
        "data_mode": market_summary.get("data_mode") if market_summary.get("data_mode") in ALLOWED_DATA_MODES else "model_only",
        "has_real_market_data": False,
        "holding": _status_counts(holding),
        "watching": _status_counts(watching),
        "disclaimer": "仅展示持有 / 收藏状态统计，不生成交易动作。",
    }


def attach_market_summary_to_page_model(page_model: Mapping[str, Any], market_summary: Mapping[str, Any]) -> dict[str, Any]:
    model = deepcopy(dict(page_model))
    pages = model.setdefault("pages", {})
    visible_pages = list(model.get("visible_pages") or [])
    model["data_mode"] = market_summary.get("data_mode") if market_summary.get("data_mode") in ALLOWED_DATA_MODES else "model_only"
    model["has_real_market_data"] = False
    model["disclaimer"] = DISCLAIMER
    warnings = list(model.get("warnings") or [])
    if BASE_WARNING not in warnings:
        warnings.append(BASE_WARNING)
    model["warnings"] = warnings

    builders = {
        "overview": build_overview_market_section,
        "funds": build_funds_market_section,
        "stocks": build_stocks_market_section,
        "watching": build_watching_market_section,
        "holding_vs_watching": build_holding_vs_watching_market_section,
    }
    for page_key in visible_pages:
        if page_key in builders and page_key in pages:
            pages[page_key] = deepcopy(pages[page_key])
            pages[page_key]["market_summary"] = builders[page_key](market_summary)
        elif page_key == "history" and page_key in pages:
            pages[page_key] = deepcopy(pages[page_key])
            pages[page_key]["market_note"] = "历史资产默认不参与当前行情 / 净值汇总。"
    validate_account_market_page_model(model)
    return model


def build_account_page_model_with_market_data(
    group: Mapping[str, Any],
    quote_provider: QuoteProvider | None = None,
    fund_nav_provider: FundNavProvider | None = None,
    market_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    original = deepcopy(dict(group))
    page_model = build_account_page_model(dict(group))
    summary = market_summary or build_account_realtime_summary(group, quote_provider, fund_nav_provider)
    model = attach_market_summary_to_page_model(page_model, summary)
    if dict(group) != original:
        raise RuntimeError("build_account_page_model_with_market_data must not mutate group")
    return model


def validate_account_market_page_model(model: Mapping[str, Any]) -> bool:
    validate_page_model(dict(model))
    if model.get("has_real_market_data") is not False:
        raise ValueError("has_real_market_data must be false")
    if model.get("data_mode") not in ALLOWED_DATA_MODES:
        raise ValueError("unsupported data_mode")
    for page in (model.get("pages") or {}).values():
        section = page.get("market_summary") if isinstance(page, Mapping) else None
        if section and section.get("has_real_market_data") is not False:
            raise ValueError("page market_summary must not contain real market data")
    return True


def _summary_line(section: Mapping[str, Any]) -> str:
    return (
        f"可用 {section.get('available_count', 0)} / "
        f"不支持 {section.get('unsupported_count', 0)} / "
        f"provider_error {section.get('provider_error_count', 0)}"
    )


def render_account_market_page_demo_markdown(model: Mapping[str, Any]) -> str:
    pages = model.get("pages") or {}
    overview = (pages.get("overview") or {}).get("market_summary") or {}
    funds = (pages.get("funds") or {}).get("market_summary") or {}
    stocks = (pages.get("stocks") or {}).get("market_summary") or {}
    watching = (pages.get("watching") or {}).get("market_summary") or {}
    return "\n".join([
        "# 账户页面行情 / 净值展示 Demo",
        "",
        "## 1. 页面概览",
        f"- 账户：{model.get('account_name') or model.get('account_id') or '-'}",
        f"- 可见页面：{', '.join(model.get('visible_pages') or [])}",
        f"- 数据模式：{model.get('data_mode')}",
        f"- 是否真实行情：{str(model.get('has_real_market_data')).lower()}",
        "",
        "## 2. 总览页行情摘要",
        f"- {_summary_line(overview)}",
        "",
        "## 3. 基金页净值摘要",
        f"- {_summary_line(funds)}",
        "- 场外基金展示净值 / 估算净值框架摘要。",
        "",
        "## 4. 股票页行情摘要",
        f"- {_summary_line(stocks)}",
        "- 股票 / ETF / 官方指数展示行情框架结果。",
        "",
        "## 5. 收藏页摘要",
        f"- {_summary_line(watching)}",
        "- watching 资产单独展示。",
        "",
        "## 6. 数据说明",
        f"- {MARKET_DISCLAIMER}",
        f"- {FUND_DISCLAIMER}",
        "- 本结果只做观察，不构成交易建议。",
    ])
