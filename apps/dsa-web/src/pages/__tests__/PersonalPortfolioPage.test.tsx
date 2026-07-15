import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UiLanguageProvider } from '../../contexts/UiLanguageContext';
import PersonalPortfolioPage from '../PersonalPortfolioPage';

const { getAccounts, getSnapshot, getRisk } = vi.hoisted(() => ({
  getAccounts: vi.fn(),
  getSnapshot: vi.fn(),
  getRisk: vi.fn(),
}));

vi.mock('../../api/portfolio', () => ({
  portfolioApi: {
    getAccounts,
    getSnapshot,
    getRisk,
  },
}));

vi.mock('../PortfolioPage', () => ({
  default: () => <div>legacy-advanced-ledger</div>,
}));

function makeSnapshot() {
  return {
    asOf: '2026-07-15',
    costMethod: 'fifo' as const,
    currency: 'CNY',
    accountCount: 1,
    totalCash: 20000,
    totalMarketValue: 80000,
    totalEquity: 100000,
    realizedPnl: 1000,
    unrealizedPnl: 5000,
    feeTotal: 0,
    taxTotal: 0,
    fxStale: false,
    dataQuality: 'ok',
    limitations: [],
    accounts: [
      {
        accountId: 1,
        accountName: '个人股票账户',
        broker: 'Demo',
        market: 'cn',
        baseCurrency: 'CNY',
        asOf: '2026-07-15',
        costMethod: 'fifo' as const,
        totalCash: 20000,
        totalMarketValue: 80000,
        totalEquity: 100000,
        realizedPnl: 1000,
        unrealizedPnl: 5000,
        feeTotal: 0,
        taxTotal: 0,
        fxStale: false,
        positions: [
          {
            symbol: '600519',
            market: 'cn',
            currency: 'CNY',
            quantity: 10,
            avgCost: 1500,
            totalCost: 15000,
            lastPrice: 1600,
            marketValueBase: 16000,
            unrealizedPnlBase: 1000,
            unrealizedPnlPct: 6.67,
            valuationCurrency: 'CNY',
            priceAvailable: true,
          },
        ],
      },
    ],
  };
}

function makeRisk() {
  return {
    asOf: '2026-07-15',
    accountId: null,
    costMethod: 'fifo' as const,
    currency: 'CNY',
    thresholds: {},
    concentration: {
      totalMarketValue: 80000,
      topWeightPct: 20,
      alert: false,
      topPositions: [],
    },
    sectorConcentration: {
      totalMarketValue: 80000,
      topWeightPct: 35,
      alert: false,
      topSectors: [],
      coverage: {},
      errors: [],
    },
    drawdown: {
      seriesPoints: 10,
      maxDrawdownPct: -8,
      currentDrawdownPct: -2,
      alert: false,
      fxStale: false,
    },
    stopLoss: {
      nearAlert: true,
      triggeredCount: 1,
      nearCount: 2,
      items: [],
    },
    decisionSignalRisk: {
      available: true,
      total: 3,
      actions: { sell: 1, reduce: 1, alert: 1 },
      items: [],
    },
  };
}

function renderPage() {
  render(
    <UiLanguageProvider>
      <PersonalPortfolioPage />
    </UiLanguageProvider>,
  );
}

describe('PersonalPortfolioPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    getAccounts.mockResolvedValue({
      accounts: [
        {
          id: 1,
          name: '个人股票账户',
          broker: 'Demo',
          market: 'cn',
          baseCurrency: 'CNY',
          isActive: true,
        },
      ],
    });
    getSnapshot.mockResolvedValue(makeSnapshot());
    getRisk.mockResolvedValue(makeRisk());
  });

  it('shows personal summary, fund placeholder, and stock table while keeping advanced ledger closed', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: '个人持仓' })).toBeInTheDocument();
    expect(await screen.findByText('CNY 100,000.00')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '基金持仓' })).toBeInTheDocument();
    expect(screen.getByText('基金数据尚未接入')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '股票持仓' })).toBeInTheDocument();
    expect(screen.getByText('600519')).toBeInTheDocument();
    expect(screen.queryByText('legacy-advanced-ledger')).not.toBeInTheDocument();
  });

  it('loads the legacy tools only after the advanced ledger is opened', async () => {
    renderPage();
    await screen.findByRole('heading', { name: '个人持仓' });

    fireEvent.click(screen.getByRole('button', { name: /高级账本/ }));

    expect(await screen.findByText('legacy-advanced-ledger')).toBeInTheDocument();
    expect(screen.getByTestId('advanced-ledger-content')).toBeInTheDocument();
  });

  it('reloads snapshot and risk for a selected account', async () => {
    renderPage();
    await screen.findByRole('heading', { name: '个人持仓' });

    fireEvent.change(screen.getByLabelText('查看账户'), { target: { value: '1' } });

    await waitFor(() => {
      expect(getSnapshot).toHaveBeenLastCalledWith({ accountId: 1, costMethod: 'fifo' });
      expect(getRisk).toHaveBeenLastCalledWith({ accountId: 1, costMethod: 'fifo' });
    });
  });
});
