import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PortfolioUserProvider } from '../../contexts/PortfolioUserContext';
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

function renderPage(section: 'home' | 'ask' | 'watchlist' | 'compare' | 'industry-exposure' | 'industry-cycle' | 'advice') {
  render(
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <MemoryRouter><FundCenterPage section={section} /></MemoryRouter>
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
    expect(screen.getByText('基金自选')).toBeInTheDocument();
    expect(screen.getByText('AKShare 基金公开数据支持本机手动只读查询')).toBeInTheDocument();
    expect(screen.getByText('Build C 基金数据契约')).toBeInTheDocument();
    expect(screen.getByText('披露持仓')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '手动读取' })).toBeDisabled();
    expect(apiMocks.fetchAksharePublicFund).not.toHaveBeenCalled();
    expect(screen.queryByText('股票回测')).not.toBeInTheDocument();
  });

  it('shows the local per-user fund watchlist separately from holdings and public lookup', () => {
    renderPage('watchlist');

    expect(screen.getByRole('heading', { name: '基金自选' })).toBeInTheDocument();
    expect(screen.getByTestId('fund-watchlist-panel')).toBeInTheDocument();
    expect(screen.getByText(/不自动加入持仓/)).toBeInTheDocument();
    expect(screen.getByText(/不自动查询/)).toBeInTheDocument();
    expect(screen.queryByText('Build C 基金数据契约')).not.toBeInTheDocument();
    expect(apiMocks.fetchAksharePublicFund).not.toHaveBeenCalled();
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

  it('prepares fund question subjects without starting public lookup or AI', () => {
    renderPage('ask');

    expect(screen.getByRole('heading', { name: '问基金' })).toBeInTheDocument();
    expect(screen.getByText('持久化阶段 E4 已接入统一基金来源选择')).toBeInTheDocument();
    expect(screen.getByText(/这里只准备当前用户的基金代码上下文/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '000001, 110022' } });
    expect(screen.getByText(/已准备基金对象/)).toHaveTextContent('000001、110022');
    expect(apiMocks.fetchAksharePublicFund).not.toHaveBeenCalled();
    expect(apiMocks.compareAksharePublicFunds).not.toHaveBeenCalled();
  });

  it('shows D4 advice for the active user without reading automatically', () => {
    renderPage('advice');

    expect(screen.getByText('Build D4 已接入当前用户基金组合风险与配置复核建议')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '本人的基金组合' })).toBeInTheDocument();
    expect(screen.getByText(/请先到“基金持仓”录入/)).toBeInTheDocument();
    expect(apiMocks.fetchAkshareFundPortfolioAdvice).not.toHaveBeenCalled();
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
});
