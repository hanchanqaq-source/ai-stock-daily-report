"""Verifiable asset enrichment framework.

This module defines deterministic structures for future enrichment providers. It
never performs network lookups and the bundled example records are fixtures only;
they must not be treated as verified public market facts.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from src.asset_model import normalize_asset_type, normalize_market, normalize_source_status, validate_asset
from src.code_identifier import identify_code, normalize_code_input

ALLOWED_PROVIDER_TYPES = {"fixture", "market_data", "fund_data", "public_web", "official", "manual_user_input", "internal_history"}
ALLOWED_FIELD_STATUSES = {"verified", "unknown", "pending_confirmation", "conflict", "manual_user_input"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
SCALAR_FIELDS = ("name", "type", "market", "industry", "concept", "fund_theme")
LIST_FIELDS = ("tags",)
ALL_FIELDS = SCALAR_FIELDS + LIST_FIELDS
EXAMPLE_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "config" / "examples" / "asset_enrichment.example.json"

Provider = Callable[[str], Mapping[str, Any] | None]


def _confidence(value: Any) -> str:
    return str(value).strip().lower() if str(value).strip().lower() in ALLOWED_CONFIDENCE else "low"


def _field(value: Any, status: str, confidence: str, reason: str, sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    normalized_status = status if status in ALLOWED_FIELD_STATUSES else "unknown"
    return {"value": value, "status": normalized_status, "confidence": _confidence(confidence), "reason": str(reason or "未提供原因。"), "sources": list(sources or [])}


def _empty_fields(reason: str, status: str = "unknown") -> dict[str, Any]:
    fields = {name: _field(None, status, "low", reason) for name in SCALAR_FIELDS}
    fields["tags"] = []
    return fields


def build_unknown_enrichment(code: str | None, reason: str) -> dict[str, Any]:
    return {"code": normalize_code_input(code), "status": "unknown", "confidence": "low", "needs_user_confirmation": True, "fields": _empty_fields(reason), "sources": [], "conflicts": [], "usable_for_formal_analysis": False, "reason": reason}


def build_pending_enrichment(code: str | None, reason: str) -> dict[str, Any]:
    return {"code": normalize_code_input(code), "status": "pending_confirmation", "confidence": "low", "needs_user_confirmation": True, "fields": _empty_fields(reason, "pending_confirmation"), "sources": [], "conflicts": [], "usable_for_formal_analysis": False, "reason": reason}


def build_conflict_enrichment(code: str | None, conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    reason = "多个补全来源给出了不同字段值，需要人工确认。"
    result = {"code": normalize_code_input(code), "status": "conflict", "confidence": "low", "needs_user_confirmation": True, "fields": _empty_fields(reason, "conflict"), "sources": [], "conflicts": conflicts, "usable_for_formal_analysis": False, "reason": reason}
    return result


def _provider_result(provider: Any, code: str) -> Mapping[str, Any] | None:
    if callable(provider):
        return provider(code)
    if hasattr(provider, "enrich"):
        return provider.enrich(code)
    return None


def enrich_asset(asset_or_code: Any, providers: Iterable[Any] | None = None) -> dict[str, Any]:
    code = asset_or_code.get("code") if isinstance(asset_or_code, Mapping) else asset_or_code
    normalized = normalize_code_input(code)
    if providers is None:
        providers = [example_enrichment_provider]
    results = [dict(result) for provider in providers if (result := _provider_result(provider, normalized))]
    if not results:
        return build_unknown_enrichment(normalized, "没有可查证补全来源。")
    return merge_enrichment_results(results)


def enrich_identification_result(identification_result: Mapping[str, Any], providers: Iterable[Any] | None = None) -> dict[str, Any]:
    code = normalize_code_input(identification_result.get("normalized_code") or identification_result.get("code"))
    if identification_result.get("status") == "unknown":
        return build_unknown_enrichment(code, "代码识别结果为 unknown，不能编造补全信息。")
    enriched = enrich_asset(code, providers)
    if enriched["status"] == "unknown" and identification_result.get("status") == "pending_confirmation":
        return build_pending_enrichment(code, "仅有代码格式识别结果，缺少可查证补全来源。")
    return enriched


def merge_enrichment_results(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    records = [deepcopy(dict(result)) for result in results]
    if not records:
        return build_unknown_enrichment("", "没有可查证补全来源。")
    for record in records:
        validate_provider_result(record)
    code = normalize_code_input(records[0].get("code"))
    conflicts = detect_enrichment_conflicts(records)
    if conflicts:
        merged = build_conflict_enrichment(code, conflicts)
    else:
        merged = {"code": code, "status": "pending_confirmation", "confidence": "low", "needs_user_confirmation": True, "fields": _empty_fields("字段尚未由可查证来源补全。"), "sources": [], "conflicts": [], "usable_for_formal_analysis": False}
    merged["sources"] = _merge_sources(records)
    for field_name in SCALAR_FIELDS:
        values = [record["fields"][field_name] for record in records if isinstance(record.get("fields", {}).get(field_name), Mapping) and record["fields"][field_name].get("value") is not None]
        if values and not conflicts_for_field(conflicts, field_name):
            merged["fields"][field_name] = _merge_same_value_field(values)
    tags: list[dict[str, Any]] = []
    seen_tags: set[str] = set()
    for record in records:
        for tag in record.get("fields", {}).get("tags", []) or []:
            value = str(tag.get("value") or "").strip()
            if value and value not in seen_tags:
                tags.append(_field(value, tag.get("status", "unknown"), tag.get("confidence", "low"), tag.get("reason", "补全标签。"), tag.get("sources", [])))
                seen_tags.add(value)
    merged["fields"]["tags"] = tags
    if conflicts:
        for conflict in conflicts:
            merged["fields"][conflict["field"]] = _field(None, "conflict", "low", "多个补全来源给出不同值。", conflict.get("sources", []))
    elif any(_is_public_verified(record) for record in records):
        merged["status"] = "verified"
        merged["needs_user_confirmation"] = False
        merged["usable_for_formal_analysis"] = False
    else:
        merged["status"] = "pending_confirmation"
    merged["confidence"] = _max_confidence([field.get("confidence", "low") for field in _iter_fields(merged["fields"])])
    validate_enrichment_result(merged)
    return merged


def conflicts_for_field(conflicts: list[dict[str, Any]], field_name: str) -> bool:
    return any(conflict.get("field") == field_name for conflict in conflicts)


def detect_enrichment_conflicts(results: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    records = list(results)
    for field_name in SCALAR_FIELDS:
        by_value: dict[str, list[Mapping[str, Any]]] = {}
        for record in records:
            field = record.get("fields", {}).get(field_name)
            if isinstance(field, Mapping) and field.get("value") is not None:
                by_value.setdefault(str(field.get("value")), []).append(record)
        if len(by_value) > 1:
            conflicts.append({"field": field_name, "values": sorted(by_value), "providers": [record.get("provider_name") for record in records if isinstance(record.get("fields", {}).get(field_name), Mapping) and record["fields"][field_name].get("value") is not None], "sources": _merge_sources(records)})
    return conflicts


def _merge_same_value_field(fields: list[Mapping[str, Any]]) -> dict[str, Any]:
    first = fields[0]
    status = "verified" if any(field.get("status") == "verified" for field in fields) else first.get("status", "unknown")
    return _field(first.get("value"), status, _max_confidence([field.get("confidence", "low") for field in fields]), "; ".join(dict.fromkeys(str(field.get("reason") or "") for field in fields if field.get("reason"))), _merge_field_sources(fields))


def _max_confidence(values: Iterable[str]) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    return max((_confidence(value) for value in values), key=lambda item: order[item], default="low")


def _merge_sources(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for record in records:
        sources.extend(record.get("sources") or [])
        sources.extend(_merge_field_sources(_iter_fields(record.get("fields", {}))))
    return _dedupe_sources(sources)


def _merge_field_sources(fields: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for field in fields:
        sources.extend(field.get("sources") or [])
    return _dedupe_sources(sources)


def _dedupe_sources(sources: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for source in sources:
        key = json.dumps(source, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            output.append(dict(source))
            seen.add(key)
    return output


def _iter_fields(fields: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for value in fields.values():
        if isinstance(value, Mapping):
            yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    yield item


def _is_public_verified(record: Mapping[str, Any]) -> bool:
    if record.get("provider_type") not in {"official", "public_web", "market_data", "fund_data"}:
        return False
    return any(field.get("status") == "verified" for field in _iter_fields(record.get("fields", {})))


def validate_provider_result(result: Mapping[str, Any]) -> bool:
    if not str(result.get("provider_name") or "").strip():
        raise ValueError("provider_name is required.")
    provider_type = result.get("provider_type")
    if provider_type not in ALLOWED_PROVIDER_TYPES:
        raise ValueError("provider_type is invalid or missing.")
    if provider_type == "fixture" and provider_type in {"official", "public_web"}:
        raise ValueError("fixture provider cannot masquerade as public source.")
    fields = result.get("fields")
    if not isinstance(fields, Mapping):
        raise ValueError("fields must be an object.")
    for field_name, field_value in fields.items():
        items = field_value if isinstance(field_value, list) else [field_value]
        for item in items:
            if not isinstance(item, Mapping):
                raise ValueError(f"{field_name} must contain field objects.")
            if item.get("status") not in ALLOWED_FIELD_STATUSES:
                raise ValueError(f"{field_name} status is invalid.")
            if item.get("confidence") not in ALLOWED_CONFIDENCE:
                raise ValueError(f"{field_name} confidence is invalid.")
            if not str(item.get("reason") or "").strip():
                raise ValueError(f"{field_name} reason is required.")
            if item.get("status") == "verified" and not isinstance(item.get("sources"), list):
                raise ValueError(f"{field_name} verified field requires sources.")
    return True


def validate_enrichment_result(result: Mapping[str, Any]) -> bool:
    if result.get("status") not in {"verified", "unknown", "pending_confirmation", "conflict"}:
        raise ValueError("invalid enrichment status")
    if result.get("confidence") not in ALLOWED_CONFIDENCE:
        raise ValueError("invalid enrichment confidence")
    if not isinstance(result.get("needs_user_confirmation"), bool):
        raise ValueError("needs_user_confirmation must be bool")
    return True


def build_enriched_asset_draft(identification_result: Mapping[str, Any], enrichment_result: Mapping[str, Any]) -> dict[str, Any]:
    fields = enrichment_result.get("fields", {})
    asset_type = fields.get("type", {}).get("value") or identification_result.get("asset_type", {}).get("value") or "unknown"
    market = fields.get("market", {}).get("value") or identification_result.get("market", {}).get("value") or "unknown"
    source_status = normalize_source_status(enrichment_result.get("status", "unknown"))
    if source_status == "verified" and not enrichment_result.get("usable_for_formal_analysis"):
        source_status = "pending_confirmation"
    asset = {
        "asset_id": f"draft_{normalize_code_input(enrichment_result.get('code') or identification_result.get('code')) or 'unknown'}",
        "type": normalize_asset_type(asset_type),
        "code": normalize_code_input(enrichment_result.get("code") or identification_result.get("code")),
        "name": fields.get("name", {}).get("value") or "",
        "market": normalize_market(market),
        "tags": [tag["value"] for tag in fields.get("tags", []) if isinstance(tag, Mapping) and tag.get("value")],
        "status": "watching",
        "weight_level": 1,
        "source_status": source_status,
        "notes": None,
    }
    validate_asset(asset)
    return asset


def load_example_enrichment_records() -> list[dict[str, Any]]:
    data = json.loads(EXAMPLE_FIXTURE_PATH.read_text(encoding="utf-8"))
    return list(data.get("records") or [])


def example_enrichment_provider(code: str) -> dict[str, Any] | None:
    normalized = normalize_code_input(code)
    for record in load_example_enrichment_records():
        if normalize_code_input(record.get("code")) == normalized:
            source_type = record.get("source_type", "manual_user_input")
            confidence = _confidence(record.get("confidence", "medium"))
            reason = "来自 example fixture，仅用于测试，不代表真实公开数据。"
            fields = {
                "name": _field(record.get("name"), source_type, confidence, reason),
                "type": _field(record.get("type"), source_type, confidence, reason),
                "market": _field(record.get("market"), source_type, confidence, reason),
                "tags": [_field(tag, source_type, confidence, reason) for tag in record.get("tags", [])],
            }
            return {"provider_name": "example_verified_records", "provider_type": "fixture", "code": normalized, "fields": fields, "sources": []}
    return None


__all__ = [
    "enrich_asset", "enrich_identification_result", "merge_enrichment_results", "detect_enrichment_conflicts", "build_enriched_asset_draft", "validate_enrichment_result", "build_unknown_enrichment", "build_pending_enrichment", "build_conflict_enrichment", "load_example_enrichment_records", "validate_provider_result", "example_enrichment_provider",
]
