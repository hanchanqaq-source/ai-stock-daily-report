import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePortfolioUsers } from '../../contexts/PortfolioUserContext';
import FundAnalysisSourceSelector from './FundAnalysisSourceSelector';
import { parseFundCodeInput } from './fundAnalysisSource';

vi.mock('../../contexts/PortfolioUserContext', () => ({
  usePortfolioUsers: vi.fn(),
}));

const mockedUsePortfolioUsers = vi.mocked(usePortfolioUsers);
const onSelectionChange = vi.fn();

function setContext({
  holdings = [],
  watchlist = [],
}: {
  holdings?: Array<{ id: string; code: string; name: string; amount: number; profit: number }>;
  watchlist?: Array<{ id: string; code: string; name: string }>;
} = {}) {
  mockedUsePortfolioUsers.mockReturnValue({
    activeUser: { id: 'user-a', name: '用户甲', isPrimary: false },
    activeFundHoldings: holdings,
    activeFundWatchlist: watchlist,
    persistenceStatus: 'ready',
  } as unknown as ReturnType<typeof usePortfolioUsers>);
}

function renderSelector(minimum = 1, maximum = 4) {
  render(
    <FundAnalysisSourceSelector
      language="zh"
      minimum={minimum}
      maximum={maximum}
      inputLabel="基金代码"
      placeholder="例如 000001, 110022"
      onSelectionChange={onSelectionChange}
    />,
  );
}

describe('FundAnalysisSourceSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setContext();
  });

  it('parses manual codes without starting any external action', () => {
    renderSelector(1, 4);

    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '000001， 110022;000002' } });

    expect(onSelectionChange).toHaveBeenLastCalledWith({
      source: 'manual',
      codes: ['000001', '110022', '000002'],
    });
    expect(screen.getByText('000001 · 110022 · 000002')).toBeInTheDocument();
  });

  it('uses a single current-user holding without exposing its amount', () => {
    setContext({
      holdings: [
        { id: 'fund-1', code: '000001', name: '持仓基金一', amount: 1234.56, profit: 78.9 },
        { id: 'fund-2', code: '110022', name: '持仓基金二', amount: 500, profit: -5 },
      ],
    });
    renderSelector(1, 1);

    fireEvent.click(screen.getByRole('button', { name: /我的持仓 \(2\)/ }));
    expect(onSelectionChange).toHaveBeenLastCalledWith({ source: 'holdings', codes: [] });
    fireEvent.click(screen.getByRole('button', { name: '选择 000001 持仓基金一' }));
    expect(onSelectionChange).toHaveBeenLastCalledWith({ source: 'holdings', codes: ['000001'] });
    fireEvent.click(screen.getByRole('button', { name: '选择 110022 持仓基金二' }));
    expect(onSelectionChange).toHaveBeenLastCalledWith({ source: 'holdings', codes: ['110022'] });
    expect(screen.queryByText('1234.56')).not.toBeInTheDocument();
    expect(screen.queryByText('78.9')).not.toBeInTheDocument();
  });

  it('deduplicates watchlist options and enforces the multi-select maximum', () => {
    setContext({
      watchlist: [
        { id: 'watch-1', code: '000001', name: '自选一' },
        { id: 'watch-duplicate', code: '000001', name: '重复自选' },
        { id: 'watch-2', code: '000002', name: '自选二' },
        { id: 'watch-3', code: '000003', name: '自选三' },
      ],
    });
    renderSelector(1, 2);

    fireEvent.click(screen.getByRole('button', { name: /我的自选 \(3\)/ }));
    fireEvent.click(screen.getByRole('button', { name: '选择 000001 自选一' }));
    fireEvent.click(screen.getByRole('button', { name: '选择 000002 自选二' }));

    expect(onSelectionChange).toHaveBeenLastCalledWith({ source: 'watchlist', codes: ['000001', '000002'] });
    expect(screen.getByRole('button', { name: '选择 000003 自选三' })).toBeDisabled();
    expect(screen.queryByText('重复自选')).not.toBeInTheDocument();
  });

  it('keeps manual text locally but clears cross-source selection', () => {
    setContext({ watchlist: [{ id: 'watch-1', code: '000001', name: '自选一' }] });
    renderSelector(1, 4);

    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '110022' } });
    fireEvent.click(screen.getByRole('button', { name: /我的自选 \(1\)/ }));
    expect(onSelectionChange).toHaveBeenLastCalledWith({ source: 'watchlist', codes: [] });
    fireEvent.click(screen.getByRole('button', { name: /手动输入/ }));
    expect(onSelectionChange).toHaveBeenLastCalledWith({ source: 'manual', codes: ['110022'] });
    expect(screen.getByLabelText('基金代码')).toHaveValue('110022');
  });
});

describe('parseFundCodeInput', () => {
  it('preserves duplicates so parent validation can reject them', () => {
    expect(parseFundCodeInput('000001,000001')).toEqual(['000001', '000001']);
  });
});
