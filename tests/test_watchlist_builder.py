from src.watchlist_builder import build_watchlist, render_watchlist_markdown


def _trend(temp="升温", turnover="放量", rise="上升", status="available"):
    return {"5": {"status": status, "market_temperature": {"direction": temp}, "turnover": {"direction": turnover}, "rise_ratio": {"direction": rise}, "data_quality": {"average_coverage_percent": 90}}, "20": {"status": status}}


def _persistence():
    return {"5": {"status": "available", "industries": {"persistent_leaders": [{"name": "PCB"}], "short_term_breakouts": [{"name": "半导体"}], "pullback_risks": [{"name": "机器人"}], "persistent_laggers": [{"name": "地产"}]}, "concepts": {"persistent_leaders": [], "short_term_breakouts": [], "pullback_risks": [], "persistent_laggers": []}}}


def _all_text(data):
    parts = [data.get("summary", "")]
    for key in ("market_watch", "sector_watch", "risk_watch", "data_quality_watch", "next_period_watch", "pending_watch"):
        for item in data.get(key, []):
            parts.append(str(item))
    return "\n".join(parts)


def test_no_history_returns_insufficient_data():
    data = build_watchlist(trend=_trend(status="insufficient_data"))
    assert data["status"] == "insufficient_data"
    assert data["market_watch"] == []


def test_market_warming_generates_market_watch():
    data = build_watchlist(trend=_trend(temp="升温"))
    assert any("市场热度" in x["item"] for x in data["market_watch"])


def test_market_cooling_generates_market_watch():
    data = build_watchlist(trend=_trend(temp="降温", turnover="平稳", rise="震荡"))
    assert any("市场降温" in x["item"] for x in data["market_watch"])


def test_turnover_expansion_and_shrink_generate_watch():
    assert any("成交额是否继续放大" in x["item"] for x in build_watchlist(trend=_trend(turnover="放量"))["market_watch"])
    assert any("成交额缩量是否缓解" in x["item"] for x in build_watchlist(trend=_trend(turnover="缩量"))["market_watch"])


def test_sector_and_risk_watch_from_persistence():
    data = build_watchlist(trend=_trend(), persistence=_persistence())
    assert any("持续强势方向" in x["item"] for x in data["sector_watch"])
    assert any("短线爆发" in x["item"] for x in data["sector_watch"])
    assert any("冲高回落" in x["item"] for x in data["risk_watch"])
    assert any("持续走弱" in x["item"] for x in data["risk_watch"])


def test_data_quality_and_pending_watch():
    data = build_watchlist(trend={"5": _trend()["5"], "20": {"status": "insufficient_data"}}, data_quality={"average_coverage_percent": 55})
    assert any("数据覆盖率" in x["item"] for x in data["data_quality_watch"])
    assert any("暂不做长期趋势判断" in x for x in data["pending_watch"])


def test_items_include_reason_and_no_direct_trading_advice_or_sensitive_tokens():
    data = build_watchlist(trend=_trend(), persistence=_persistence(), risk_radar={"status": "available", "risks": [{"level": "高", "reason": "风险雷达识别", "observation": "观察风险变化"}]})
    for key in ("market_watch", "sector_watch", "risk_watch", "data_quality_watch"):
        for item in data[key]:
            assert item["item"]
            assert item["reason"]
            assert item["source"]
    text = _all_text(data)
    for word in ("买入", "卖出", "加仓", "减仓", "webhook", "Token", "10000元"):
        assert word not in text


def test_render_markdown_insufficient_data():
    text = render_watchlist_markdown({"status": "insufficient_data"}, title="## 今日观察清单")
    assert "历史样本不足" in text
