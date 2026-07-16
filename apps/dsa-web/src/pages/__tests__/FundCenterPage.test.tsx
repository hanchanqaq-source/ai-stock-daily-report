import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PortfolioUserProvider, usePortfolioUsers } from '../../contexts/PortfolioUserContext';
import { UiLanguageProvider } from '../../contexts/UiLanguageContext';
import { UI_LANGUAGE_STORAGE_KEY } from '../../utils/uiLanguage';
import FundCenterPage from '../FundCenterPage';

const apiMocks = vi.hoisted(() => ({
  fetchAksharePublicFund: vi.fn(),
  compareAksharePublicFunds: vi.fn(),
  fetchAkshareFundIndustryCycle: vi.fn(),
  fetchAkshareFundPortfolioAdvice: vi.fn(),
}));

vi.mock('../../api/fundData', () => ({
  fundDataApi: {
    fetchAksharePublicFund: apiMocks.fetchAksharePublicFund,
    compareAksharePublicFunds: apiMocks.compareAksharePublicFunds,
    fetchAkshareFundIndustryCycle: apiMocks.fetchAkshareFundIndustryCycle,
    fetchAkshareFundPortfolioAdvice: apiMocks.fetchAkshareFundPortfolioAdvice,
  },
}));

function renderPage(section: 'home' | 'ask' | 'compare' | 'industry-exposure' | 'industry-cycle' | 'advice') {
  render(
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <MemoryRouter><FundCenterPage section={section} /></MemoryRouter>
      </PortfolioUserProvider>
    </UiLanguageProvider>,
  );
}

function AdviceControls() {
  const { addFundHolding, addUser } = usePortfolioUsers();
  return (
    <>
      <button type="button" onClick={() => addFundHolding({ code: '000001', name: '公开基金', amount: 1000, profit: 0, targetAllocation: 100 })}>seed-fund</button>
      <button type="button" onClick={() => addUser('家人')}>switch-user</button>
    </>
  );
}

function renderAdvicePage() {
  render(
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <AdviceControls />
        <MemoryRouter><FundCenterPage section="advice" /></MemoryRouter>
      </PortfolioUserProvider>
    </UiLanguageProvider>,
  );
}

describe('FundCenterPage', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, 'zh');
    apiMocks.fetchAksharePublicFund.mockReset();
    apiMocks.compareAksharePublicFunds.mockReset();
    apiMocks.fetchAkshareFundIndustryCycle.mockReset();
    apiMocks.fetchAkshareFundPortfolioAdvice.mockReset();
  });

  it('shows fund-only tasks and the real-data boundary on the fund home', () => {
    renderPage('home');

    expect(screen.getByRole('heading', { name: '基金首页' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /进入基金持仓/ })).toBeInTheDocument();
    expect(screen.getByText('AKShare 基金公开数据支持本机手动只读查询')).toBeInTheDocument();
    expect(screen.getByText('Build C 基金数据契约')).toBeInTheDocument();
    expect(screen.getByText('披露持仓')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '手动读取' })).toBeDisabled();
    expect(apiMocks.fetchAksharePublicFund).not.toHaveBeenCalled();
    expect(screen.queryByText('股票回测')).not.toBeInTheDocument();
  });

  it('requires a six-digit code and per-request read-only approval before calling AKShare', async () => {
    apiMocks.fetchAksharePublicFund.mockResolvedValue({
      status: 'completed-readonly',
      providerLabel: 'AKShare 公开基金数据',
      readOnly: true,
      bundle: {
        code: '000001', requested_sections: ['profile', 'nav', 'holdings'], data_status: 'partial',
        source: { provider: 'akshare_fund_public', source_kind: 'provider', source_status: 'partial', fetched_at: '2026-07-16T10:00:00+00:00', effective_at: null, report_period: null, stale: false, stale_reason: '', confidence: '0.85', missing_fields: [], missing_reasons: {} },
        profile: { code: '000001', name: '公开基金', fund_type: '混合型', manager: '公开经理', scale: '12.34', scale_currency: 'CNY_100M', inception_date: '2020-01-02', source: { provider: 'akshare_fund_public', source_kind: 'provider', source_status: 'available', fetched_at: '2026-07-16T10:00:00+00:00', effective_at: null, report_period: null, stale: false, stale_reason: '', confidence: '0.9', missing_fields: [], missing_reasons: {} } },
        nav: { code: '000001', unit_nav: '1.23', accumulated_nav: '1.5', daily_change_pct: '0.2', nav_date: '2026-07-15', source: { provider: 'akshare_fund_public', source_kind: 'provider', source_status: 'partial', fetched_at: '2026-07-16T10:00:00+00:00', effective_at: '2026-07-15', report_period: null, stale: false, stale_reason: '', confidence: '0.9', missing_fields: ['estimated_nav'], missing_reasons: { estimated_nav: 'not provided' } } },
        holdings: { code: '000001', report_period: '2026-Q2', disclosed_total_pct: '8.5', source: { provider: 'akshare_fund_public', source_kind: 'provider', source_status: 'available', fetched_at: '2026-07-16T10:00:00+00:00', effective_at: null, report_period: '2026-Q2', stale: false, stale_reason: '', confidence: '0.85', missing_fields: [], missing_reasons: {} }, positions: [{ security_code: '600001', security_name: '公开证券', weight_pct: '8.5', industry: { status: 'unknown', industry_code: null, industry_name: null, source: { provider: 'akshare_fund_public', source_kind: 'provider', source_status: 'partial', fetched_at: '2026-07-16T10:00:00+00:00', effective_at: null, report_period: '2026-Q2', stale: false, stale_reason: '', confidence: '0', missing_fields: ['industry_code', 'industry_name'], missing_reasons: { industry_code: 'pending', industry_name: 'pending' } } } }] },
        missing_sections: [], reason: '部分字段缺失，请按来源日期使用。',
      },
    });
    renderPage('home');

    const button = screen.getByRole('button', { name: '手动读取' });
    fireEvent.change(screen.getByLabelText('六位基金代码'), { target: { value: '000001' } });
    expect(button).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/我确认本次仅获取公开只读基金数据/));
    expect(button).toBeEnabled();
    fireEvent.click(button);

    await waitFor(() => expect(apiMocks.fetchAksharePublicFund).toHaveBeenCalledWith('000001'));
    expect(await screen.findByTestId('fund-public-readonly-result')).toHaveTextContent('公开基金');
    expect(screen.getByText('见行业穿透页')).toBeInTheDocument();
  });

  it('keeps fund questions separate from the stock chat implementation', () => {
    renderPage('ask');

    expect(screen.getByRole('heading', { name: '问基金' })).toBeInTheDocument();
    expect(screen.getByText(/输入六位基金代码并逐次确认后读取公开资料/)).toBeInTheDocument();
    expect(screen.getByText(/Build D4 已在“基金仓位与风险建议”页面接入/)).toBeInTheDocument();
  });

  it('requires two unique codes and per-request approval on the comparison page', async () => {
    apiMocks.compareAksharePublicFunds.mockResolvedValue({
      status: 'completed-readonly',
      providerLabel: 'AKShare 公开基金数据',
      readOnly: true,
      comparison: {
        requested_codes: ['000001', '110022'],
        data_status: 'partial',
        source: { provider: 'akshare_fund_public', source_kind: 'provider', source_status: 'partial', fetched_at: '2026-07-16T10:00:00+00:00', effective_at: null, report_period: null, stale: false, stale_reason: '', confidence: '0.85', missing_fields: [], missing_reasons: {} },
        funds: [], pair_overlaps: [], missing_funds: [], reason: '测试为部分数据',
      },
    });
    renderPage('compare');

    expect(apiMocks.compareAksharePublicFunds).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: '读取并计算' });
    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '000001' } });
    fireEvent.click(screen.getByLabelText(/我确认本次只读取公开基金披露/));
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '000001, 110022' } });
    expect(button).toBeEnabled();
    fireEvent.click(button);

    await waitFor(() => expect(apiMocks.compareAksharePublicFunds).toHaveBeenCalledWith(['000001', '110022']));
    expect(await screen.findByTestId('fund-comparison-result')).toHaveTextContent('测试为部分数据');
  });

  it('allows a single code on the industry exposure page without calling automatically', () => {
    renderPage('industry-exposure');

    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '000001' } });
    fireEvent.click(screen.getByLabelText(/我确认本次只读取公开基金披露/));
    expect(screen.getByRole('button', { name: '读取并计算' })).toBeEnabled();
    expect(apiMocks.compareAksharePublicFunds).not.toHaveBeenCalled();
    expect(screen.getByText(/结果不是行业周期、生产力或买卖建议/)).toBeInTheDocument();
  });

  it('requires approval and keeps cycle and productivity evidence separate', async () => {
    apiMocks.fetchAkshareFundIndustryCycle.mockResolvedValue({
      status: 'completed-readonly',
      providerLabel: 'AKShare 公开基金数据',
      readOnly: true,
      cycle: {
        requested_codes: ['000001'], data_status: 'partial', fetched_at: '2026-07-16T10:00:00+00:00', provider: 'akshare_fund_public', benchmark_code: '000300', financial_report_period: '2026-Q2',
        funds: [{ code: '000001', name: '公开基金', holdings_report_period: '2026-Q2', industry_links: [{ industry_name: '软件开发', fund_weight_pct: '35', scope: 'provider-disclosed-industry-allocation' }], analyzed_weight_pct: '35', unclassified_holdings: [], omitted_industries: 0, warnings: [] }],
        industries: [{
          industry_name: '软件开发', board_code: 'BK0737', data_status: 'partial', phase: 'expansion', confidence: '0.85',
          metrics: { as_of_date: '2026-07-15', return_20d_pct: '8', return_60d_pct: '15', turnover_change_20d_pct: '20', breadth_rise_ratio_pct: '70', relative_strength_20d_pct: '5', median_dynamic_pe: '25', median_pb: '3', constituent_count: 8, breadth_sample_count: 8 },
          productivity: { status: 'improving', report_period: '2026-Q2', effective_at: '2026-06-30', revenue_yoy_median_pct: '18', profit_yoy_median_pct: '22', roe_median_pct: '12', gross_margin_median_pct: '45', operating_cashflow_positive_ratio_pct: '100', covered_constituents: 8, total_constituents: 8, confidence: '0.8', missing_dimensions: ['capital_expenditure'], scope: 'operating-productivity-proxy-not-total-factor-productivity' },
          source_interfaces: ['stock_board_industry_hist_em', 'stock_board_industry_cons_em', 'index_zh_a_hist', 'stock_yjbb_em'], evidence_dates: ['2026-07-15', '2026-06-30'], missing_evidence: [], warnings: [], cycle_scope: 'market-cycle-evidence-not-trading-advice',
        }],
        missing_evidence: [], warnings: ['短期行业周期与长期经营生产力代理分开展示。'], method: 'deterministic-explainable-features-inspired-by-market-state-analysis',
      },
    });
    renderPage('industry-cycle');

    expect(apiMocks.fetchAkshareFundIndustryCycle).not.toHaveBeenCalled();
    expect(screen.getByText(/短期周期和长期经营证据分开计算/)).toBeInTheDocument();
    const button = screen.getByRole('button', { name: '读取周期证据' });
    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '000001' } });
    expect(button).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/我确认本次仅读取公开基金、行业行情和业绩报表/));
    expect(button).toBeEnabled();
    fireEvent.click(button);

    await waitFor(() => expect(apiMocks.fetchAkshareFundIndustryCycle).toHaveBeenCalledWith(['000001']));
    expect(await screen.findByTestId('fund-industry-cycle-result')).toHaveTextContent('扩张');
    expect(screen.getByRole('heading', { name: /经营生产力代理证据：改善/ })).toBeInTheDocument();
  });

  it('uses only the active user normalized fund weights and clears the result after switching users', async () => {
    apiMocks.fetchAkshareFundPortfolioAdvice.mockResolvedValue({
      status: 'completed-readonly', providerLabel: 'AKShare 公开基金数据', readOnly: true,
      advice: {
        requested_codes: ['000001'], data_status: 'partial', fetched_at: '2026-07-16T12:30:00+00:00', risk_profile: 'balanced',
        positions: [{ code: '000001', weight_pct: '100', target_weight_pct: '100' }],
        input_privacy: { amount_shared: false, cost_basis_shared: false, user_identity_shared: false, account_read: false },
        concentration: { status: 'high', largest_fund_weight_pct: '100', top_two_weight_pct: '100', herfindahl_index: '1', effective_fund_count: '1', attention_thresholds: { single_fund_pct: '40', top_two_pct: '70', scope: 'monitoring-thresholds-not-prescribed-allocation' } },
        disclosed_overlap: { status: 'not-applicable', max_disclosed_holdings_overlap_pct: null, max_disclosed_industry_overlap_pct: null, highest_pair: null, pair_count: 0, scope: 'latest-disclosed-data-lower-bound' },
        industry_exposure: { status: 'watch', disclosed_portfolio_coverage_pct: '60', unclassified_or_undisclosed_pct: '40', top_industries: [{ industry_name: '软件开发', portfolio_exposure_pct: '30' }], top_three_exposure_pct: '30', report_dates: ['2026-06-30'], attention_threshold_pct: '25', scope: 'provider-disclosed-look-through-not-complete-current-portfolio' },
        nav_risk: { status: 'normal', weighted_average_fund_volatility_60d_pct: '12', volatility_coverage_pct: '100', worst_fund_drawdown_120d_pct: '-8', funds: [{ code: '000001', data_status: 'available', as_of_date: '2026-07-15', observations: 90, return_20d_pct: '3', return_60d_pct: '8', annualized_volatility_60d_pct: '12', max_drawdown_120d_pct: '-8', missing_evidence: [] }], attention_thresholds: { annualized_volatility_pct: '25', drawdown_magnitude_pct: '15' }, scope: 'weighted-average-of-fund-volatility-not-covariance-portfolio-volatility' },
        cycle_exposure: { status: 'watch', analyzed_portfolio_exposure_pct: '30', phase_exposure_pct: { expansion: '20', slowdown: '10' }, pressure_exposure_pct: '10', weakening_productivity_proxy_exposure_pct: '0', financial_report_period: '2026-Q2', scope: 'selected-disclosed-industry-evidence-not-market-timing-signal' },
        allocation_guidance: [{ id: 'fund-concentration', priority: 'high', title: '基金集中度需要复核', reason: '超过关注阈值', evidence: ['状态 high'], action: '核对当前占比是否符合目标。' }],
        missing_evidence: [], warnings: ['只用于人工复核。'], method: 'deterministic-current-user-fund-risk-and-allocation-review',
      },
    });
    renderAdvicePage();

    expect(screen.getByText('当前用户还没有可分析的基金持仓。')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'seed-fund' }));
    expect(screen.getByText(/000001 · 100.00%/)).toBeInTheDocument();
    const runButton = screen.getByRole('button', { name: '分析当前组合' });
    expect(runButton).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/我确认本次只发送基金代码/));
    fireEvent.click(runButton);

    await waitFor(() => expect(apiMocks.fetchAkshareFundPortfolioAdvice).toHaveBeenCalledWith(
      [{ code: '000001', weightPct: 100, targetWeightPct: 100 }],
      'balanced',
    ));
    expect(await screen.findByTestId('fund-portfolio-advice-result')).toHaveTextContent('基金集中度需要复核');
    expect(screen.getByText(/金额\/成本\/用户身份未发送/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'switch-user' }));
    await waitFor(() => expect(screen.queryByTestId('fund-portfolio-advice-result')).not.toBeInTheDocument());
    expect(screen.getByRole('heading', { name: '家人 的基金组合' })).toBeInTheDocument();
    expect(screen.getByText('当前用户还没有可分析的基金持仓。')).toBeInTheDocument();
  });
});
