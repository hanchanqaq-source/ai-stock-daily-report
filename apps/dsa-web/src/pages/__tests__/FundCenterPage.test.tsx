import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PortfolioUserProvider } from '../../contexts/PortfolioUserContext';
import { UiLanguageProvider } from '../../contexts/UiLanguageContext';
import { UI_LANGUAGE_STORAGE_KEY } from '../../utils/uiLanguage';
import FundCenterPage from '../FundCenterPage';

const apiMocks = vi.hoisted(() => ({ fetchAksharePublicFund: vi.fn() }));

vi.mock('../../api/fundData', () => ({
  fundDataApi: { fetchAksharePublicFund: apiMocks.fetchAksharePublicFund },
}));

function renderPage(section: 'home' | 'ask' | 'industry-cycle') {
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
    expect(screen.getByText('待 D2 映射')).toBeInTheDocument();
  });

  it('keeps fund questions separate from the stock chat implementation', () => {
    renderPage('ask');

    expect(screen.getByRole('heading', { name: '问基金' })).toBeInTheDocument();
    expect(screen.getByText(/输入六位基金代码并逐次确认后读取公开资料/)).toBeInTheDocument();
    expect(screen.getByText(/本页仍不生成虚假基金对比/)).toBeInTheDocument();
  });

  it('describes the required evidence boundary for industry cycles', () => {
    renderPage('industry-cycle');

    expect(screen.getByText(/证据、日期、周期阶段、置信度和缺失项/)).toBeInTheDocument();
  });
});
