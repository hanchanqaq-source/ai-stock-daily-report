import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, Settings2, UsersRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { portfolioApi } from '../api/portfolio';
import { getParsedApiError, type ParsedApiError } from '../api/error';
import { ApiErrorAlert, Card, EmptyState, InlineAlert } from '../components/common';
import { usePortfolioUsers } from '../contexts/PortfolioUserContext';
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

type AccountOption = 'all' | number;

type StockPositionRow = PortfolioPositionItem & {
  accountId: number;
  accountName: string;
};

const TEXT = {
  zh: {
    documentTitle: '我的持仓分析 - DSA',
    title: '我的持仓分析',
    description: '按用户分别管理基金和股票，重点查看持有金额、收益、仓位和风险。',
    currentUser: '当前用户',
    manageUsers: '管理用户',
    userNotConnectedTitle: '该用户尚未接入持仓数据',
    userNotConnectedDescription: '当前只建立了独立用户档案。M2 接入快速录入后，可为该用户单独添加基金和股票。',
    stockAccountAssets: '证券账户总资产',
    stockValue: '股票持仓市值',
    stockCash: '证券账户可用现金',
    stockProfit: '股票浮动收益',
    fundTitle: '基金持仓分析',
    fundBadge: 'M2 接入快速录入',
    fundAmount: '基金持有金额',
    fundProfit: '持有收益',
    fundReturn: '持有收益率',
    fundPosition: '当前仓位',
    fundEmptyTitle: '基金数据尚未接入',
    fundEmptyDescription: '基金区只做基金持仓、收益、仓位和风险分析，不使用股票资金流水、公司行为或券商 CSV。',
    userFundEmptyTitle: '该用户暂无基金持仓',
    userFundEmptyDescription: 'M2 支持快速录入后，可为当前用户单独添加基金。',
    stockTitle: '股票持仓分析',
    stockCount: '共 {count} 项',
    securitiesAccount: '证券账户',
    allSecuritiesAccounts: '全部证券账户',
    stockCostMethod: '股票成本口径',
    fifo: '先进先出',
    avg: '均价成本',
    refresh: '刷新股票数据',
    refreshing: '刷新中',
    noSecuritiesAccount: '当前没有证券账户，可进入“股票高级管理”创建账户并添加股票。',
    noStockTitle: '暂无股票持仓',
    noStockDescription: '进入“股票高级管理”录入股票交易后，持仓会显示在这里。',
    userStockEmptyTitle: '该用户暂无股票持仓',
    userStockEmptyDescription: 'M2 支持快速录入后，可为当前用户单独添加股票。',
    accountColumn: '证券账户',
    code: '股票代码',
    quantity: '持有数量',
    avgCost: '平均成本',
    currentPrice: '当前价格',
    marketValue: '股票市值',
    profit: '浮动盈亏',
    returnPct: '收益率',
    stockToolsTitle: '股票高级管理',
    stockToolsDescription: '股票专用工具：交易录入、资金流水、公司行为、券商 CSV 和证券账户管理。',
    tradeEntry: '交易录入',
    cashLedger: '资金流水',
    corporateActions: '公司行为',
    brokerCsv: '券商 CSV',
    securitiesAccounts: '证券账户',
    openStockTools: '进入股票高级管理',
    riskTitle: '股票风险概览',
    topWeight: '最大股票占比',
    currentDrawdown: '证券账户回撤',
    stopLoss: '股票止损提醒',
    aiRisk: '股票 AI 风险信号',
    riskUnavailable: '股票风险数据暂不可用，股票持仓快照仍可正常查看。',
  },
  en: {
    documentTitle: 'My Holdings Analysis - DSA',
    title: 'My holdings analysis',
    description: 'Manage funds and stocks separately for each user, focusing on value, return, allocation, and risk.',
    currentUser: 'Current user',
    manageUsers: 'Manage users',
    userNotConnectedTitle: 'Holdings are not connected for this user',
    userNotConnectedDescription: 'This stage only creates a separate profile. M2 quick entry will add funds and stocks for this user.',
    stockAccountAssets: 'Securities account assets',
    stockValue: 'Stock market value',
    stockCash: 'Securities account cash',
    stockProfit: 'Stock unrealized P/L',
    fundTitle: 'Fund holdings analysis',
    fundBadge: 'Quick entry in M2',
    fundAmount: 'Fund value',
    fundProfit: 'Holding profit',
    fundReturn: 'Holding return',
    fundPosition: 'Allocation',
    fundEmptyTitle: 'Fund data is not connected yet',
    fundEmptyDescription: 'The fund area is only for fund holdings, return, allocation, and risk. Stock ledger tools do not appear here.',
    userFundEmptyTitle: 'No fund holdings for this user',
    userFundEmptyDescription: 'M2 quick entry will add funds separately for the current user.',
    stockTitle: 'Stock holdings analysis',
    stockCount: '{count} positions',
    securitiesAccount: 'Securities account',
    allSecuritiesAccounts: 'All securities accounts',
    stockCostMethod: 'Stock cost method',
    fifo: 'FIFO',
    avg: 'Average cost',
    refresh: 'Refresh stock data',
    refreshing: 'Refreshing',
    noSecuritiesAccount: 'No securities account exists. Open Stock advanced management to create one and add stocks.',
    noStockTitle: 'No stock holdings',
    noStockDescription: 'Enter stock trades in Stock advanced management and positions will appear here.',
    userStockEmptyTitle: 'No stock holdings for this user',
    userStockEmptyDescription: 'M2 quick entry will add stocks separately for the current user.',
    accountColumn: 'Securities account',
    code: 'Stock code',
    quantity: 'Quantity',
    avgCost: 'Avg cost',
    currentPrice: 'Current price',
    marketValue: 'Stock value',
    profit: 'Unrealized P/L',
    returnPct: 'Return',
    stockToolsTitle: 'Stock advanced management',
    stockToolsDescription: 'Stock-only tools: trade entry, cash ledger, corporate actions, broker CSV, and securities account management.',
    tradeEntry: 'Trade entry',
    cashLedger: 'Cash ledger',
    corporateActions: 'Corporate actions',
    brokerCsv: 'Broker CSV',
    securitiesAccounts: 'Securities accounts',
    openStockTools: 'Open stock advanced management',
    riskTitle: 'Stock risk overview',
    topWeight: 'Largest stock weight',
    currentDrawdown: 'Securities account drawdown',
    stopLoss: 'Stock stop-loss alerts',
    aiRisk: 'Stock AI risk signals',
    riskUnavailable: 'Stock risk data is temporarily unavailable. The stock snapshot is still available.',
  },
} as const;

function formatCount(template: string, count: number): string {
  return template.replace('{count}', String(count));
}

const PersonalPortfolioPage: React.FC = () => {
  const navigate = useNavigate();
  const { language } = useUiLanguage();
  const { users, activeUser, activeUserId, setActiveUserId } = usePortfolioUsers();
  const text = TEXT[language];
  const isPrimaryUser = activeUser.isPrimary;
  const [accounts, setAccounts] = useState<PortfolioAccountItem[]>([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<AccountOption>('all');
  const [costMethod, setCostMethod] = useState<PortfolioCostMethod>('fifo');
  const [snapshot, setSnapshot] = useState<PortfolioSnapshotResponse | null>(null);
  const [risk, setRisk] = useState<PortfolioRiskResponse | null>(null);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [riskWarning, setRiskWarning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => { document.title = text.documentTitle; }, [text.documentTitle]);

  const accountId = selectedAccount === 'all' ? undefined : selectedAccount;

  const loadAccounts = useCallback(async () => {
    if (!isPrimaryUser) {
      setAccounts([]);
      setSelectedAccount('all');
      setAccountsLoaded(true);
      return;
    }
    setAccountsLoaded(false);
    try {
      const response = await portfolioApi.getAccounts(false);
      const nextAccounts = response.accounts || [];
      setAccounts(nextAccounts);
      setSelectedAccount((current) => (
        current === 'all' || nextAccounts.some((item) => item.id === current) ? current : 'all'
      ));
    } finally {
      setAccountsLoaded(true);
    }
  }, [isPrimaryUser]);

  const loadOverview = useCallback(async () => {
    if (!isPrimaryUser) {
      setSnapshot(null);
      setRisk(null);
      setError(null);
      setRiskWarning(false);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    setRiskWarning(false);
    try {
      const nextSnapshot = await portfolioApi.getSnapshot({ accountId, costMethod });
      setSnapshot(nextSnapshot);
      try {
        setRisk(await portfolioApi.getRisk({ accountId, costMethod }));
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
  }, [accountId, costMethod, isPrimaryUser]);

  useEffect(() => {
    void loadAccounts().catch((loadError) => setError(getParsedApiError(loadError)));
  }, [loadAccounts]);

  useEffect(() => { void loadOverview(); }, [loadOverview]);

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
  const summaryValue = (value: number | null | undefined) => isPrimaryUser ? formatMoney(value, currency) : '--';
  const riskValue = (value: number | null | undefined) => isPrimaryUser ? formatPct(value) : '--';

  const handleRefresh = async () => {
    if (!isPrimaryUser) return;
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
        <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-2">
            <h1 className="text-xl font-semibold text-foreground md:text-2xl">{text.title}</h1>
            <p className="text-xs leading-6 text-secondary md:text-sm">{text.description}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="min-w-[220px] space-y-1 text-xs text-secondary">
              <span>{text.currentUser}</span>
              <select
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm text-foreground"
                value={activeUserId}
                onChange={(event) => setActiveUserId(event.target.value)}
              >
                {users.map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
              </select>
            </label>
            <button type="button" className="btn-secondary flex h-11 items-center justify-center gap-2 px-4 text-sm" onClick={() => navigate('/users')}>
              <UsersRound className="h-4 w-4" aria-hidden="true" />{text.manageUsers}
            </button>
          </div>
        </div>
      </section>

      {!isPrimaryUser ? <InlineAlert variant="info" title={text.userNotConnectedTitle} message={text.userNotConnectedDescription} /> : null}
      {error ? <ApiErrorAlert error={error} onDismiss={() => setError(null)} /> : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="stock portfolio summary">
        <Card variant="gradient" padding="md"><p className="text-xs text-secondary">{text.stockAccountAssets}</p><p className="mt-2 text-xl font-semibold text-foreground">{summaryValue(snapshot?.totalEquity)}</p></Card>
        <Card variant="gradient" padding="md"><p className="text-xs text-secondary">{text.stockValue}</p><p className="mt-2 text-xl font-semibold text-foreground">{summaryValue(snapshot?.totalMarketValue)}</p></Card>
        <Card variant="gradient" padding="md"><p className="text-xs text-secondary">{text.stockCash}</p><p className="mt-2 text-xl font-semibold text-foreground">{summaryValue(snapshot?.totalCash)}</p></Card>
        <Card variant="gradient" padding="md"><p className="text-xs text-secondary">{text.stockProfit}</p><p className={`mt-2 text-xl font-semibold ${(snapshot?.unrealizedPnl || 0) >= 0 ? 'text-success' : 'text-danger'}`}>{summaryValue(snapshot?.unrealizedPnl)}</p></Card>
      </section>

      <section className="space-y-3" data-testid="fund-portfolio-section">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-foreground">{text.fundTitle}</h2>
          <span className="rounded-full border border-cyan/30 bg-cyan/10 px-3 py-1 text-xs text-cyan">{text.fundBadge}</span>
        </div>
        <Card className="overflow-hidden" padding="md">
          <div className="rounded-2xl border border-cyan/15 bg-gradient-to-br from-cyan/10 via-transparent to-transparent p-4">
            <p className="text-xs text-secondary">{text.fundAmount}</p><p className="mt-2 text-3xl font-semibold text-foreground">--</p>
            <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
              <div><p className="text-secondary">{text.fundProfit}</p><p className="mt-1 font-medium text-foreground">--</p></div>
              <div><p className="text-secondary">{text.fundReturn}</p><p className="mt-1 font-medium text-foreground">--</p></div>
              <div><p className="text-secondary">{text.fundPosition}</p><p className="mt-1 font-medium text-foreground">--</p></div>
            </div>
          </div>
          <EmptyState
            title={isPrimaryUser ? text.fundEmptyTitle : text.userFundEmptyTitle}
            description={isPrimaryUser ? text.fundEmptyDescription : text.userFundEmptyDescription}
            className="mt-3 border-none bg-transparent px-3 py-5 shadow-none"
          />
        </Card>
      </section>

      <section className="space-y-3" data-testid="stock-portfolio-section">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="text-base font-semibold text-foreground">{text.stockTitle}</h2><span className="mt-1 block text-xs text-secondary">{formatCount(text.stockCount, stockRows.length)}</span></div>
          <button type="button" disabled={!isPrimaryUser} className="btn-secondary flex items-center gap-2 text-sm" onClick={() => navigate('/portfolio/stock-management')}>
            <Settings2 className="h-4 w-4" aria-hidden="true" />{text.stockToolsTitle}
          </button>
        </div>

        {isPrimaryUser && accounts.length > 0 ? (
          <div className="grid gap-2 rounded-2xl border border-white/10 bg-white/[0.02] p-3 md:grid-cols-[minmax(0,1fr)_220px_auto] md:items-end">
            <label className="space-y-1 text-xs text-secondary">
              <span>{text.securitiesAccount}</span>
              <select className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm text-foreground" value={String(selectedAccount)} onChange={(event) => setSelectedAccount(event.target.value === 'all' ? 'all' : Number(event.target.value))}>
                <option value="all">{text.allSecuritiesAccounts}</option>
                {accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
              </select>
            </label>
            <label className="space-y-1 text-xs text-secondary">
              <span>{text.stockCostMethod}</span>
              <select className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm text-foreground" value={costMethod} onChange={(event) => setCostMethod(event.target.value as PortfolioCostMethod)}>
                <option value="fifo">{text.fifo}</option><option value="avg">{text.avg}</option>
              </select>
            </label>
            <button type="button" className="btn-secondary flex h-11 items-center justify-center gap-2 px-4 text-sm" disabled={isLoading} onClick={() => void handleRefresh()}>
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} aria-hidden="true" />{isLoading ? text.refreshing : text.refresh}
            </button>
          </div>
        ) : null}

        {isPrimaryUser && accountsLoaded && accounts.length === 0 ? <InlineAlert variant="warning" message={text.noSecuritiesAccount} /> : null}

        <Card padding="md">
          {stockRows.length === 0 ? (
            <EmptyState
              title={isPrimaryUser ? text.noStockTitle : text.userStockEmptyTitle}
              description={isPrimaryUser ? text.noStockDescription : text.userStockEmptyDescription}
              className="border-none bg-transparent px-4 py-8 shadow-none"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-[860px] w-full text-sm">
                <thead className="border-b border-white/10 text-xs text-secondary"><tr>
                  <th className="py-2 pr-3 text-left">{text.accountColumn}</th><th className="py-2 pr-3 text-left">{text.code}</th><th className="py-2 pr-3 text-right">{text.quantity}</th><th className="py-2 pr-3 text-right">{text.avgCost}</th><th className="py-2 pr-3 text-right">{text.currentPrice}</th><th className="py-2 pr-3 text-right">{text.marketValue}</th><th className="py-2 pr-3 text-right">{text.profit}</th><th className="py-2 text-right">{text.returnPct}</th>
                </tr></thead>
                <tbody>{stockRows.map((row) => (
                  <tr key={`${row.accountId}-${row.market}-${row.symbol}`} className="border-b border-white/5">
                    <td className="py-3 pr-3 text-secondary">{row.accountName}</td><td className="py-3 pr-3 font-mono text-foreground">{row.symbol}</td><td className="py-3 pr-3 text-right">{row.quantity.toFixed(2)}</td><td className="py-3 pr-3 text-right">{row.avgCost.toFixed(4)}</td><td className="py-3 pr-3 text-right">{formatPositionPrice(row)}</td><td className="py-3 pr-3 text-right">{formatPositionMoney(row.marketValueBase, row)}</td><td className={`py-3 pr-3 text-right ${row.unrealizedPnlBase >= 0 ? 'text-success' : 'text-danger'}`}>{formatPositionMoney(row.unrealizedPnlBase, row)}</td><td className={`py-3 text-right ${(row.unrealizedPnlPct || 0) >= 0 ? 'text-success' : 'text-danger'}`}>{formatSignedPct(row.unrealizedPnlPct)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </Card>

        <Card padding="md">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div><h3 className="font-semibold text-foreground">{text.stockToolsTitle}</h3><p className="mt-1 text-xs leading-5 text-secondary">{text.stockToolsDescription}</p>
              <div className="mt-3 flex flex-wrap gap-2">{[text.tradeEntry, text.cashLedger, text.corporateActions, text.brokerCsv, text.securitiesAccounts].map((item) => <span key={item} className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-secondary">{item}</span>)}</div>
            </div>
            <button type="button" disabled={!isPrimaryUser} className="btn-secondary shrink-0 text-sm" onClick={() => navigate('/portfolio/stock-management')}>{text.openStockTools}</button>
          </div>
        </Card>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">{text.riskTitle}</h2>
        {riskWarning ? <InlineAlert variant="warning" message={text.riskUnavailable} /> : null}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Card padding="md"><p className="text-xs text-secondary">{text.topWeight}</p><p className="mt-2 text-lg font-semibold text-foreground">{riskValue(risk?.concentration?.topWeightPct)}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.currentDrawdown}</p><p className="mt-2 text-lg font-semibold text-foreground">{riskValue(risk?.drawdown?.currentDrawdownPct)}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.stopLoss}</p><p className="mt-2 text-lg font-semibold text-foreground">{isPrimaryUser ? stopLossCount : '--'}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.aiRisk}</p><p className="mt-2 text-lg font-semibold text-foreground">{isPrimaryUser ? risk?.decisionSignalRisk?.total ?? 0 : '--'}</p></Card>
        </div>
      </section>
    </div>
  );
};

export default PersonalPortfolioPage;
