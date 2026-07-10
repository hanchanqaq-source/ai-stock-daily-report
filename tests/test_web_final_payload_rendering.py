import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _payload() -> dict:
    return json.loads(_read("web/static/demo_final_page_payload.json"))


def test_web_p2_static_rendering_files_exist():
    for path in [
        "web/static/index.html",
        "web/static/styles.css",
        "web/static/app.js",
        "web/static/demo_final_page_payload.json",
        "docs/web_final_payload_rendering.md",
    ]:
        assert (ROOT / path).is_file(), path


def test_app_js_exposes_final_payload_rendering_functions():
    script = _read("web/static/app.js")
    for name in [
        "loadFinalPagePayload",
        "getFallbackPayload",
        "renderFinalPagePayload",
        "renderAccountHeader",
        "renderSafetyBadges",
        "renderStockEtfSection",
        "renderFundNavSection",
        "renderObservationPoints",
        "renderWarnings",
        "renderDisclaimer",
        "renderBlockedPayload",
        "escapeHtml",
    ]:
        assert f"function {name}" in script or f"async function {name}" in script
    assert 'fetch("demo_final_page_payload.json")' in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_index_contains_web_p2_rendering_containers():
    html = _read("web/static/index.html")
    for container_id in [
        "account-name",
        "payload-status",
        "display-mode",
        "safety-badges",
        "stock-etf-section",
        "fund-nav-section",
        "observation-points-section",
        "warnings-section",
        "disclaimer-section",
        "blocked-banner",
    ]:
        assert f'id="{container_id}"' in html


def test_demo_payload_has_safe_redacted_sections():
    payload = _payload()
    assert payload["payload_status"] == "safe_for_account_page"
    assert payload["display_mode"] == "redacted"
    assert payload["can_write_to_public_repo"] is False
    assert "stock_etf" in payload["sections"]
    assert "fund_nav" in payload["sections"]
    assert "observation_points" in payload["sections"]
    assert payload["sections"]["stock_etf"]["enabled"] is True
    assert payload["sections"]["fund_nav"]["enabled"] is True
    assert payload["sections"]["observation_points"]["enabled"] is True
    assert payload["sections"]["stock_etf"]["display_models"]
    assert payload["sections"]["fund_nav"]["display_models"]


def test_demo_payload_does_not_store_real_values_or_secrets():
    raw = _read("web/static/demo_final_page_payload.json")
    forbidden = [
        "真实价格",
        "真实基金净值",
        "真实金额",
        "成本价",
        "Token",
        "API Key",
        "Webhook",
        "sk-",
        "ghp_",
        "xoxb-",
        "discord.com/api/webhooks/",
    ]
    for text in forbidden:
        assert text not in raw
    assert "<redacted>" in raw
    assert "demo-date" in raw
    assert "demo-time" in raw


def test_demo_payload_contains_personal_observation_labels_and_fund_note():
    payload = _payload()
    labels = {item["label"] for item in payload["sections"]["observation_points"]["items"]}
    assert {"买入观察", "加仓观察", "止盈观察", "风险位"}.issubset(labels)
    assert any("最终以基金公司公布净值为准" in warning for warning in payload["warnings"])
    assert any("需用户自行判断" in warning for warning in payload["warnings"])


def test_docs_explain_final_payload_rendering_and_safety_boundary():
    doc = _read("docs/web_final_payload_rendering.md")
    for text in [
        "只消费 `final_page_payload`",
        "不请求原始行情字段",
        "不请求原始基金净值字段",
        "blocked 状态下也不得展示上游 raw value",
        "最终以基金公司公布净值为准",
        "买入观察",
        "加仓观察",
        "清仓观察",
        "自动" + "下" + "单",
    ]:
        assert text in doc


def test_existing_web_docs_reference_web_p2_flow():
    combined = "\n".join(
        _read(path)
        for path in [
            "docs/web_data_flow.md",
            "docs/web_minimal_page_skeleton.md",
            "web/README.md",
            "web/ENTRY.md",
        ]
    )
    assert "P5-T final_page_payload" in combined
    assert "web/static/demo_final_page_payload.json" in combined
    assert "web/static/app.js 渲染" in combined
    assert "stock_etf" in combined
    assert "fund_nav" in combined
    assert "observation_points" in combined
