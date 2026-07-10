import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def payload():
    return json.loads(read("web/static/demo_final_page_payload.json"))


def test_web_p17_docs_exists_and_documents_safety_boundaries():
    doc_path = ROOT / "docs" / "web_account_home_dashboard.md"
    assert doc_path.exists()
    text = doc_path.read_text(encoding="utf-8")
    assert "# Web-P17 账户首页综合看板说明" in text
    assert "不请求原始行情字段" in text
    assert "不请求原始基金净值字段" in text
    assert "默认展示脱敏结果" in text
    assert "最终以基金公司公布净值为准" in text
    assert "实时涨跌" in text
    assert "不把场外基金称为实时涨跌" in text


def test_app_js_contains_dashboard_rendering_functions():
    script = read("web/static/app.js")
    for name in [
        "renderAccountHomeDashboard",
        "renderDashboardSummary",
        "renderDashboardMetricCards",
        "renderDashboardSafetyPanel",
        "renderDashboardQuickSections",
        "countDisplayModelsByStatus",
        "countObservationPoints",
        "buildDashboardSummaryFromPayload",
        "renderQuickLink",
        "renderEmptyDashboardState",
    ]:
        assert f"function {name}" in script
    assert "renderStockEtfCards" in script
    assert "renderFundNavCards" in script
    assert "renderObservationPoints" in script
    assert "renderObservationPointCards" in script


def test_index_html_contains_dashboard_containers_and_required_copy():
    html = read("web/static/index.html")
    for text in [
        "dashboard-summary",
        "dashboard-metrics",
        "dashboard-safety-panel",
        "dashboard-quick-stock-etf",
        "dashboard-quick-fund-nav",
        "dashboard-quick-observation-points",
        "dashboard-warnings",
        "账户首页综合看板",
        "股票 / ETF 行情",
        "场外基金净值",
        "个人观察点位",
        "风险提醒",
        "数据说明",
        "不执行交易操作",
        "不构成操作指令",
        "最终以基金公司公布净值为准",
    ]:
        assert text in html


def test_demo_payload_dashboard_summary_and_redacted_mode():
    data = payload()
    assert "dashboard_summary" in data
    assert "counts" in data["dashboard_summary"]
    assert data["display_mode"] == "redacted"
    assert data["can_write_to_public_repo"] is False
    assert "<redacted>" in json.dumps(data, ensure_ascii=False)


def test_demo_payload_does_not_contain_real_values_or_secrets():
    raw = read("web/static/demo_final_page_payload.json")
    forbidden = [
        "真实价格",
        "真实基金净值",
        "真实金额",
        "成本价",
        "Token",
        "API Key",
        "Webhook",
        "token",
        "api_key",
        "webhook",
        "场外基金实时涨跌",
        "基金实时价格",
        "实时净值",
    ]
    for word in forbidden:
        assert word not in raw


def test_p17_docs_are_linked_from_related_docs():
    combined = "\n".join(
        read(path)
        for path in [
            "docs/web_observation_points_cards.md",
            "docs/web_market_fund_dashboard.md",
            "docs/web_final_payload_rendering.md",
            "docs/web_page_routes_plan.md",
            "web/README.md",
            "docs/CHANGELOG.md",
        ]
    )
    assert "Web-P17" in combined
    assert "账户首页综合看板" in combined
