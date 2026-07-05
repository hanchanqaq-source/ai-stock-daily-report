from src.realtime_quote_provider import (
    FixtureQuoteProvider,
    MockQuoteProvider,
    QuoteRequest,
    QuoteResult,
    fetch_realtime_quotes,
)


def test_stock_etf_and_official_index_are_supported_fixture_only():
    provider = FixtureQuoteProvider()
    requests = [
        QuoteRequest(symbol="000001", asset_type="stock", market="CN"),
        QuoteRequest(symbol="510300", asset_type="etf", market="CN"),
        QuoteRequest(symbol="cn_sse_composite", asset_type="index", market="CN", item_type="official_index"),
    ]

    results = provider.fetch_quotes(requests)

    assert [result.success for result in results] == [True, True, True]
    assert [result.asset_type for result in results] == ["stock", "etf", "official_index"]
    for result in results:
        assert isinstance(result, QuoteResult)
        assert result.provider == "fixture_quote_provider"
        assert result.source_status == "fixture_only"
        assert result.fixture_only is True
        assert result.checked_at
        assert "不抓取" in result.disclaimer
        assert result.price is None
        assert result.change_pct is None
        assert result.turnover is None


def test_fund_is_unsupported_and_points_to_nav_module():
    result = FixtureQuoteProvider().fetch_quote(QuoteRequest(symbol="000001", asset_type="fund", market="CN"))

    assert result.success is False
    assert result.source_status == "unsupported"
    assert "NAV" in result.message
    assert "净值" in result.message


def test_computed_indicator_is_not_directly_quoted():
    result = FixtureQuoteProvider().fetch_quote(
        QuoteRequest(symbol="cn_median_change_pct", asset_type="index", market="CN", item_type="computed_indicator")
    )

    assert result.success is False
    assert result.asset_type == "computed_indicator"
    assert result.source_status == "unsupported"
    assert "不能直接抓取 quote" in result.message


def test_batch_fetch_preserves_partial_success_and_failure_statuses():
    provider = FixtureQuoteProvider({"BAD": "provider_error", "INVALID": "invalid_request"})
    results = fetch_realtime_quotes(
        [
            QuoteRequest(symbol="AAPL", asset_type="stock", market="US", request_id="ok"),
            QuoteRequest(symbol="BAD", asset_type="stock", market="US", request_id="bad"),
            QuoteRequest(symbol="INVALID", asset_type="stock", market="US", request_id="invalid"),
            QuoteRequest(symbol="FUND", asset_type="fund", market="CN", request_id="fund"),
        ],
        provider=provider,
    )

    assert [(result.request_id, result.success, result.source_status) for result in results] == [
        ("ok", True, "fixture_only"),
        ("bad", False, "provider_error"),
        ("invalid", False, "invalid_request"),
        ("fund", False, "unsupported"),
    ]


def test_mock_provider_default_batch_fetch_is_fixture_only():
    results = fetch_realtime_quotes([QuoteRequest(symbol="0700", asset_type="stock", market="HK")])

    assert len(results) == 1
    assert results[0].provider == MockQuoteProvider.provider_name
    assert results[0].source_status == "fixture_only"
    assert results[0].to_dict()["fixture_only"] is True


def test_invalid_request_rejects_missing_symbol_and_sensitive_metadata():
    missing_symbol = FixtureQuoteProvider().fetch_quote(QuoteRequest(symbol="", asset_type="stock", market="CN"))
    sensitive = FixtureQuoteProvider().fetch_quote(
        QuoteRequest(symbol="AAPL", asset_type="stock", market="US", metadata={"api_key": "api_key=abcdefghijklmnop123456"})
    )

    assert missing_symbol.source_status == "invalid_request"
    assert sensitive.source_status == "invalid_request"
