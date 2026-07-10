import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATIC_FILES = [
    "web/static/index.html",
    "web/static/styles.css",
    "web/static/app.js",
    "web/static/demo_final_page_payload.json",
    "docs/web_minimal_page_skeleton.md",
]
FORBIDDEN_PAYLOAD_TERMS = [
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


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_web_p1_static_files_exist():
    for path in STATIC_FILES:
        assert (ROOT / path).is_file(), path


def test_index_contains_required_layout_and_safety_text():
    html = _read("web/static/index.html")
    for text in [
        "AI 股票基金工作台",
        "首页",
        "指数",
        "持仓",
        "观察",
        "个人点位",
        "清理中心",
        "设置",
        "账户概览",
        "股票 / ETF 行情",
        "场外基金净值",
        "个人观察点位",
        "风险提醒",
        "数据说明",
        "不自动下单",
        "不构成强制交易指令",
        "final_page_payload",
    ]:
        assert text in html


def test_demo_payload_is_redacted_and_public_safe():
    payload = json.loads(_read("web/static/demo_final_page_payload.json"))
    assert payload["display_mode"] == "redacted"
    assert payload["can_write_to_public_repo"] is False
    assert payload["data_mode"] == "dry_run"
    assert payload["payload_status"] == "safe_for_account_page"


def test_demo_payload_does_not_contain_real_values_or_secrets():
    raw = _read("web/static/demo_final_page_payload.json")
    for text in FORBIDDEN_PAYLOAD_TERMS:
        assert text not in raw
    payload = json.loads(raw)
    assert payload["sections"]["stock_etf"]["display_models"]
    assert payload["sections"]["fund_nav"]["display_models"]
    assert "<redacted>" in raw


def test_demo_payload_contains_personal_observation_labels():
    payload = json.loads(_read("web/static/demo_final_page_payload.json"))
    labels = {
        item["label"]
        for item in payload["sections"]["observation_points"]["items"]
    }
    assert {"买入观察", "加仓观察", "止盈观察", "风险位"}.issubset(labels)


def test_docs_document_final_payload_and_safety_boundary():
    doc = _read("docs/web_minimal_page_skeleton.md")
    for text in [
        "只消费 `final_page_payload`",
        "不请求原始行情字段",
        "不请求原始基金净值字段",
        "不保存 Token / API Key / Webhook",
        "不自动下单",
        "不构成强制交易指令",
        "买入观察",
        "加仓观察",
        "止盈观察",
        "风险位",
    ]:
        assert text in doc


def test_app_js_uses_local_demo_payload_and_fallback_only():
    script = _read("web/static/app.js")
    assert 'fetch("demo_final_page_payload.json")' in script
    assert "fallbackPayload" in script
    for forbidden in ["cn_quote", "fund_nav_real_provider", "user_config", "localStorage", "sessionStorage"]:
        assert forbidden not in script
