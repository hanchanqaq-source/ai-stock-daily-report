from copy import deepcopy

from src.holding_watch_compare import (
    build_holding_watch_comparison,
    collect_asset_tags,
    compare_tag_sets,
    count_assets_by_status,
    render_holding_watch_comparison_markdown,
    split_holding_and_watching_assets,
)


def asset(asset_id, status, tags):
    return {
        "asset_id": asset_id,
        "type": "fund",
        "code": "000000",
        "name": f"示例{asset_id}",
        "market": "CN",
        "tags": tags,
        "status": status,
        "weight_level": 3,
        "source_status": "manual_user_input",
    }


def group(assets):
    return {
        "account_id": "demo_mixed_group",
        "account_name": "示例基金股票混合组",
        "enabled": True,
        "risk_profile": "balanced",
        "description": "demo only",
        "assets": assets,
    }


def mixed_group():
    return group([
        asset("h1", "holding", ["PCB", "AI硬件"]),
        asset("h2", "holding", ["PCB", "半导体"]),
        asset("w1", "watching", ["机器人", "AI硬件"]),
        asset("w2", "watching", ["存储芯片"]),
        asset("c1", "cleared", ["清仓标签"]),
        asset("a1", "archived", ["归档标签"]),
        asset("d1", "deleted", ["删除标签"]),
    ])


def test_split_holding_and_watching_ignores_inactive_statuses():
    split = split_holding_and_watching_assets(mixed_group())
    assert [item["asset_id"] for item in split["holding"]] == ["h1", "h2"]
    assert [item["asset_id"] for item in split["watching"]] == ["w1", "w2"]


def test_count_assets_by_status_includes_cleared_archived_deleted_counts():
    counts = count_assets_by_status(mixed_group())
    assert counts["holding"] == 2
    assert counts["watching"] == 2
    assert counts["cleared"] == 1
    assert counts["archived"] == 1
    assert counts["deleted"] == 1


def test_collect_asset_tags_counts_holding_and_watching_tags():
    split = split_holding_and_watching_assets(mixed_group())
    holding_tags = collect_asset_tags(split["holding"])
    watching_tags = collect_asset_tags(split["watching"])
    assert holding_tags[0] == {"tag": "PCB", "count": 2, "asset_ids": ["h1", "h2"]}
    assert {item["tag"] for item in watching_tags} == {"机器人", "AI硬件", "存储芯片"}


def test_compare_tag_sets_finds_common_and_one_side_tags():
    split = split_holding_and_watching_assets(mixed_group())
    comparison = compare_tag_sets(collect_asset_tags(split["holding"]), collect_asset_tags(split["watching"]))
    assert comparison["common_tags"] == ["AI硬件"]
    assert comparison["holding_only_tags"] == ["PCB", "半导体"]
    assert comparison["watching_only_tags"] == ["存储芯片", "机器人"]


def test_build_comparison_excludes_cleared_archived_deleted_from_tags():
    result = build_holding_watch_comparison(mixed_group())
    assert result["status"] == "available"
    all_compare_tags = set(result["comparison"]["common_tags"] + result["comparison"]["holding_only_tags"] + result["comparison"]["watching_only_tags"])
    assert "清仓标签" not in all_compare_tags
    assert "归档标签" not in all_compare_tags
    assert "删除标签" not in all_compare_tags
    assert result["asset_counts"]["cleared"] == 1


def test_only_holding_returns_readable_warning():
    result = build_holding_watch_comparison(group([asset("h1", "holding", ["PCB"])]))
    assert result["status"] == "insufficient_data"
    assert "当前没有收藏资产可对比。" in result["data_warnings"]


def test_only_watching_returns_readable_warning():
    result = build_holding_watch_comparison(group([asset("w1", "watching", ["机器人"])]))
    assert result["status"] == "insufficient_data"
    assert "当前没有持有资产可对比。" in result["data_warnings"]


def test_empty_when_holding_and_watching_are_absent():
    result = build_holding_watch_comparison(group([asset("c1", "cleared", ["历史"])]))
    assert result["status"] == "empty"
    assert result["asset_counts"]["cleared"] == 1


def test_input_group_is_not_modified():
    source = mixed_group()
    original = deepcopy(source)
    build_holding_watch_comparison(source, market_context={"hot_tags": ["机器人"], "risk_tags": ["PCB"]})
    assert source == original


def test_market_context_uses_existing_signals_without_inventing_data():
    result = build_holding_watch_comparison(mixed_group(), market_context={"hot_tags": ["机器人"], "risk_tags": ["PCB"]})
    assert result["comparison"]["watching_hotter_than_holding"] is True
    assert result["comparison"]["holding_risk_higher_than_watching"] is True
    assert result["holding"]["risk_signals"] == ["PCB"]


def test_markdown_demo_is_generated_without_forbidden_trading_or_private_terms():
    markdown = render_holding_watch_comparison_markdown(build_holding_watch_comparison(mixed_group()))
    assert markdown.startswith("# 持有 vs 收藏对比 Demo")
    assert "## 4. 差异观察" in markdown
    forbidden = [
        "买入",
        "卖出",
        "加仓",
        "减仓",
        "金额",
        "成本价",
        "账户资产",
        "Webhook",
        "webhook",
        "Token",
        "token",
        "API Key",
        "api_key",
    ]
    for word in forbidden:
        assert word not in markdown


def test_structured_output_excludes_private_money_and_secret_fields():
    result = build_holding_watch_comparison(mixed_group())
    text = str(result)
    for word in ["amount", "cost_price", "account_value", "webhook", "token", "api_key", "成本价", "账户资产"]:
        assert word not in text
