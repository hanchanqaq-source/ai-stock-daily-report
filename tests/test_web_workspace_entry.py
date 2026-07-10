from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "web/README.md",
    "web/ENTRY.md",
    "web/AGENTS.md",
    "docs/web_workspace_entry.md",
    "docs/web_page_routes_plan.md",
    "docs/web_data_flow.md",
]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _combined_docs() -> str:
    return "\n".join(_read(path) for path in REQUIRED_FILES)


def test_web_workspace_entry_files_exist():
    for path in REQUIRED_FILES:
        assert (ROOT / path).is_file(), path


def test_web_workspace_safe_data_contract_is_documented():
    docs = _combined_docs()
    assert "final_page_payload" in docs
    assert "不直接请求真实行情" in docs or "must not directly request real market quotes" in docs
    assert "不直接请求真实基金净值" in docs or "must not directly request real fund NAV values" in docs
    assert "Token / API Key / Webhook" in docs
    assert "真实金额 / 成本价 / 账户资产" in docs


def test_personal_observation_and_disclaimer_are_documented():
    docs = _combined_docs()
    for label in ["买入观察", "加仓观察", "减仓观察", "止盈观察", "止损观察", "清仓观察", "低吸区", "目标区", "风险位", "等待回调", "继续持有", "暂不操作"]:
        assert label in docs
    assert "仅作为个人观察和记录，需用户自行判断。" in docs


def test_route_plan_contains_required_pages():
    plan = _read("docs/web_page_routes_plan.md")
    for route in ["dashboard", "indices", "holdings", "watchlist", "observation-points", "cleanup", "settings"]:
        assert route in plan


def test_docs_do_not_include_real_values_or_secret_examples():
    docs = _combined_docs()
    forbidden_examples = [
        "123456",
        "1.2345",
        "10000",
        "sk-",
        "ghp_",
        "xoxb-",
        "discord.com/api/webhooks/",
        "成本价：",
        "账户资产：",
        "真实价格：",
        "真实基金净值：",
    ]
    for text in forbidden_examples:
        assert text not in docs
