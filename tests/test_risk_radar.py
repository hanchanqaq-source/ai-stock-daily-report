from src.risk_radar import build_risk_radar
from src.report_sections import render_risk_radar_section


def _trend_available():
    return {
        "5": {
            "status": "available",
            "data_points": 5,
            "market_temperature": {"direction": "降温"},
            "rise_ratio": {"latest": 35, "average": 52, "direction": "下降"},
            "turnover": {"latest": 9800, "average": 12300, "direction": "缩量"},
            "limit_diff": {"latest": -20, "average": 10, "direction": "走弱"},
            "market_score": {"latest": 45, "average": 60, "direction": "走弱"},
        },
        "20": {"status": "available", "data_points": 20},
    }


def _persistence():
    return {
        "5": {
            "status": "available",
            "industries": {
                "pullback_risks": [{"name": "有色金属"}],
                "persistent_laggers": [{"name": "机器人"}],
            },
            "concepts": {
                "pullback_risks": [{"name": "算力"}],
                "persistent_laggers": [],
            },
        }
    }


def test_no_history_returns_insufficient_data():
    radar = build_risk_radar(trend={}, persistence={}, data_quality={}, history_count=0)
    assert radar["status"] == "insufficient_data"
    assert radar["overall_risk_level"] == "数据不足"
    assert all(r["reason"] for r in radar["risks"])


def test_low_data_quality_identifies_quality_risk():
    radar = build_risk_radar(
        trend=_trend_available(),
        data_quality={"coverage_percent": 60, "missing_fields": ["turnover"], "partial_fields": [], "data_mode": "normal"},
    )
    risk = next(r for r in radar["risks"] if r["risk_type"] == "数据质量风险")
    assert risk["level"] == "中"
    assert risk["reason"]
    assert risk["observation"]


def test_market_cooling_turnover_limit_score_and_sector_risks():
    radar = build_risk_radar(trend=_trend_available(), persistence=_persistence(), data_quality={"coverage_percent": 90}, history_count=5)
    types = {r["risk_type"] for r in radar["risks"]}
    assert "市场降温风险" in types
    assert "成交额缩量风险" in types
    assert "涨跌停差恶化风险" in types
    assert "市场评分走弱风险" in types
    assert "板块 / 概念冲高回落风险" in types
    assert "板块 / 概念持续走弱风险" in types
    assert radar["overall_risk_level"] == "高"
    assert all(r["reason"] and r["observation"] for r in radar["risks"])


def test_history_fallback_and_20d_sample_warning():
    trend = _trend_available()
    trend["20"] = {"status": "insufficient_data", "data_points": 8}
    radar = build_risk_radar(latest_snapshot={"data_mode": "history_fallback", "date": "2026-07-03"}, trend=trend, data_quality={"coverage_percent": 90})
    assert any(r["risk_type"] == "非交易日 / 历史兜底数据风险" for r in radar["risks"])
    assert radar["data_warnings"]


def test_radar_text_has_no_direct_trading_advice_or_secrets():
    radar = build_risk_radar(trend=_trend_available(), persistence=_persistence(), data_quality={"coverage_percent": 90})
    text = render_risk_radar_section(radar)
    forbidden = ["买入", "卖出", "加仓", "减仓", "webhook", "Token", "用户金额"]
    assert not any(word in text for word in forbidden)
