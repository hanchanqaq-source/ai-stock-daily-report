import type React from 'react';
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { portfolioApi } from '../api/portfolio';
import { getParsedApiError, type ParsedApiError } from '../api/error';
import { ApiErrorAlert, Card, EmptyState, InlineAlert } from '../components/common';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import type {
  PortfolioAccountItem,
  PortfolioCostMethod,
  PortfolioPositionItem,
  PortfolioRiskResponse,
  PortfolioSnapshotResponse,
} from '../types/portfolio';
import {
  formatMoney,
  formatPct,
  formatPositionMoney,
  formatPositionPrice,
  formatSignedPct,
} from '../utils/portfolioFormat';

const AdvancedPortfolioLedger = lazy(() => import('./PortfolioPage'));

type AccountOption = 'all' | number;

type StockPositionRow = PortfolioPositionItem & {
  accountId: number;
  accountName: string;
};

const TEXT = {
  zh: {
    documentTitle: '个人持仓 - DSA',
    title: '个人持仓',
    description: '先看资产、收益、仓位和风险；交易流水、资金流水与券商工具收进高级账本。',
    account: '查看账户',
    allAccounts: '全部账户',
    costMethod: '成本口径',
    fifo: '先进先出',
    avg: '均价成本',
    refresh: '刷新',
    refreshing: '刷新中',
    totalAssets: '总资产',
    stockValue: '股票持仓市值',
    availableCash: '可用现金',
    holdingProfit: '持仓浮动收益',
    fundTitle: '基金持仓',
    fundBadge: 'M2 接入快速录入',
    fundAmount: '基金持有金额',
    fundProfit: '持有收益',
    fundReturn: '持有收益率',
    fundPosition: '当前仓位',
    fundEmptyTitle: '基金数据尚未接入',
    fundEmptyDescription: 'M1 不伪造基金数据。下一阶段会增加基金类型、持有金额、目标仓位和卡片式快速录入。',
    stockTitle: '股票持仓',
    stockCount: '共 {count} 项',
    noStockTitle: '暂无股票持仓',
    noStockDescription: '高级账本中录入交易或导入券商 CSV 后，股票持仓会显示在这里。',
    accountColumn: '账户',
    code: '代码',
    quantity: '数量',
    avgCost: '平均成本',
    currentPrice: '当前价格',
    marketValue: '市值',
    profit: '浮动盈亏',
    returnPct: '收益率',
    riskTitle: '个人风险概览',
    topWeight: '最大单项占比',
    currentDrawdown: '当前回撤',
    stopLoss: '止损提醒',
    aiRisk: 'AI 风险信号',
    riskUnavailable: '风险数据暂不可用，持仓快照仍可正常查看。',
    advancedTitle: '高级账本',
    advancedDescription: '交易录入、资金流水、分红拆股、券商 CSV、账户管理和精确成本核算。默认收起，日常查看不需要维护这些内容。',
    advancedOpen: '展开高级账本',
    advancedClose: '收起高级账本',
    advancedLoading: '正在加载高级账本…',
    noAccounts: '当前没有持仓账户。请展开高级账本创建一个账户。',
  },
  en: {
    documentTitle: 'Personal Portfolio - DSA',
    title: 'Personal portfolio',
    description: 'Focus on assets, returns, allocation, and risk. Detailed ledgers and broker tools stay in the advanced section.',
    account: 'Account view',
    allAccounts: 'All accounts',
    costMethod: 'Cost method',
    fifo: 'FIFO',
    avg: 'Average cost',
    refresh: 'Refresh',
    refreshing: 'Refreshing',
    totalAssets: 'Total assets',
    stockValue: 'Stock market value',
    availableCash: 'Available cash',
    holdingProfit: 'Unrealized P/L',
    fundTitle: 'Fund holdings',
    fundBadge: 'Quick entry in M2',
    fundAmount: 'Fund value',
    fundProfit: 'Holding profit',
    fundReturn: 'Holding return',
    fundPosition: 'Allocation',
    fundEmptyTitle: 'Fund data is not connected yet',
    fundEmptyDescription: 'M1 does not fabricate fund data. M2 will add fund types, holding value, target allocation, and card-based quick entry.',
    stockTitle: 'Stock holdings',
    stockCount: '{count} positions',
    noStockTitle: 'No stock holdings',
    noStockDescription: 'Enter trades or import a broker CSV from the advanced ledger to populate this table.',
    accountColumn: 'Account',
    code: 'Code',
    quantity: 'Quantity',
    avgCost: 'Avg cost',
    currentPrice: 'Current price',
    marketValue: 'Market value',
    profit: 'Unrealized P/L',
    returnPct: 'Return',
    riskTitle: 'Personal risk overview',
    topWeight: 'Largest position',
    currentDrawdown: 'Current drawdown',
    stopLoss: 'Stop-loss alerts',
    aiRisk: 'AI risk signals',
    riskUnavailable: 'Risk data is temporarily unavailable. The portfolio snapshot is still available.',
    advancedTitle: 'Advanced ledger',
    advancedDescription: 'Trade entry, cash ledger, dividends and splits, broker CSV, account management, and exact cost accounting. Collapsed by default.',
    advancedOpen: 'Open advanced ledger',
    advancedClose: 'Close advanced ledger',
    advancedLoading: 'Loading advanced ledger…',
    noAccounts: 'No portfolio account exists. Open the advanced ledger to create one.',
  },
} as const;

function formatCount(template: string, count: number): string {
  return template.replace('{count}', String(count));
}

const PersonalPortfolioPage: React.FC = () => {
  const { language } = useUiLanguage();
  const text = TEXT[language];
  const [accounts, setAccounts] = useState<PortfolioAccountItem[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<AccountOption>('all');
  const [costMethod, setCostMethod] = useState<PortfolioCostMethod>('fifo');
  const [snapshot, setSnapshot] = useState<PortfolioSnapshotResponse | null>(null);
  const [risk, setRisk] = useState<PortfolioRiskResponse | null>(null);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [riskWarning, setRiskWarning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  useEffect(() => {
    document.title = text.documentTitle;
  }, [text.documentTitle, advancedOpen]);

  const accountId = selectedAccount === 'all' ? undefined : selectedAccount;

  const loadAccounts = useCallback(async () => {
    const response = await portfolioApi.getAccounts(false);
    const nextAccounts = response.accounts || [];
    setAccounts(nextAccounts);
    setSelectedAccount((current) => {
      if (current === 'all') return current;
      return nextAccounts.some((item) => item.id === current) ? current : 'all';
    });
  }, []);

  const loadOverview = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setRiskWarning(false);
    try {
      const nextSnapshot = await portfolioApi.getSnapshot({ accountId, costMethod });
      setSnapshot(nextSnapshot);
      try {
        const nextRisk = await portfolioApi.getRisk({ accountId, costMethod });
        setRisk(nextRisk);
      } catch {
        setRisk(null);
        setRiskWarning(true);
      }
    } catch (loadError) {
      setSnapshot(null);
      setRisk(null);
      setError(getParsedApiError(loadError));
    } finally {
      setIsLoading(false);
    }
  }, [accountId, costMethod]);

  useEffect(() => {
    void loadAccounts().catch((loadError) => setError(getParsedApiError(loadError)));
  }, [loadAccounts]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const stockRows = useMemo<StockPositionRow[]>(() => (
    (snapshot?.accounts || []).flatMap((account) => (
      (account.positions || []).map((position) => ({
        ...position,
        accountId: account.accountId,
        accountName: account.accountName,
      }))
    ))
  ), [snapshot]);

  const currency = snapshot?.currency || 'CNY';
  const stopLossCount = (risk?.stopLoss?.triggeredCount || 0) + (risk?.stopLoss?.nearCount || 0);

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      await loadAccounts();
      await loadOverview();
    } catch (refreshError) {
      setError(getParsedApiError(refreshError));
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen space-y-5 p-4 md:p-6" data-testid="personal-portfolio-workbench">
      <section className="space-y-3">
        <div>
          <h1 className="text-xl font-semibold text-foreground md:text-2xl">{text.title}</h1>
          <p className="mt-1 text-xs leading-6 text-secondary md:text-sm">{text.description}</p>
        </div>

        <div className="grid gap-2 rounded-2xl border border-white/10 bg-white/[0.02] p-3 md:grid-cols-[minmax(0,1fr)_220px_auto] md:items-end">
          <label className="space-y-1 text-xs text-secondary">
            <span>{text.account}</span>
            <select
              className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm text-foreground"
              value={String(selectedAccount)}
              onChange={(event) => setSelectedAccount(event.target.value === 'all' ? 'all' : Number(event.target.value))}
            >
              <option value="all">{text.allAccounts}</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>{account.name}</option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-xs text-secondary">
            <span>{text.costMethod}</span>
            <select
              className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm text-foreground"
              value={costMethod}
              onChange={(event) => setCostMethod(event.target.value as PortfolioCostMethod)}
            >
              <option value="fifo">{text.fifo}</option>
              <option value="avg">{text.avg}</option>
            </select>
          </label>
          <button
            type="button"
            className="btn-secondary flex h-11 items-center justify-center gap-2 px-4 text-sm"
            disabled={isLoading}
            onClick={() => void handleRefresh()}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} aria-hidden="true" />
            {isLoading ? text.refreshing : text.refresh}
          </button>
        </div>
      </section>

      {error ? <ApiErrorAlert error={error} onDismiss={() => setError(null)} /> : null}
      {accounts.length === 0 && !isLoading ? (
        <InlineAlert variant="warning" message={text.noAccounts} />
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="portfolio summary">
        <Card variant="gradient" padding="md">
          <p className="text-xs text-secondary">{text.totalAssets}</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{formatMoney(snapshot?.totalEquity, currency)}</p>
        </Card>
        <Card variant="gradient" padding="md">
          <p className="text-xs text-secondary">{text.stockValue}</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{formatMoney(snapshot?.totalMarketValue, currency)}</p>
        </Card>
        <Card variant="gradient" padding="md">
          <p className="text-xs text-secondary">{text.availableCash}</p>
          <p className="mt-2 text-xl font-semibold text-foreground">{formatMoney(snapshot?.totalCash, currency)}</p>
        </Card>
        <Card variant="gradient" padding="md">
          <p className="text-xs text-secondary">{text.holdingProfit}</p>
          <p className={`mt-2 text-xl font-semibold ${(snapshot?.unrealizedPnl || 0) >= 0 ? 'text-success' : 'text-danger'}`}>
            {formatMoney(snapshot?.unrealizedPnl, currency)}
          </p>
        </Card>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-foreground">{text.fundTitle}</h2>
          <span className="rounded-full border border-cyan/30 bg-cyan/10 px-3 py-1 text-xs text-cyan">{text.fundBadge}</span>
        </div>
        <Card className="overflow-hidden" padding="md">
          <div className="rounded-2xl border border-cyan/15 bg-gradient-to-br from-cyan/10 via-transparent to-transparent p-4">
            <p className="text-xs text-secondary">{text.fundAmount}</p>
            <p className="mt-2 text-3xl font-semibold text-foreground">--</p>
            <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
              <div><p className="text-secondary">{text.fundProfit}</p><p className="mt-1 font-medium text-foreground">--</p></div>
              <div><p className="text-secondary">{text.fundReturn}</p><p className="mt-1 font-medium text-foreground">--</p></div>
              <div><p className="text-secondary">{text.fundPosition}</p><p className="mt-1 font-medium text-foreground">--</p></div>
            </div>
          </div>
          <EmptyState
            title={text.fundEmptyTitle}
            description={text.fundEmptyDescription}
            className="mt-3 border-none bg-transparent px-3 py-5 shadow-none"
          />
        </Card>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-foreground">{text.stockTitle}</h2>
          <span className="text-xs text-secondary">{formatCount(text.stockCount, stockRows.length)}</span>
        </div>
        <Card padding="md">
          {stockRows.length === 0 ? (
            <EmptyState
              title={text.noStockTitle}
              description={text.noStockDescription}
              className="border-none bg-transparent px-4 py-8 shadow-none"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-[820px] w-full text-sm">
                <thead className="border-b border-white/10 text-xs text-secondary">
                  <tr>
                    <th className="py-2 pr-3 text-left">{text.accountColumn}</th>
                    <th className="py-2 pr-3 text-left">{text.code}</th>
                    <th className="py-2 pr-3 text-right">{text.quantity}</th>
                    <th className="py-2 pr-3 text-right">{text.avgCost}</th>
                    <th className="py-2 pr-3 text-right">{text.currentPrice}</th>
                    <th className="py-2 pr-3 text-right">{text.marketValue}</th>
                    <th className="py-2 pr-3 text-right">{text.profit}</th>
                    <th className="py-2 text-right">{text.returnPct}</th>
                  </tr>
                </thead>
                <tbody>
                  {stockRows.map((row) => (
                    <tr key={`${row.accountId}-${row.market}-${row.symbol}`} className="border-b border-white/5">
                      <td className="py-3 pr-3 text-secondary">{row.accountName}</td>
                      <td className="py-3 pr-3 font-mono text-foreground">{row.symbol}</td>
                      <td className="py-3 pr-3 text-right">{row.quantity.toFixed(2)}</td>
                      <td className="py-3 pr-3 text-right">{row.avgCost.toFixed(4)}</td>
                      <td className="py-3 pr-3 text-right">{formatPositionPrice(row)}</td>
                      <td className="py-3 pr-3 text-right">{formatPositionMoney(row.marketValueBase, row)}</td>
                      <td className={`py-3 pr-3 text-right ${row.unrealizedPnlBase >= 0 ? 'text-success' : 'text-danger'}`}>
                        {formatPositionMoney(row.unrealizedPnlBase, row)}
                      </td>
                      <td className={`py-3 text-right ${(row.unrealizedPnlPct || 0) >= 0 ? 'text-success' : 'text-danger'}`}>
                        {formatSignedPct(row.unrealizedPnlPct)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">{text.riskTitle}</h2>
        {riskWarning ? <InlineAlert variant="warning" message={text.riskUnavailable} /> : null}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Card padding="md"><p className="text-xs text-secondary">{text.topWeight}</p><p className="mt-2 text-lg font-semibold text-foreground">{formatPct(risk?.concentration?.topWeightPct)}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.currentDrawdown}</p><p className="mt-2 text-lg font-semibold text-foreground">{formatPct(risk?.drawdown?.currentDrawdownPct)}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.stopLoss}</p><p className="mt-2 text-lg font-semibold text-foreground">{stopLossCount}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.aiRisk}</p><p className="mt-2 text-lg font-semibold text-foreground">{risk?.decisionSignalRisk?.total ?? 0}</p></Card>
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-3">
        <button
          type="button"
          className="flex w-full items-center justify-between gap-4 rounded-xl px-2 py-2 text-left"
          aria-expanded={advancedOpen}
          onClick={() => setAdvancedOpen((current) => !current)}
        >
          <span>
            <span className="block font-semibold text-foreground">{text.advancedTitle}</span>
            <span className="mt-1 block text-xs leading-5 text-secondary">{text.advancedDescription}</span>
          </span>
          <span className="flex shrink-0 items-center gap-2 text-xs text-cyan">
            {advancedOpen ? text.advancedClose : text.advancedOpen}
            {advancedOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </span>
        </button>
        {advancedOpen ? (
          <div className="mt-3 border-t border-white/10 pt-3" data-testid="advanced-ledger-content">
            <Suspense fallback={<div className="px-4 py-8 text-center text-sm text-secondary">{text.advancedLoading}</div>}>
              <AdvancedPortfolioLedger />
            </Suspense>
          </div>
        ) : null}
      </section>
    </div>
  );
};

export default PersonalPortfolioPage;
