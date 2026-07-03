import logging

from src.data_quality import assess_data_quality, format_data_quality_block
from src.notification import format_discord_report_summary


def test_complete_mapping_has_high_coverage():
    quality = assess_data_quality({
        "report_date": "2026-07-03",
        "latest_data_date": "2026-07-03",
        "data_mode": "realtime",
        "market_status": "偏强",
        "market_score": 82,
        "rise_ratio": 62.5,
        "rising_count": 3200,
        "falling_count": 1800,
        "turnover": 10234,
        "limit_up_count": 80,
        "limit_down_count": 15,
        "limit_diff": 65,
        "indices": ["上证指数", "深证成指", "恒生指数", "纳斯达克", "标普500", "日经225", "韩国综合指数"],
        "leading_industries": ["半导体"],
        "lagging_industries": ["煤炭"],
        "leading_concepts": ["AI"],
        "lagging_concepts": ["ST"],
        "history_yesterday": {"rise_ratio": 55},
        "history_5d": [{"rise_ratio": 50}],
    })

    assert quality["coverage_percent"] >= 90
    assert quality["data_mode"] == "realtime"
    assert quality["latest_data_date"] == "2026-07-03"


def test_missing_fields_are_reported_for_empty_input():
    quality = assess_data_quality({})

    assert quality["coverage_percent"] == 0
    assert "rise_ratio" in quality["missing_fields"]
    assert quality["data_mode"] == "unknown"
    assert "数据质量偏低" in quality["human_summary"]


def test_partial_indices_are_marked_when_group_has_sparse_members():
    quality = assess_data_quality({"indices": ["纳斯达克"], "latest_data_date": "2026-07-03"})

    assert "us_indices" in quality["available_fields"]
    assert "us_indices" in quality["partial_fields"]


def test_text_input_extracts_core_fields_and_formats_block():
    quality = assess_data_quality("""
报告日期：2026-07-03
数据日期：2026-07-03
数据状态：实时
市场状态：偏强
盘面信号：82/100
上涨占比：62.5%
上涨股票：3200 家
下跌股票：1800 家
两市成交额：10234 亿
涨跌停差：+65
行业板块领涨 Top 5
1. 半导体：+3.2%
近 5 日盘面对比
昨日：上涨占比 55%
全球指数：上证指数、恒生指数、纳斯达克、日经225、韩国综合指数
""")

    assert quality["coverage_percent"] > 40
    block = format_data_quality_block(quality)
    assert "数据覆盖率" in block
    assert "2026-07-03" in block
    assert "实时" in block


def test_discord_summary_shows_data_quality_line():
    content = """
# 大盘复盘
报告日期：2026-07-03
数据日期：2026-07-03
数据状态：实时
今日结论：市场偏强。
盘面信号：82/100
上涨占比：62.5%
涨跌停差：+65
两市成交额：10234 亿
"""

    summary = format_discord_report_summary(content)

    assert "数据质量" in summary
    assert "数据覆盖率" in summary
    assert "数据日期：2026-07-03" in summary


def test_data_quality_logs_do_not_emit_webhook_url(caplog):
    caplog.set_level(logging.INFO)
    assess_data_quality({
        "discord_webhook_url": "https://discord.com/api/webhooks/secret-token",
        "rise_ratio": 50,
    })

    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "discord.com/api/webhooks" not in logs
    assert "secret-token" not in logs


def test_core_a_share_mapping_aliases_are_recognized():
    quality = assess_data_quality({
        "date": "2026-07-03",
        "breadth": {
            "rise_ratio": 0.58,
            "rising_count": 3100,
            "falling_count": 1900,
            "flat_count": 120,
            "turnover": 10888,
            "limit_up_count": 72,
            "limit_down_count": 18,
            "limit_diff": 54,
        },
        "indices": [{"name": "上证指数"}, {"name": "深证成指"}, {"name": "创业板指"}],
        "sectors": {
            "top": [{"name": "半导体", "change_pct": 3.2}],
            "bottom": [{"name": "煤炭", "change_pct": -1.1}],
        },
    })

    for field in ("rise_ratio", "rising_count", "falling_count", "flat_count", "turnover", "limit_diff"):
        assert field in quality["available_fields"]
    assert "a_share_indices" in quality["available_fields"]
    assert "leading_industries" in quality["available_fields"]
    assert "lagging_industries" in quality["available_fields"]


def test_discord_summary_extracts_core_signal_table_values():
    content = """
# 📈 AI股票基金每日盯盘报告
报告日期：2026-07-03
数据日期：2026-07-03
数据状态：实时
今日结论：结构化数据可用，市场偏强。
- **盘面信号**：68/100（偏暖，可进攻）
- **上涨占比**：62.0%
- **上涨/下跌**：3100 家 / 1900 家
- **两市成交额**：10888 亿
- **涨跌停差**：+54
"""

    summary = format_discord_report_summary(content)

    assert "• 上涨占比：62.0%" in summary
    assert "• 上涨/下跌：3100 家 / 1900 家" in summary
    assert "• 两市成交额：10888 亿" in summary
    assert "• 涨跌停差：+54" in summary
    assert "• 盘面信号：68/100" in summary


def test_global_indices_partial_when_one_market_missing():
    quality = assess_data_quality({
        "indices": [
            {"name": "上证指数"},
            {"name": "恒生指数"},
            {"name": "纳斯达克综合指数"},
            {"name": "标普500"},
            {"name": "道琼斯工业指数"},
            {"name": "日经225"},
        ],
        "latest_data_date": "2026-07-03",
    })

    assert "global_indices" in quality["available_fields"]
    assert "global_indices" in quality["partial_fields"]


def test_global_indices_ok_when_all_markets_present():
    quality = assess_data_quality({
        "indices": [
            {"name": "上证指数"},
            {"name": "深证成指"},
            {"name": "恒生指数"},
            {"name": "恒生科技指数"},
            {"name": "纳斯达克综合指数"},
            {"name": "标普500"},
            {"name": "道琼斯工业指数"},
            {"name": "日经225"},
            {"name": "KOSPI"},
        ],
    })

    assert "global_indices" in quality["available_fields"]
    assert "global_indices" not in quality["partial_fields"]
