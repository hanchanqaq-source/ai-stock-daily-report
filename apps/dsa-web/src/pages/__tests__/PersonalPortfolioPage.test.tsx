import type React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PortfolioUserProvider, usePortfolioUsers } from '../../contexts/PortfolioUserContext';
import { UiLanguageProvider } from '../../contexts/UiLanguageContext';
import { UI_LANGUAGE_STORAGE_KEY } from '../../utils/uiLanguage';
import PersonalPortfolioPage from '../PersonalPortfolioPage';
import UsersPage from '../UsersPage';

const { getAccounts, getSnapshot, getRisk } = vi.hoisted(() => ({
  getAccounts: vi.fn(),
  getSnapshot: vi.fn(),
  getRisk: vi.fn(),
}));

vi.mock('../../api/portfolio', () => ({
  portfolioApi: { getAccounts, getSnapshot, getRisk },
}));

function makeSnapshot() {
  return {
    asOf: '2026-07-15', costMethod: 'fifo' as const, currency: 'CNY', accountCount: 1,
    totalCash: 20000, totalMarketValue: 80000, totalEquity: 100000,
    realizedPnl: 1000, unrealizedPnl: 5000, feeTotal: 0, taxTotal: 0,
    fxStale: false, dataQuality: 'ok', limitations: [],
    accounts: [{
      accountId: 1, accountName: '个人证券账户', broker: 'Demo', market: 'cn', baseCurrency: 'CNY',
      asOf: '2026-07-15', costMethod: 'fifo' as const, totalCash: 20000,
      totalMarketValue: 80000, totalEquity: 100000, realizedPnl: 1000, unrealizedPnl: 5000,
      feeTotal: 0, taxTotal: 0, fxStale: false,
      positions: [{
        symbol: '600519', market: 'cn', currency: 'CNY', quantity: 10, avgCost: 1500,
        totalCost: 15000, lastPrice: 1600, marketValueBase: 16000,
        unrealizedPnlBase: 1000, unrealizedPnlPct: 6.67,
        valuationCurrency: 'CNY', priceAvailable: true,
      }],
    }],
  };
}

function makeRisk() {
  return {
    asOf: '2026-07-15', accountId: null, costMethod: 'fifo' as const, currency: 'CNY', thresholds: {},
    concentration: { totalMarketValue: 80000, topWeightPct: 20, alert: false, topPositions: [] },
    sectorConcentration: { totalMarketValue: 80000, topWeightPct: 35, alert: false, topSectors: [], coverage: {}, errors: [] },
    drawdown: { seriesPoints: 10, maxDrawdownPct: -8, currentDrawdownPct: -2, alert: false, fxStale: false },
    stopLoss: { nearAlert: true, triggeredCount: 1, nearCount: 2, items: [] },
    decisionSignalRisk: { available: true, total: 3, actions: { sell: 1, reduce: 1, alert: 1 }, items: [] },
  };
}

const AddFamilyUser: React.FC = () => {
  const { addUser, setActiveUserId } = usePortfolioUsers();
  return (
    <button type="button" onClick={() => {
      const user = addUser('家人A');
      if (user) setActiveUserId(user.id);
    }}>
      add-family-user
    </button>
  );
};

function renderPage() {
  render(
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <MemoryRouter initialEntries={['/portfolio']}>
          <AddFamilyUser />
          <Routes>
            <Route path="/portfolio" element={<PersonalPortfolioPage />} />
            <Route path="/stocks/portfolio/manage" element={<div>stock-management-destination</div>} />
            <Route path="/users" element={<UsersPage />} />
          </Routes>
        </MemoryRouter>
      </PortfolioUserProvider>
    </UiLanguageProvider>,
  );
}

function renderDomainPage(domain: 'stock' | 'fund') {
  const path = domain === 'stock' ? '/stocks/portfolio' : '/funds/portfolio';
  render(
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes><Route path={path} element={<PersonalPortfolioPage domain={domain} />} /></Routes>
        </MemoryRouter>
      </PortfolioUserProvider>
    </UiLanguageProvider>,
  );
}

describe('PersonalPortfolioPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, 'zh');
    getAccounts.mockResolvedValue({
      accounts: [{ id: 1, name: '个人证券账户', broker: 'Demo', market: 'cn', baseCurrency: 'CNY', isActive: true }],
    });
    getSnapshot.mockResolvedValue(makeSnapshot());
    getRisk.mockResolvedValue(makeRisk());
  });

  it('keeps fund analysis free of stock ledger tools and places them under stocks', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: '我的持仓分析' })).toBeInTheDocument();
    expect(await screen.findByText('CNY 100,000.00')).toBeInTheDocument();
    expect(screen.getByLabelText('当前用户')).toHaveValue('self');

    const fundSection = screen.getByTestId('fund-portfolio-section');
    expect(within(fundSection).getByRole('heading', { name: '基金持仓分析' })).toBeInTheDocument();
    expect(within(fundSection).queryByText('资金流水')).not.toBeInTheDocument();
    expect(within(fundSection).queryByText('公司行为')).not.toBeInTheDocument();
    expect(within(fundSection).queryByText('券商 CSV')).not.toBeInTheDocument();

    const stockSection = screen.getByTestId('stock-portfolio-section');
    expect(within(stockSection).getByText('600519')).toBeInTheDocument();
    expect(within(stockSection).getByText('资金流水')).toBeInTheDocument();
    expect(within(stockSection).getByText('公司行为')).toBeInTheDocument();
    expect(within(stockSection).getByText('券商 CSV')).toBeInTheDocument();
    expect(within(stockSection).getAllByText('证券账户').length).toBeGreaterThan(0);
  });

  it('opens the dedicated stock management and user routes', async () => {
    renderPage();
    await screen.findByRole('heading', { name: '我的持仓分析' });

    fireEvent.click(screen.getByRole('button', { name: '进入股票高级管理' }));
    expect(await screen.findByText('stock-management-destination')).toBeInTheDocument();
  });

  it('reloads stock snapshot and risk for a selected securities account', async () => {
    renderPage();
    await screen.findByRole('heading', { name: '我的持仓分析' });

    fireEvent.change(screen.getByLabelText('证券账户'), { target: { value: '1' } });

    await waitFor(() => {
      expect(getSnapshot).toHaveBeenLastCalledWith({ accountId: 1, costMethod: 'fifo' });
      expect(getRisk).toHaveBeenLastCalledWith({ accountId: 1, costMethod: 'fifo' });
    });
  });

  it('isolates a non-primary user from the primary stock snapshot', async () => {
    renderPage();
    await screen.findByText('600519');

    fireEvent.click(screen.getByRole('button', { name: 'add-family-user' }));

    expect(await screen.findByText('该用户尚未接入正式持仓数据')).toBeInTheDocument();
    expect(screen.queryByText('600519')).not.toBeInTheDocument();
    expect(screen.getByLabelText('当前用户')).not.toHaveValue('self');
  });

  it('keeps the stock and fund portfolio routes visually separated', async () => {
    renderDomainPage('stock');

    expect(await screen.findByRole('heading', { name: '股票持仓' })).toBeInTheDocument();
    expect(screen.getByTestId('stock-portfolio-section')).toBeInTheDocument();
    expect(screen.queryByTestId('fund-portfolio-section')).not.toBeInTheDocument();
  });

  it('does not load stock account APIs inside the fund portfolio route', async () => {
    renderDomainPage('fund');

    expect(await screen.findByRole('heading', { name: '基金持仓' })).toBeInTheDocument();
    expect(screen.getByTestId('fund-portfolio-section')).toBeInTheDocument();
    expect(screen.queryByTestId('stock-portfolio-section')).not.toBeInTheDocument();
    expect(getAccounts).not.toHaveBeenCalled();
    expect(getSnapshot).not.toHaveBeenCalled();
    expect(getRisk).not.toHaveBeenCalled();
  });
});
