import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import FundPortfolioAdvicePanel from './FundPortfolioAdvicePanel';

const api = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock('../../api/fundData', () => ({ fundDataApi: { fetchAkshareFundPortfolioAdvice: api.fetch } }));

const holdings = [
  { id: 'a', code: '000001', name: '基金A', amount: 7000, profit: 300, targetAllocation: 50 },
  { id: 'b', code: '000002', name: '基金B', amount: 3000, profit: -50, targetAllocation: 50 },
];

describe('FundPortfolioAdvicePanel', () => {
  beforeEach(() => api.fetch.mockReset());

  it('does not run automatically and requires per-request approval', async () => {
    api.fetch.mockResolvedValue({
      status: 'completed-readonly', providerLabel: 'AKShare 公开基金数据', readOnly: true,
      advice: {
        data_status: 'partial', risk_level: 'high', total_amount: '10000', total_profit: '250', holding_count: 2,
        unique_fund_count: 2, top_fund_weight_pct: '70', top3_weight_pct: '100', public_evidence_codes: ['000001', '000002'],
        public_evidence_coverage_pct: '100', funds: [],
        findings: [{ category: 'single-fund-concentration', severity: 'high', title: '单只基金占比较高', evidence: '000001 占基金组合 70%。' }],
        suggestions: [{ priority: 'high', title: '复核单只基金上限', reason: '人工确认。', action_scope: 'review-only-no-automatic-execution' }],
        missing_evidence: ['complete-industry-cycle-evidence'], warnings: ['披露数据不是实时仓位。'],
        scope: 'active-user-in-memory-fund-portfolio-review', advice_boundary: 'educational-review-not-investment-order',
      },
    });
    render(<FundPortfolioAdvicePanel language="zh" activeUserName="本人" holdings={holdings} />);

    const button = screen.getByRole('button', { name: '计算组合风险' });
    expect(button).toBeDisabled();
    expect(api.fetch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText(/我确认本次只在本机计算当前页面基金组合/));
    expect(button).toBeEnabled();
    fireEvent.click(button);

    await waitFor(() => expect(api.fetch).toHaveBeenCalledWith([
      { code: '000001', name: '基金A', amount: 7000, profit: 300, targetAllocation: 50 },
      { code: '000002', name: '基金B', amount: 3000, profit: -50, targetAllocation: 50 },
    ]));
    expect(await screen.findByTestId('fund-portfolio-advice-result')).toHaveTextContent('单只基金占比较高');
    expect(screen.getByText('配置复核建议（不自动执行）')).toBeInTheDocument();
  });

  it('blocks calculation when the active user has no fund holdings', () => {
    render(<FundPortfolioAdvicePanel language="zh" activeUserName="用户B" holdings={[]} />);
    expect(screen.getByText(/请先到“基金持仓”录入/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '计算组合风险' })).toBeDisabled();
    expect(api.fetch).not.toHaveBeenCalled();
  });
});
