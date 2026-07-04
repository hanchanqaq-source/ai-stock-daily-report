"""Public-safe asset status transition helpers.

This module only changes in-memory account group dictionaries. It does not read
real user configuration, persist data, delete files, or connect to downstream
report/notification workflows.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from src.account_groups import validate_account_group
from src.asset_model import get_allowed_asset_statuses, validate_asset

ALLOWED_TRANSITIONS = frozenset(
    {
        ("watching", "holding"),
        ("holding", "watching"),
        ("holding", "cleared"),
        ("watching", "archived"),
        ("cleared", "watching"),
        ("cleared", "archived"),
        ("archived", "watching"),
        ("watching", "deleted"),
        ("cleared", "deleted"),
        ("archived", "deleted"),
        ("holding", "deleted"),
    }
)

LOW_RISK_TRANSITIONS = frozenset(
    {
        ("watching", "holding"),
        ("holding", "watching"),
        ("cleared", "watching"),
    }
)
MEDIUM_RISK_TRANSITIONS = frozenset(
    {
        ("holding", "cleared"),
        ("watching", "archived"),
        ("cleared", "archived"),
        ("archived", "watching"),
    }
)
HIGH_RISK_TRANSITIONS = frozenset(
    {
        ("holding", "deleted"),
        ("watching", "deleted"),
        ("cleared", "deleted"),
        ("archived", "deleted"),
    }
)

PUBLIC_ASSET_RESULT_FIELDS = ("asset_id", "code", "name", "type", "market", "tags", "status", "weight_level", "source_status")


def _safe_asset_view(asset: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(asset[key]) for key in PUBLIC_ASSET_RESULT_FIELDS if key in asset}


def _base_error(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    result = {"status": status, "will_apply": False, "reason": reason, "warnings": []}
    result.update(extra)
    return result


def find_asset_for_status_change(
    group: dict[str, Any], asset_id: str | None = None, code: str | None = None
) -> dict[str, Any]:
    """Find one asset by asset_id or code without guessing on conflicts."""

    validate_account_group(group)
    if not asset_id and not code:
        return _base_error("invalid_request", "asset_id 或 code 至少需要提供一个。")

    assets = group.get("assets", [])
    if asset_id:
        for index, asset in enumerate(assets):
            if asset.get("asset_id") == asset_id:
                return {"status": "found", "asset": asset, "asset_index": index, "warnings": []}
        return _base_error("not_found", f"未找到 asset_id={asset_id} 的资产。", asset_id=asset_id)

    matches = [(index, asset) for index, asset in enumerate(assets) if asset.get("code") == code]
    if not matches:
        return _base_error("not_found", f"未找到 code={code} 的资产。", code=code)
    if len(matches) > 1:
        return _base_error(
            "conflict",
            "code 匹配到多个资产，请指定 asset_id。",
            code=code,
            matches=[{"asset_id": asset.get("asset_id"), "name": asset.get("name"), "status": asset.get("status")} for _, asset in matches],
        )
    index, asset = matches[0]
    return {"status": "found", "asset": asset, "asset_index": index, "warnings": []}


def validate_status_transition(from_status: str, to_status: str) -> dict[str, Any]:
    allowed_statuses = set(get_allowed_asset_statuses())
    if to_status not in allowed_statuses:
        return _base_error("invalid_request", f"不支持的目标状态: {to_status}", safe_to_apply=False)
    if from_status not in allowed_statuses:
        return _base_error("invalid_request", f"不支持的原状态: {from_status}", safe_to_apply=False)
    if from_status == to_status:
        return {"status": "valid", "safe_to_apply": True, "warnings": ["资产已经处于目标状态。"]}
    if from_status == "deleted" and to_status != "deleted":
        return _base_error("blocked", "本阶段不支持从 deleted 恢复资产状态。", safe_to_apply=False, requires_confirm=True)
    if (from_status, to_status) not in ALLOWED_TRANSITIONS:
        return _base_error("blocked", f"不允许的状态流转: {from_status} -> {to_status}", safe_to_apply=False)
    if (from_status, to_status) == ("holding", "deleted"):
        return _base_error(
            "blocked",
            "holding -> deleted 属于高风险操作，本阶段需要二次确认，暂不直接执行。",
            safe_to_apply=False,
            requires_confirm=True,
            requires_double_confirm=True,
        )
    return {"status": "valid", "safe_to_apply": True, "warnings": []}


def get_status_change_risk_level(from_status: str, to_status: str) -> str:
    transition = (from_status, to_status)
    if transition in HIGH_RISK_TRANSITIONS:
        return "high"
    if transition in MEDIUM_RISK_TRANSITIONS:
        return "medium"
    if transition in LOW_RISK_TRANSITIONS or from_status == to_status:
        return "low"
    return "blocked"


def _build_impact(from_status: str, to_status: str) -> list[str]:
    impact: list[str] = []
    if to_status == "holding":
        impact.append("该资产将显示在当前持有列表。")
    if to_status == "watching":
        impact.append("该资产将显示在收藏或观察列表，不代表真实持有。")
    if to_status == "cleared":
        impact.extend(["该资产将不再显示在当前持有列表。", "该资产仍会保留在已清仓记录中。", "不会删除历史记录。"])
    if to_status == "archived":
        impact.extend(["该资产默认不显示在主页面。", "该资产记录仍会保留，可后续恢复观察。"])
    if to_status == "deleted":
        impact.extend(["该资产将被标记为 deleted 并在后续默认隐藏。", "本阶段 deleted 只是状态标记，不会物理删除文件。", "不会静默删除历史记录。"])
    if from_status == "holding" and to_status == "deleted":
        impact.append("持有中资产删除属于高风险操作，需要二次确认，本阶段默认阻断。")
    return impact or ["资产状态将被更新，原始记录仍保留在输入分组结构中。"]


def build_status_change_preview(asset: dict[str, Any], to_status: str, reason: str | None = None) -> dict[str, Any]:
    validate_asset(asset)
    from_status = asset.get("status")
    transition = validate_status_transition(from_status, to_status)
    risk_level = get_status_change_risk_level(from_status, to_status)
    safe_to_apply = transition.get("safe_to_apply", False)
    result = {
        "status": "preview" if transition["status"] == "valid" else transition["status"],
        "will_apply": False,
        "requires_confirm": True,
        "requires_double_confirm": bool(transition.get("requires_double_confirm", False)),
        "risk_level": risk_level,
        "asset_id": asset.get("asset_id"),
        "code": asset.get("code"),
        "name": asset.get("name"),
        "from_status": from_status,
        "to_status": to_status,
        "reason": reason,
        "impact": _build_impact(from_status, to_status),
        "safe_to_apply": safe_to_apply,
        "warnings": list(transition.get("warnings", [])),
    }
    if transition["status"] != "valid":
        result["blocked_reason"] = transition.get("reason")
    if risk_level == "high":
        result["warnings"].append("高风险操作：请确认影响范围；本阶段不会物理删除文件。")
    return result


def preview_asset_status_change(
    group: dict[str, Any], asset_id: str | None = None, code: str | None = None, to_status: str | None = None, reason: str | None = None
) -> dict[str, Any]:
    if not to_status:
        return _base_error("invalid_request", "to_status 是必填项。", requires_confirm=True)
    found = find_asset_for_status_change(group, asset_id=asset_id, code=code)
    if found.get("status") != "found":
        return found
    return build_status_change_preview(found["asset"], to_status, reason=reason)


def build_status_change_result(
    group: dict[str, Any], asset: dict[str, Any], from_status: str, to_status: str, reason: str | None = None, confirm: bool = False
) -> dict[str, Any]:
    updated_asset = _safe_asset_view(asset)
    return {
        "status": "applied" if confirm else "blocked",
        "will_apply": bool(confirm),
        "asset_id": asset.get("asset_id"),
        "code": asset.get("code"),
        "name": asset.get("name"),
        "from_status": from_status,
        "to_status": to_status,
        "changed_at": datetime.now().replace(microsecond=0).isoformat(),
        "reason": reason,
        "updated_asset": updated_asset,
        "updated_group": deepcopy(group),
        "warnings": [],
    }


def apply_asset_status_change(
    group: dict[str, Any], asset_id: str | None = None, code: str | None = None, to_status: str | None = None, reason: str | None = None, confirm: bool = False
) -> dict[str, Any]:
    preview = preview_asset_status_change(group, asset_id=asset_id, code=code, to_status=to_status, reason=reason)
    if preview.get("status") != "preview" or not preview.get("safe_to_apply", False):
        return preview
    if not confirm:
        blocked = dict(preview)
        blocked["status"] = "blocked"
        blocked["reason"] = "confirm=false，未执行状态变更"
        blocked["will_apply"] = False
        blocked["requires_confirm"] = True
        return blocked

    updated_group = deepcopy(group)
    found = find_asset_for_status_change(updated_group, asset_id=asset_id, code=code)
    if found.get("status") != "found":
        return found
    asset = found["asset"]
    from_status = asset["status"]
    asset["status"] = to_status
    validate_asset(asset)
    validate_account_group(updated_group)
    return build_status_change_result(updated_group, asset, from_status, to_status, reason=reason, confirm=True)


def mark_asset_holding(group: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return apply_asset_status_change(group, to_status="holding", **kwargs)


def mark_asset_watching(group: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return apply_asset_status_change(group, to_status="watching", **kwargs)


def mark_asset_cleared(group: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return apply_asset_status_change(group, to_status="cleared", **kwargs)


def mark_asset_archived(group: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return apply_asset_status_change(group, to_status="archived", **kwargs)


def mark_asset_deleted(group: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return apply_asset_status_change(group, to_status="deleted", **kwargs)
