import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UiLanguageProvider } from '../../contexts/UiLanguageContext';
import { UI_LANGUAGE_STORAGE_KEY } from '../../utils/uiLanguage';
import FundCenterPage from '../FundCenterPage';

const portfolioState = vi.hoisted(() => ({
  current: {
    activeUser: { id: 'user-a', name: '用户甲', isPrimary: false },
    activeFundHoldings: [{ id: 'fund-a', code: '000001', name: '甲的基金', amount: 100, profit: 1 }],
    activeFundWatchlist: [],
    persistenceStatus: 'ready',
  },
}));

vi.mock('../../contexts/PortfolioUserContext', () => ({
  usePortfolioUsers: () => portfolioState.current,
}));

const apiMocks = vi.hoisted(() => ({
  fetchAksharePublicFund: vi.fn(),
  compareAksharePublicFunds: vi.fn(),
  fetchAkshareFundIndustryCycle: vi.fn(),
  fetchAkshareFundPortfolioAdvice: vi.fn(),
}));

vi.mock('../../api/fundData', () => ({ fundDataApi: apiMocks }));

function page() {
  return (
    <UiLanguageProvider>
      <MemoryRouter><FundCenterPage section="home" /></MemoryRouter>
    </UiLanguageProvider>
  );
}

describe('FundCenterPage active-user source reset', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, 'zh');
    vi.clearAllMocks();
    portfolioState.current = {
      activeUser: { id: 'user-a', name: '用户甲', isPrimary: false },
      activeFundHoldings: [{ id: 'fund-a', code: '000001', name: '甲的基金', amount: 100, profit: 1 }],
      activeFundWatchlist: [],
      persistenceStatus: 'ready',
    };
  });

  it('clears temporary code and approval when the active user changes', () => {
    const view = render(page());

    fireEvent.change(screen.getByLabelText('六位基金代码'), { target: { value: '000001' } });
    fireEvent.click(screen.getByLabelText(/我确认本次仅获取公开只读基金数据/));
    expect(screen.getByRole('button', { name: '手动读取' })).toBeEnabled();

    portfolioState.current = {
      activeUser: { id: 'user-b', name: '用户乙', isPrimary: false },
      activeFundHoldings: [{ id: 'fund-b', code: '110022', name: '乙的基金', amount: 200, profit: 2 }],
      activeFundWatchlist: [],
      persistenceStatus: 'ready',
    };
    view.rerender(page());

    expect(screen.getByLabelText('六位基金代码')).toHaveValue('');
    expect(screen.getByLabelText(/我确认本次仅获取公开只读基金数据/)).not.toBeChecked();
    expect(screen.getByRole('button', { name: '手动读取' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: /我的持仓 \(1\)/ }));
    expect(screen.getByText('乙的基金')).toBeInTheDocument();
    expect(screen.queryByText('甲的基金')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '选择 110022 乙的基金' }));
    expect(screen.getByRole('button', { name: '手动读取' })).toBeDisabled();
    expect(apiMocks.fetchAksharePublicFund).not.toHaveBeenCalled();
  });
});
