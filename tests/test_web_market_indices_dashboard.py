import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "static" / "app.js"
INDEX_HTML = ROOT / "web" / "static" / "index.html"
PAYLOAD = ROOT / "web" / "static" / "demo_final_page_payload.json"
DOC = ROOT / "docs" / "web_market_indices_dashboard.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def payload() -> dict:
    return json.loads(read(PAYLOAD))


def test_web_p18_doc_exists_and_documents_tabs_and_indicator_types():
    assert DOC.exists()
    text = read(DOC)
    assert "Web-P18" in text
    for label in ["全球总览", "A股", "港股", "美股", "韩股"]:
        assert label in text
    assert "官方指数" in text
    assert "系统计算指标" in text
    assert "非官方指数" in text


def test_index_html_contains_market_indices_containers_and_copy():
    text = read(INDEX_HTML)
    for expected in [
        "market-indices-section",
        "market-indices-tabs",
        "market-index-overview",
        "market-index-cn",
        "market-index-hk",
        "market-index-us",
        "market-index-kr",
        "market-index-detail",
        "market-index-disclaimer",
        "全球市场指数",
    ]:
        assert expected in text


def test_app_js_contains_market_indices_render_helpers():
    text = read(APP_JS)
    for name in [
        "renderMarketIndicesDashboard",
        "renderMarketIndexTabs",
        "renderMarketIndexPanel",
        "renderMarketIndexGroup",
        "renderMarketIndexItem",
        "setActiveMarketIndexTab",
        "getMarketIndicesFromPayload",
        "buildFallbackMarketIndices",
        "normalizeMarketIndexLabel",
        "renderIndicatorTypeBadge",
    ]:
        assert f"function {name}" in text
    assert "fetch(\"demo_final_page_payload.json\")" in text
    assert "akshare" not in text.lower()
    assert "yfinance" not in text.lower()
    assert "eastmoney" not in text.lower()


def test_demo_payload_contains_safe_market_indices_contract():
    data = payload()
    market_indices = data["market_indices"]
    assert market_indices["data_mode"] == "dry_run"
    assert market_indices["display_mode"] == "redacted"
    assert market_indices["source_status"] == "demo_only"
    assert market_indices["can_write_to_public_repo"] is False
    for key in ["global", "cn", "hk", "us", "kr"]:
        assert key in market_indices["markets"]


def test_demo_payload_contains_required_market_groups():
    markets = payload()["market_indices"]["markets"]
    cn_labels = {group["group_label"] for group in markets["cn"]["groups"]}
    assert {"权重核心", "中小盘", "成长科技", "市场体感"}.issubset(cn_labels)
    us_labels = {group["group_label"] for group in markets["us"]["groups"]}
    assert "市场广度 / 体感" in us_labels
    global_labels = {group["group_label"] for group in markets["global"]["groups"]}
    assert {"A股摘要", "港股摘要", "美股摘要", "韩股摘要", "全球风险提示", "数据说明"}.issubset(global_labels)


def test_system_computed_indicators_carry_indicator_type_and_note():
    markets = payload()["market_indices"]["markets"]
    computed_items = []
    for market in markets.values():
        for group in market.get("groups", []):
            for item in group.get("items", []):
                if item.get("indicator_type", "").startswith("computed"):
                    computed_items.append(item)
    assert computed_items
    for item in computed_items:
        assert item["indicator_type"] in {"computed_breadth_indicator", "computed_sentiment_indicator"}
        assert "非官方指数" in item["note"]


def test_demo_payload_contains_no_real_values_or_secrets_for_indices():
    market_indices_text = json.dumps(payload()["market_indices"], ensure_ascii=False).lower()
    forbidden = [
        "token",
        "api key",
        "apikey",
        "api_key",
        "webhook",
        "cost_basis",
        "asset_value",
        "amount",
        "真实账户金额",
        "贵州茅台",
        "腾讯",
        "招商银行",
        "1.234",
        "10000",
        "+1%",
        "-1%",
    ]
    for word in forbidden:
        assert word not in market_indices_text
    assert "<redacted>" in market_indices_text


def test_related_docs_and_changelog_link_web_p18():
    combined = "\n".join(
        read(ROOT / path)
        for path in [
            "docs/web_page_routes_plan.md",
            "docs/web_account_home_dashboard.md",
            "docs/web_final_payload_rendering.md",
            "web/README.md",
            "docs/CHANGELOG.md",
        ]
    )
    assert "Web-P18" in combined
    assert "全球市场指数" in combined
    assert "不请求真实行情" in combined
