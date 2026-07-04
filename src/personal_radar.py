# -*- coding: utf-8 -*-
"""Public-safe demo personal stock/fund impact radar.

The radar only loads committed example configuration by default and only matches
watchlist tags against public market signals.  It never reads real
``data/user_config`` files, never sends notifications, and never persists private
portfolio data.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping

from src.risk_radar import build_risk_radar
from src.trend_analyzer import analyze_multi_window_persistence, analyze_multi_window_trends
from src.user_config import (
    EXAMPLE_CONFIG_DIR,
    get_task_group_by_id,
    get_watchlist_by_id,
    load_user_config,
    scan_config_for_sensitive_values,
)
from src.watchlist_builder import build_watchlist

RADAR_VERSION = 1
_FORBIDDEN = ("买入", "卖出", "加仓", "减仓", "必须买", "必须卖")


def build_personal_radar_for_user(user_id: str, config_dir: str | Path | None = None) -> dict[str, Any]:
    """Build demo personal radar for one example user without reading real config."""
    config = _load_example_only(config_dir)
    user = next((u for u in config.get("users", {}).get("users", []) if u.get("user_id") == user_id), None)
    if not user:
        return _empty_result(user_id=user_id, data_warnings=["未找到示例用户配置。"])
    group_ids = [gid for gid in user.get("task_group_ids", []) if isinstance(gid, str)]
    if not group_ids:
        return _empty_result(user_id=user_id, data_warnings=["示例用户未配置任务组。"])
    result = build_personal_radar_for_task_group(group_ids[0], config_dir=config_dir)
    result["user_id"] = user_id
    result["user_display_name"] = user.get("display_name")
    return _sanitize_result(result)


def build_personal_radar_for_task_group(task_group_id: str, config_dir: str | Path | None = None) -> dict[str, Any]:
    """Build demo radar for one example task group."""
    config = _load_example_only(config_dir)
    group = get_task_group_by_id(config, task_group_id)
    if not group:
        return _empty_result(task_group_id=task_group_id, data_warnings=["未找到示例任务组配置。"])
    watchlist = get_watchlist_by_id(config, str(group.get("watchlist_id") or ""))
    if not watchlist:
        return _empty_result(task_group_id=task_group_id, data_warnings=["未找到示例关注列表配置。"])

    context = _build_market_context()
    items = [analyze_watchlist_item_impact(item, context) for item in watchlist.get("items", []) if isinstance(item, Mapping)]
    signals = [signal for item in items for signal in item.get("signals", [])]
    warnings = list(context.get("data_warnings") or [])
    if context.get("status") != "available":
        warnings.append("公共历史样本不足，示例影响雷达仅返回数据不足状态。")
    status = "available" if any(item.get("signals") for item in items) and context.get("status") == "available" else "insufficient_data"
    tag_text = "、".join(group.get("focus_tags", [])[:3]) if isinstance(group.get("focus_tags"), list) else ""
    result = {
        "radar_version": RADAR_VERSION,
        "status": status,
        "user_id": None,
        "user_display_name": None,
        "task_group_id": task_group_id,
        "task_group_name": group.get("name"),
        "watchlist_id": watchlist.get("watchlist_id"),
        "watchlist_name": watchlist.get("name"),
        "data_date": context.get("data_date"),
        "summary": f"{group.get('name') or '示例任务组'}今日主要观察{tag_text or '示例标签'}相关公共市场信号。" if status == "available" else "公共历史样本不足，暂不生成完整个人影响雷达。",
        "items": items,
        "overall_watch_points": _dedupe([point for item in items for point in item.get("watch_points", [])])[:8],
        "data_warnings": _dedupe(warnings),
        "matched_signal_count": len(signals),
    }
    return _sanitize_result(result)


def analyze_watchlist_item_impact(item: Mapping[str, Any], market_context: Mapping[str, Any]) -> dict[str, Any]:
    """Analyze one watchlist item against public market context."""
    signals = match_item_tags_to_market_signals(item, market_context)
    risks = [s for s in signals if s.get("signal_type") == "risk_signal"]
    positives = [s for s in signals if s.get("signal_type") == "positive_signal"]
    if market_context.get("status") != "available" or not signals:
        level = "数据不足"
        if not signals:
            signals = [{"signal_type": "insufficient_data", "tag": None, "source": "personal_radar", "reason": "未匹配到有效公共市场信号或历史样本不足。"}]
    elif risks:
        level = "高"
    elif len(positives) >= 2:
        level = "中"
    else:
        level = "低"
    tags = [str(tag) for tag in item.get("tags", []) if str(tag).strip()] if isinstance(item.get("tags", []), list) else []
    watch_points = _watch_points(item, signals)
    return _sanitize_result({
        "type": item.get("type"),
        "name": item.get("name"),
        "code": item.get("code"),
        "market": item.get("market"),
        "tags": tags,
        "impact_level": level,
        "signals": signals,
        "risks": risks,
        "watch_points": watch_points,
    })


def match_item_tags_to_market_signals(item: Mapping[str, Any], market_context: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Match item tags to stable public market signal buckets."""
    tags = [str(tag).strip() for tag in item.get("tags", []) if str(tag).strip()] if isinstance(item.get("tags", []), list) else []
    buckets = market_context.get("signals", {}) if isinstance(market_context.get("signals"), Mapping) else {}
    rules = (
        ("positive_signal", "sector_persistence", "persistent_leaders", "在近 5 日持续走强方向中出现"),
        ("positive_signal", "trend_analyzer", "warming", "命中市场升温相关方向"),
        ("positive_signal", "watchlist_builder", "watchlist_diffusion", "出现在观察清单扩散方向中"),
        ("risk_signal", "sector_persistence", "pullback_risks", "进入冲高回落风险方向"),
        ("risk_signal", "sector_persistence", "persistent_laggers", "进入持续走弱方向"),
        ("risk_signal", "risk_radar", "risk_radar", "出现在风险雷达相关方向中"),
        ("neutral_signal", "sector_persistence", "short_term_breakouts", "出现在短线爆发方向中"),
        ("neutral_signal", "sector_persistence", "rotation_candidates", "出现在轮动扩散方向中"),
    )
    out: list[dict[str, Any]] = []
    for tag in tags:
        for signal_type, source, bucket, reason in rules:
            if _tag_matches(tag, buckets.get(bucket, [])):
                out.append({"signal_type": signal_type, "tag": tag, "source": source, "reason": f"{tag}{reason}"})
    return _dedupe_signals(out)


def render_personal_radar_markdown(radar_result: Mapping[str, Any]) -> str:
    """Render demo radar result as Markdown without writing files."""
    positives = sum(1 for item in radar_result.get("items", []) for s in item.get("signals", []) if s.get("signal_type") == "positive_signal")
    risks = sum(1 for item in radar_result.get("items", []) for s in item.get("signals", []) if s.get("signal_type") == "risk_signal")
    insuff = sum(1 for item in radar_result.get("items", []) for s in item.get("signals", []) if s.get("signal_type") == "insufficient_data")
    lines = [
        "# 示例个人影响雷达",
        "",
        "> 示例报告：仅使用 example 配置和公共市场数据，不接入真实用户、真实 Discord 或任何私人资产数据。",
        "",
        "## 1. 示例用户 / 任务组",
        "",
        f"- 用户：{radar_result.get('user_display_name') or radar_result.get('user_id') or '示例用户'}",
        f"- 任务组：{radar_result.get('task_group_name') or radar_result.get('task_group_id') or '示例任务组'}",
        f"- 关注列表：{radar_result.get('watchlist_name') or radar_result.get('watchlist_id') or '示例关注列表'}",
        "",
        "## 2. 今日影响概览",
        "",
        f"- 相关正向信号：{positives}",
        f"- 相关风险信号：{risks}",
        f"- 数据不足提示：{insuff + len(radar_result.get('data_warnings', []))}",
        "",
        "## 3. 关注对象影响",
        "",
    ]
    for item in radar_result.get("items", []):
        lines.extend([
            f"- 名称：{item.get('name') or '-'}",
            f"  - 类型：{item.get('type') or '-'}",
            f"  - 标签：{'、'.join(item.get('tags', [])) or '-'}",
            f"  - 影响等级：{item.get('impact_level') or '数据不足'}",
            f"  - 相关信号：{_format_signals(item.get('signals', []), exclude='risk_signal')}",
            f"  - 风险提示：{_format_signals(item.get('risks', []))}",
            f"  - 观察点：{'；'.join(item.get('watch_points', [])) or '继续观察公共市场信号变化。'}",
        ])
    lines.extend(["", "## 4. 观察重点", ""])
    points = radar_result.get("overall_watch_points", []) or ["公共历史样本不足时，仅保留观察，不生成进一步判断。"]
    lines.extend(f"- {point}" for point in points)
    return _clean("\n".join(lines).rstrip() + "\n")


def load_demo_personal_radar() -> dict[str, Any]:
    """Load demo radar for the committed public example user."""
    return build_personal_radar_for_user("demo_public_user", config_dir=EXAMPLE_CONFIG_DIR)


def _load_example_only(config_dir: str | Path | None) -> dict[str, Any]:
    base = Path(config_dir) if config_dir is not None else EXAMPLE_CONFIG_DIR
    if base != EXAMPLE_CONFIG_DIR and base.name != "examples":
        return {"users": {"config_version": 1, "users": []}, "task_groups": {"config_version": 1, "task_groups": []}, "watchlists": {"config_version": 1, "watchlists": []}}
    return load_user_config(base)


def _build_market_context() -> dict[str, Any]:
    trend = analyze_multi_window_trends([5, 20])
    persistence = analyze_multi_window_persistence([5, 20])
    risk = build_risk_radar(trend=trend, persistence=persistence, history_count=(trend.get("5") or {}).get("data_points"))
    public_watch = build_watchlist(trend=trend, persistence=persistence, risk_radar=risk)
    five = trend.get("5", {}) if isinstance(trend, Mapping) else {}
    status = "available" if five.get("status") == "available" else "insufficient_data"
    signals = _extract_public_signal_buckets(trend, persistence, risk, public_watch)
    return {"status": status, "data_date": _safe_data_date(five), "signals": signals, "data_warnings": list(five.get("data_warnings") or [])}


def _extract_public_signal_buckets(trend, persistence, risk, public_watch) -> dict[str, list[str]]:
    p5 = persistence.get("5", {}) if isinstance(persistence, Mapping) else {}
    out = {k: [] for k in ("persistent_leaders", "short_term_breakouts", "rotation_candidates", "pullback_risks", "persistent_laggers", "risk_radar", "watchlist_diffusion", "warming")}
    for group in ("industries", "concepts"):
        data = p5.get(group, {}) if isinstance(p5, Mapping) else {}
        for key in ("persistent_leaders", "short_term_breakouts", "rotation_candidates", "pullback_risks", "persistent_laggers"):
            out[key].extend(_names(data.get(key, [])))
    for r in risk.get("risks", []) if isinstance(risk, Mapping) else []:
        evidence = r.get("evidence", {}) if isinstance(r, Mapping) else {}
        out["risk_radar"].extend(_flatten_names(evidence.get("directions", [])))
    for row in public_watch.get("sector_watch", []) if isinstance(public_watch, Mapping) else []:
        out["watchlist_diffusion"].extend(_extract_known_tags(str(row.get("item") or ""), out["persistent_leaders"] + out["rotation_candidates"]))
    five = trend.get("5", {}) if isinstance(trend, Mapping) else {}
    if (five.get("market_temperature") or {}).get("direction") == "升温":
        out["warming"].extend(out["persistent_leaders"] + out["short_term_breakouts"])
    return {key: _dedupe([x for x in values if x]) for key, values in out.items()}


def _empty_result(**kwargs) -> dict[str, Any]:
    result = {"radar_version": RADAR_VERSION, "status": "insufficient_data", "user_id": None, "task_group_id": None, "watchlist_id": None, "data_date": None, "summary": "示例配置或公共历史数据不足。", "items": [], "overall_watch_points": [], "data_warnings": []}
    result.update(kwargs)
    return _sanitize_result(result)


def _safe_data_date(five: Mapping[str, Any]) -> str:
    value = str(five.get("latest_date") or date.today().isoformat())
    today = date.today().isoformat()
    return min(value, today)


def _tag_matches(tag: str, candidates: Any) -> bool:
    return any(tag in str(c) or str(c) in tag for c in _flatten_names(candidates))

def _names(items):
    return [str(x.get("name") if isinstance(x, Mapping) else x) for x in items if str(x.get("name") if isinstance(x, Mapping) else x).strip()]

def _flatten_names(value):
    if isinstance(value, Mapping):
        return _names(value.values())
    if isinstance(value, list):
        return _names(value)
    return [str(value)] if value else []

def _extract_known_tags(text: str, known: list[str]) -> list[str]:
    return [name for name in known if name and name in text]

def _dedupe(items):
    return list(dict.fromkeys(str(x) for x in items if x))

def _dedupe_signals(signals):
    seen = set(); out = []
    for signal in signals:
        key = (signal.get("signal_type"), signal.get("tag"), signal.get("source"), signal.get("reason"))
        if key not in seen:
            seen.add(key); out.append(signal)
    return out

def _watch_points(item, signals):
    tags = item.get("tags", []) if isinstance(item.get("tags", []), list) else []
    points = []
    for signal in signals:
        tag = signal.get("tag") or (tags[0] if tags else "相关方向")
        if signal.get("signal_type") == "risk_signal":
            points.append(f"观察{tag}方向风险信号是否收敛。")
        elif signal.get("signal_type") == "positive_signal":
            points.append(f"观察{tag}方向是否继续保持持续性。")
        elif signal.get("signal_type") == "neutral_signal":
            points.append(f"观察{tag}方向是否具备持续性。")
    return _dedupe(points)[:4]

def _format_signals(signals, exclude=None):
    rows = [s for s in signals if isinstance(s, Mapping) and s.get("signal_type") != exclude]
    return "；".join(f"{s.get('tag') or '数据'}：{s.get('reason')}（{s.get('source')}）" for s in rows) or "暂无"

def _clean(text: str) -> str:
    value = str(text)
    for word in _FORBIDDEN:
        value = value.replace(word, "观察")
    return value

def _sanitize_result(result):
    text_findings = scan_config_for_sensitive_values(result)
    if text_findings:
        raise ValueError("Personal radar output contains sensitive values: " + "; ".join(text_findings))
    if isinstance(result, dict):
        return {k: _sanitize_result(v) for k, v in result.items()}
    if isinstance(result, list):
        return [_sanitize_result(v) for v in result]
    if isinstance(result, str):
        return _clean(result)
    return result
