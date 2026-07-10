import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "static" / "app.js"
INDEX_HTML = ROOT / "web" / "static" / "index.html"
PAYLOAD = ROOT / "web" / "static" / "demo_final_page_payload.json"
DOC = ROOT / "docs" / "web_market_fund_dashboard.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_web_p15_doc_exists_and_records_safety_boundaries():
    text = read(DOC)
    assert "# Web-P15 行情与基金净值看板说明" in text
    assert "不请求原始行情字段" in text
    assert "不请求原始基金净值字段" in text
    assert "blocked` 状态不显示真实值" in text
    assert "最终以基金公司公布净值为准" in text
    assert "场外基金不能写场外基金实时涨跌" in text


def test_app_js_exposes_market_dashboard_render_helpers():
    text = read(APP_JS)
    for name in [
        "renderMarketDashboard",
        "renderStockEtfCards",
        "renderFundNavCards",
        "renderAssetBadges",
        "renderBlockedCard",
        "renderUnavailableCard",
        "renderDataStatusBadge",
        "renderRedactedValue",
        "formatDisplayValue",
        "escapeHtml",
    ]:
        assert f"function {name}" in text


def test_index_html_contains_dashboard_titles_and_required_disclaimer():
    text = read(INDEX_HTML)
    assert "股票 / ETF 行情" in text
    assert "场外基金净值" in text
    assert "不执行交易操作" in text
    assert "不构成操作指令" in text


def test_demo_payload_contains_safe_market_sections_and_states():
    payload = json.loads(read(PAYLOAD))
    assert payload["can_write_to_public_repo"] is False
    assert "stock_etf" in payload["sections"]
    assert "fund_nav" in payload["sections"]
    stock_models = payload["sections"]["stock_etf"]["display_models"]
    fund_models = payload["sections"]["fund_nav"]["display_models"]
    assert len(stock_models) >= 1
    assert len(fund_models) >= 1
    assert any(model["type"] == "stock" for model in stock_models)
    assert any(model["type"] == "ETF" for model in stock_models)
    assert any(model["display_mode"] == "redacted" for model in stock_models + fund_models)
    assert any(model["display_status"] == "blocked" for model in fund_models)
    assert "<redacted>" in read(PAYLOAD)


def test_demo_payload_does_not_contain_real_sensitive_values():
    text = read(PAYLOAD).lower()
    forbidden = [
        "成本价",
        "cost_basis",
        "token",
        "api key",
        "apikey",
        "api_key",
        "webhook",
        "贵州茅台",
        "腾讯",
        "招商银行",
        "天弘余额宝",
        "1.234",
        "10000",
        "amount",
        "asset_value",
    ]
    for word in forbidden:
        assert word not in text
