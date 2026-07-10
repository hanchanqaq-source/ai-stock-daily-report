import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "static" / "app.js"
INDEX_HTML = ROOT / "web" / "static" / "index.html"
PAYLOAD = ROOT / "web" / "static" / "demo_final_page_payload.json"
DOC = ROOT / "docs" / "web_observation_points_cards.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def payload() -> dict:
    return json.loads(read(PAYLOAD))


def test_doc_exists_and_records_contract():
    assert DOC.is_file()
    text = read(DOC)
    for word in ["买入观察", "加仓观察", "减仓观察", "止盈观察", "止损观察", "清仓观察", "低吸区", "目标区", "风险位", "等待回调", "继续持有", "暂不操作"]:
        assert word in text
    for word in ["必" + "须" + "买" + "入", "必" + "须" + "卖" + "出", "立即满仓", "稳赚", "保" + "证" + "收" + "益", "无风险", "自动" + "下" + "单", "系统替你操作"]:
        assert word in text
    assert "观察点位默认脱敏" in text
    assert "仅作为个人观察和记录，需用户自行判断。" in text


def test_app_js_exposes_observation_render_helpers():
    script = read(APP_JS)
    for name in [
        "renderObservationPoints",
        "renderObservationPointCards",
        "renderObservationPointCard",
        "renderObservationCategoryBadge",
        "renderObservationRiskBadge",
        "renderObservationStatusBadge",
        "normalizeObservationLabel",
        "isAllowedObservationLabel",
        "isForbiddenTradingExpression",
        "renderObservationEmptyState",
        "escapeHtml",
    ]:
        assert f"function {name}" in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_demo_payload_contains_required_observation_points():
    data = payload()
    section = data["sections"]["observation_points"]
    assert section["enabled"] is True
    items = section["items"]
    assert len(items) >= 4
    labels = {item["label"] for item in items}
    assert {"买入观察", "加仓观察", "止盈观察", "风险位"}.issubset(labels)
    for item in items:
        assert item.get("label")
        assert item.get("text")
        assert item.get("disclaimer")
        assert item.get("point_display") == "<redacted>"
        assert "price" not in item
        assert "amount" not in item
        assert "cost_basis" not in item


def test_demo_payload_excludes_sensitive_or_forbidden_text():
    raw = read(PAYLOAD)
    forbidden = [
        "Token", "token", "API Key", "api_key", "Webhook", "webhook",
        "必" + "须" + "买" + "入", "必" + "须" + "卖" + "出", "立即满仓", "稳赚", "保" + "证" + "收" + "益", "无风险", "系统替你操作",
        "成本价", "真实金额", "账户资产", "10000", "1.234",
    ]
    for word in forbidden:
        assert word not in raw


def test_index_html_contains_observation_title_and_disclaimer():
    html = read(INDEX_HTML)
    assert "个人观察点位" in html
    assert "仅作为个人观察和记录，需用户自行判断。" in html
