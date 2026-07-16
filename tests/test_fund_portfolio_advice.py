from decimal import Decimal
from types import SimpleNamespace

from src.fund_portfolio_advice import (
    PortfolioHoldingInput,
    analyze_fund_portfolio,
    run_akshare_fund_portfolio_advice,
    validate_advice_request,
)


def holding(code, amount, *, target=None, name="测试基金"):
    return PortfolioHoldingInput(code, name, Decimal(str(amount)), Decimal("0"), Decimal(str(target)) if target is not None else None)


def comparison(*, overlap_holdings="0", overlap_industries="0", status="available"):
    profile = SimpleNamespace(fund_type="混合型")
    fund = lambda code: SimpleNamespace(code=code, bundle=SimpleNamespace(profile=profile))
    pair = SimpleNamespace(
        left_code="000001", right_code="000002",
        disclosed_holdings_overlap_pct=overlap_holdings,
        disclosed_industry_overlap_pct=overlap_industries,
    )
    return SimpleNamespace(data_status=status, funds=[fund("000001"), fund("000002")], pair_overlaps=[pair])


def cycle(*, phase="expansion", productivity="stable", status="available"):
    link = SimpleNamespace(industry_name="软件开发", fund_weight_pct="60")
    funds = [SimpleNamespace(code="000001", industry_links=[link]), SimpleNamespace(code="000002", industry_links=[link])]
    industry = SimpleNamespace(industry_name="软件开发", phase=phase, confidence="0.85", productivity=SimpleNamespace(status=productivity))
    return SimpleNamespace(data_status=status, funds=funds, industries=[industry], missing_evidence=[])


def request(holdings):
    return {
        "mode": "fund-portfolio-advice-readonly", "provider": "akshare_fund_public",
        "holdings": holdings,
        "sections": ["portfolio-concentration", "overlap", "industry-cycle", "target-drift"],
        "humanApproved": True, "readOnly": True,
        "allowAccountRead": False, "allowTrading": False, "allowNotificationSend": False,
        "allowAiCall": False, "allowPersistence": False,
    }


def test_concentration_and_overlap_produce_explainable_review_prompts():
    result = analyze_fund_portfolio(
        (holding("000001", 70), holding("000002", 20), holding("000003", 10)),
        comparison(overlap_holdings="25", overlap_industries="40"),
        cycle(),
    )

    assert result.risk_level == "high"
    assert result.top_fund_weight_pct == "70"
    assert {item.category for item in result.findings} >= {"single-fund-concentration", "disclosed-overlap"}
    assert all(item.action_scope == "review-only-no-automatic-execution" for item in result.suggestions)


def test_cycle_headwind_uses_disclosed_weight_and_never_becomes_an_order():
    result = analyze_fund_portfolio(
        (holding("000001", 60), holding("000002", 40)),
        comparison(),
        cycle(phase="contraction", productivity="weakening"),
    )

    finding = next(item for item in result.findings if item.category == "industry-evidence-risk")
    assert "周期=contraction" in finding.evidence
    assert "买入" not in str(result.to_dict())
    assert "卖出" not in str(result.to_dict())


def test_missing_public_evidence_is_insufficient_not_low_risk():
    result = analyze_fund_portfolio(
        tuple(holding(f"00000{index}", 20) for index in range(1, 6)),
        None,
        None,
    )

    assert result.risk_level == "insufficient"
    assert "fund-comparison-and-industry-exposure" in result.missing_evidence
    assert "industry-cycle-and-productivity-evidence" in result.missing_evidence


def test_user_targets_are_used_only_when_plan_is_complete_enough():
    usable = analyze_fund_portfolio(
        (holding("000001", 70, target=50), holding("000002", 30, target=50)), comparison(), cycle()
    )
    incomplete = analyze_fund_portfolio(
        (holding("000001", 70, target=20), holding("000002", 30)), comparison(), cycle()
    )

    assert any(item.category == "target-drift" for item in usable.findings)
    assert "usable-target-allocation-plan" in incomplete.missing_evidence


def test_request_requires_local_manual_readonly_flags_and_valid_amounts():
    payload = request([{"code": "000001", "name": "基金A", "amount": 1000, "profit": 20, "targetAllocation": None}])
    assert validate_advice_request(payload)[0].amount == Decimal("1000")
    assert run_akshare_fund_portfolio_advice({**payload, "allowTrading": True})["errorCode"] == "fund-portfolio-advice.forbidden-capability"
    assert run_akshare_fund_portfolio_advice({**payload, "holdings": [{**payload["holdings"][0], "amount": -1}]})["errorCode"] == "fund-portfolio-advice.invalid-holdings"
