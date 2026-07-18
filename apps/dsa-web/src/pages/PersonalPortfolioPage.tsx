import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ImageUp, Pencil, Plus, RefreshCw, Settings2, Trash2, UsersRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { portfolioApi } from '../api/portfolio';
import { getParsedApiError, type ParsedApiError } from '../api/error';
import { ApiErrorAlert, Card, EmptyState, InlineAlert } from '../components/common';
import { QuickHoldingEntryDrawer } from '../components/portfolio/QuickHoldingEntryDrawer';
import { workspacePortfolioApi, type WorkspaceHoldingHistoryItemDto } from '../api/workspacePortfolio';
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
type EntryMode = 'manual' | 'screenshot';
type PortfolioDomain = 'stock' | 'fund';

type PersonalPortfolioPageProps = {
  domain: PortfolioDomain;
};

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
    addHolding: '添加持仓',
    screenshotRecognition: '截图确认录入',
    userNotConnectedTitle: '该用户尚未接入正式持仓数据',
    userNotConnectedDescription: '可先使用快速录入或截图确认录入添加基金和股票；正式行情和自动识别将在后续阶段接入。',
    stockAccountAssets: '证券账户总资产',
    stockValue: '股票持仓市值',
    stockCash: '证券账户可用现金',
    stockProfit: '股票浮动收益',
    fundTitle: '基金持仓分析',
    fundBadge: '已支持快速录入',
    fundAmount: '基金持有金额',
    fundProfit: '持有收益',
    fundReturn: '持有收益率',
    fundPosition: '当前仓位',
    fundEmptyTitle: '暂无基金持仓',
    fundEmptyDescription: '点击“添加持仓”，输入基金代码或名称、持有金额和收益。',
    fundCode: '基金代码',
    fundName: '基金名称',
    targetAllocation: '目标仓位',
    notes: '备注',
    stockTitle: '股票持仓分析',
    stockCount: '共 {count} 项',
    securitiesAccount: '证券账户',
    allSecuritiesAccounts: '全部证券账户',
    stockCostMethod: '股票成本口径',
    fifo: '先进先出',
    avg: '均价成本',
    refresh: '刷新股票数据',
    refreshing: '刷新中',
    noSecuritiesAccount: '当前没有正式证券账户，可进入“股票高级管理”创建账户。',
    noStockTitle: '暂无股票持仓',
    noStockDescription: '点击“添加持仓”快速录入股票，或进入“股票高级管理”录入正式交易。',
    quickStockTitle: '快速录入股票',
    accountColumn: '证券账户',
    code: '股票代码',
    name: '名称',
    quantity: '持有数量',
    avgCost: '平均成本',
    entryCost: '录入成本',
    currentPrice: '当前价格',
    marketValue: '股票市值',
    profit: '浮动盈亏',
    returnPct: '收益率',
    action: '操作',
    remove: '删除',
    edit: '编辑',
    restoreLatest: '恢复最近删除',
    holdingHistory: '持仓变更历史',
    noHoldingHistory: '当前用户还没有持仓变更记录。',
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
    addHolding: 'Add holding',
    screenshotRecognition: 'Screenshot confirmation',
    userNotConnectedTitle: 'Formal holdings are not connected for this user',
    userNotConnectedDescription: 'Use quick entry or screenshot confirmation first. Formal quotes and automatic recognition will follow.',
    stockAccountAssets: 'Securities account assets',
    stockValue: 'Stock market value',
    stockCash: 'Securities account cash',
    stockProfit: 'Stock unrealized P/L',
    fundTitle: 'Fund holdings analysis',
    fundBadge: 'Quick entry available',
    fundAmount: 'Fund value',
    fundProfit: 'Holding profit',
    fundReturn: 'Holding return',
    fundPosition: 'Allocation',
    fundEmptyTitle: 'No fund holdings',
    fundEmptyDescription: 'Use Add holding to enter a fund code or name, value, and profit.',
    fundCode: 'Fund code',
    fundName: 'Fund name',
    targetAllocation: 'Target allocation',
    notes: 'Notes',
    stockTitle: 'Stock holdings analysis',
    stockCount: '{count} positions',
    securitiesAccount: 'Securities account',
    allSecuritiesAccounts: 'All securities accounts',
    stockCostMethod: 'Stock cost method',
    fifo: 'FIFO',
    avg: 'Average cost',
    refresh: 'Refresh stock data',
    refreshing: 'Refreshing',
    noSecuritiesAccount: 'No formal securities account exists. Open advanced management to create one.',
    noStockTitle: 'No stock holdings',
    noStockDescription: 'Use Add holding for quick entry, or enter formal trades in advanced management.',
    quickStockTitle: 'Quick-entry stocks',
    accountColumn: 'Securities account',
    code: 'Stock code',
    name: 'Name',
    quantity: 'Quantity',
    avgCost: 'Avg cost',
    entryCost: 'Entry cost',
    currentPrice: 'Current price',
    marketValue: 'Stock value',
    profit: 'Unrealized P/L',
    returnPct: 'Return',
    action: 'Action',
    remove: 'Remove',
    edit: 'Edit',
    restoreLatest: 'Restore latest deleted',
    holdingHistory: 'Holding change history',
    noHoldingHistory: 'This user has no holding change records yet.',
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

const PersonalPortfolioPage: React.FC<PersonalPortfolioPageProps> = ({ domain }) => {
  const navigate = useNavigate();
  const { language } = useUiLanguage();
  const {
    users,
    activeUser,
    activeUserId,
    activeFundHoldings,
    activeStockHoldings,
    setActiveUserId,
    removeFundHolding,
    removeStockHolding,
    replaceWorkspaceState,
  } = usePortfolioUsers();
  const text = TEXT[language];
  const showStocks = domain === 'stock';
  const showFunds = domain === 'fund';
  const pageTitle = domain === 'stock'
    ? (language === 'zh' ? '股票持仓' : 'Stock holdings')
    : (language === 'zh' ? '基金持仓' : 'Fund holdings');
  const pageDescription = domain === 'stock'
    ? (language === 'zh' ? '只显示当前用户的股票持仓、证券账户和股票风险。' : 'Shows stock holdings, securities accounts, and stock risk for the active user only.')
    : (language === 'zh' ? '只显示当前用户的基金持仓；真实净值、行业穿透和周期分析将在后续阶段接入。' : 'Shows fund holdings for the active user only. Real NAV, exposure, and cycle analysis follow later.');
  const isPrimaryUser = activeUser.isPrimary;
  const [entryMode, setEntryMode] = useState<EntryMode>('manual');
  const [entryOpen, setEntryOpen] = useState(false);
  const [editingHolding, setEditingHolding] = useState<
    | { assetType: 'fund'; holding: typeof activeFundHoldings[number] }
    | { assetType: 'stock'; holding: typeof activeStockHoldings[number] }
    | null
  >(null);
  const [accounts, setAccounts] = useState<PortfolioAccountItem[]>([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<AccountOption>('all');
  const [costMethod, setCostMethod] = useState<PortfolioCostMethod>('fifo');
  const [snapshot, setSnapshot] = useState<PortfolioSnapshotResponse | null>(null);
  const [risk, setRisk] = useState<PortfolioRiskResponse | null>(null);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [riskWarning, setRiskWarning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [holdingHistory, setHoldingHistory] = useState<WorkspaceHoldingHistoryItemDto[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => { document.title = `${pageTitle} - DSA`; }, [pageTitle]);

  const accountId = selectedAccount === 'all' ? undefined : selectedAccount;

  const loadAccounts = useCallback(async () => {
    if (!showStocks || !isPrimaryUser) {
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
  }, [isPrimaryUser, showStocks]);

  const loadOverview = useCallback(async () => {
    if (!showStocks || !isPrimaryUser) {
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
  }, [accountId, costMethod, isPrimaryUser, showStocks]);

  useEffect(() => {
    void loadAccounts().catch((loadError) => setError(getParsedApiError(loadError)));
  }, [loadAccounts]);

  useEffect(() => { void loadOverview(); }, [loadOverview]);

  const loadHoldingHistory = useCallback(async () => {
    setHoldingHistory(await workspacePortfolioApi.listHoldingHistory(activeUser.id));
  }, [activeUser.id]);

  useEffect(() => { if (historyOpen) void loadHoldingHistory().catch(() => setHoldingHistory([])); }, [historyOpen, loadHoldingHistory]);

  const stockRows = useMemo<StockPositionRow[]>(() => (
    (snapshot?.accounts || []).flatMap((account) => (
      (account.positions || []).map((position) => ({
        ...position,
        accountId: account.accountId,
        accountName: account.accountName,
      }))
    ))
  ), [snapshot]);

  const fundSummary = useMemo(() => {
    const amount = activeFundHoldings.reduce((total, item) => total + item.amount, 0);
    const profit = activeFundHoldings.reduce((total, item) => total + item.profit, 0);
    const cost = amount - profit;
    return { amount, profit, returnPct: cost > 0 ? (profit / cost) * 100 : null };
  }, [activeFundHoldings]);

  const currency = snapshot?.currency || 'CNY';
  const stopLossCount = (risk?.stopLoss?.triggeredCount || 0) + (risk?.stopLoss?.nearCount || 0);
  const summaryValue = (value: number | null | undefined) => isPrimaryUser ? formatMoney(value, currency) : '--';
  const riskValue = (value: number | null | undefined) => isPrimaryUser ? formatPct(value) : '--';
  const totalStockCount = stockRows.length + activeStockHoldings.length;

  const openEntry = (mode: EntryMode) => {
    setEditingHolding(null);
    setEntryMode(mode);
    setEntryOpen(true);
  };

  const openEdit = (holding: typeof activeFundHoldings[number] | typeof activeStockHoldings[number], assetType: PortfolioDomain) => {
    setEditingHolding(assetType === 'fund' ? { assetType, holding: holding as typeof activeFundHoldings[number] } : { assetType, holding: holding as typeof activeStockHoldings[number] });
    setEntryMode('manual'); setEntryOpen(true);
  };

  const confirmRemove = (holdingId: string, assetType: PortfolioDomain, name: string) => {
    if (!window.confirm(`确认删除“${name}”吗？删除后可通过“恢复最近删除”找回。`)) return;
    if (assetType === 'fund') removeFundHolding(holdingId); else removeStockHolding(holdingId);
  };
  const restoreLatestDeleted = async () => {
    const entries = await workspacePortfolioApi.listRecycleBin(activeUser.id);
    if (!entries[0]) return;
    await workspacePortfolioApi.restoreRecycleEntry(activeUser.id, entries[0].id);
    replaceWorkspaceState(await workspacePortfolioApi.getState());
    if (historyOpen) await loadHoldingHistory();
  };

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
            <h1 className="text-xl font-semibold text-foreground md:text-2xl">{pageTitle}</h1>
            <p className="text-xs leading-6 text-secondary md:text-sm">{pageDescription}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
            <label className="min-w-[220px] space-y-1 text-xs text-secondary">
              <span>{text.currentUser}</span>
              <select className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm text-foreground" value={activeUserId} onChange={(event) => setActiveUserId(event.target.value)}>
                {users.map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
              </select>
            </label>
            <button type="button" className="btn-primary flex h-11 items-center justify-center gap-2 px-4 text-sm" onClick={() => openEntry('manual')}>
              <Plus className="h-4 w-4" aria-hidden="true" />{text.addHolding}
            </button>
            <button type="button" className="btn-secondary flex h-11 items-center justify-center gap-2 px-4 text-sm" onClick={() => openEntry('screenshot')}>
              <ImageUp className="h-4 w-4" aria-hidden="true" />{text.screenshotRecognition}
            </button>
            <button type="button" className="btn-secondary flex h-11 items-center justify-center gap-2 px-4 text-sm" onClick={() => navigate('/users')}>
              <UsersRound className="h-4 w-4" aria-hidden="true" />{text.manageUsers}
            </button>
          </div>
        </div>
      </section>

      {!isPrimaryUser ? <InlineAlert variant="info" title={text.userNotConnectedTitle} message={text.userNotConnectedDescription} /> : null}
      <div className="flex flex-wrap justify-end gap-2"><button type="button" className="btn-secondary text-xs" onClick={() => void restoreLatestDeleted()}>{text.restoreLatest}</button><button type="button" className="btn-secondary text-xs" onClick={() => setHistoryOpen((current) => !current)}>{text.holdingHistory}</button></div>
      {historyOpen ? <Card padding="md"><div className="space-y-2"><h2 className="text-sm font-semibold text-foreground">{text.holdingHistory}</h2>{holdingHistory.length ? holdingHistory.map((entry) => <div key={entry.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border/60 px-3 py-2 text-xs"><span className="text-foreground">{entry.assetType === 'fund' ? '基金' : '股票'} · {entry.holding.name}</span><span className="text-secondary">{({ created: '新增', updated: '编辑', deleted: '删除', restored: '恢复' } as Record<string, string>)[entry.action]} · {new Date(entry.createdAt).toLocaleString()}</span></div>) : <p className="text-sm text-secondary">{text.noHoldingHistory}</p>}</div></Card> : null}
      {showStocks && error ? <ApiErrorAlert error={error} onDismiss={() => setError(null)} /> : null}

      {showStocks ? <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="stock portfolio summary">
        <Card variant="gradient" padding="md"><p className="text-xs text-secondary">{text.stockAccountAssets}</p><p className="mt-2 text-xl font-semibold text-foreground">{summaryValue(snapshot?.totalEquity)}</p></Card>
        <Card variant="gradient" padding="md"><p className="text-xs text-secondary">{text.stockValue}</p><p className="mt-2 text-xl font-semibold text-foreground">{summaryValue(snapshot?.totalMarketValue)}</p></Card>
        <Card variant="gradient" padding="md"><p className="text-xs text-secondary">{text.stockCash}</p><p className="mt-2 text-xl font-semibold text-foreground">{summaryValue(snapshot?.totalCash)}</p></Card>
        <Card variant="gradient" padding="md"><p className="text-xs text-secondary">{text.stockProfit}</p><p className={`mt-2 text-xl font-semibold ${(snapshot?.unrealizedPnl || 0) >= 0 ? 'text-success' : 'text-danger'}`}>{summaryValue(snapshot?.unrealizedPnl)}</p></Card>
      </section> : null}

      {showFunds ? <section className="space-y-3" data-testid="fund-portfolio-section">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-foreground">{text.fundTitle}</h2>
          <span className="rounded-full border border-cyan/30 bg-cyan/10 px-3 py-1 text-xs text-cyan">{text.fundBadge}</span>
        </div>
        <Card className="overflow-hidden" padding="md">
          <div className="rounded-2xl border border-cyan/15 bg-gradient-to-br from-cyan/10 via-transparent to-transparent p-4">
            <p className="text-xs text-secondary">{text.fundAmount}</p><p className="mt-2 text-3xl font-semibold text-foreground">{activeFundHoldings.length ? formatMoney(fundSummary.amount) : '--'}</p>
            <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
              <div><p className="text-secondary">{text.fundProfit}</p><p className="mt-1 font-medium text-foreground">{activeFundHoldings.length ? formatMoney(fundSummary.profit) : '--'}</p></div>
              <div><p className="text-secondary">{text.fundReturn}</p><p className="mt-1 font-medium text-foreground">{fundSummary.returnPct == null ? '--' : formatSignedPct(fundSummary.returnPct)}</p></div>
              <div><p className="text-secondary">{text.fundPosition}</p><p className="mt-1 font-medium text-foreground">--</p></div>
            </div>
          </div>
          {activeFundHoldings.length === 0 ? (
            <EmptyState title={text.fundEmptyTitle} description={text.fundEmptyDescription} className="mt-3 border-none bg-transparent px-3 py-5 shadow-none" />
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-[760px] w-full text-sm">
                <thead className="border-b border-white/10 text-xs text-secondary"><tr>
                  <th className="py-2 pr-3 text-left">{text.fundCode}</th><th className="py-2 pr-3 text-left">{text.fundName}</th><th className="py-2 pr-3 text-right">{text.fundAmount}</th><th className="py-2 pr-3 text-right">{text.fundProfit}</th><th className="py-2 pr-3 text-right">{text.targetAllocation}</th><th className="py-2 text-right">{text.action}</th>
                </tr></thead>
                <tbody>{activeFundHoldings.map((item) => (
                  <tr key={item.id} className="border-b border-white/5">
                    <td className="py-3 pr-3 font-mono text-foreground">{item.code || '--'}</td><td className="py-3 pr-3 text-foreground">{item.name}</td><td className="py-3 pr-3 text-right">{formatMoney(item.amount)}</td><td className={`py-3 pr-3 text-right ${item.profit >= 0 ? 'text-success' : 'text-danger'}`}>{formatMoney(item.profit)}</td><td className="py-3 pr-3 text-right">{item.targetAllocation == null ? '--' : `${item.targetAllocation.toFixed(1)}%`}</td><td className="py-3 text-right"><span className="inline-flex gap-3"><button type="button" className="inline-flex items-center gap-1 text-xs text-cyan" onClick={() => openEdit(item, 'fund')}><Pencil className="h-3.5 w-3.5" />{text.edit}</button><button type="button" className="inline-flex items-center gap-1 text-xs text-danger" onClick={() => confirmRemove(item.id, 'fund', item.name)}><Trash2 className="h-3.5 w-3.5" />{text.remove}</button></span></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </Card>
      </section> : null}

      {showStocks ? <section className="space-y-3" data-testid="stock-portfolio-section">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="text-base font-semibold text-foreground">{text.stockTitle}</h2><span className="mt-1 block text-xs text-secondary">{formatCount(text.stockCount, totalStockCount)}</span></div>
          <button type="button" disabled={!isPrimaryUser} className="btn-secondary flex items-center gap-2 text-sm" onClick={() => navigate('/stocks/portfolio/manage')}>
            <Settings2 className="h-4 w-4" aria-hidden="true" />{text.stockToolsTitle}
          </button>
        </div>

        {activeStockHoldings.length > 0 ? (
          <Card padding="md">
            <h3 className="mb-3 font-semibold text-foreground">{text.quickStockTitle}</h3>
            <div className="overflow-x-auto">
              <table className="min-w-[820px] w-full text-sm">
                <thead className="border-b border-white/10 text-xs text-secondary"><tr>
                  <th className="py-2 pr-3 text-left">{text.accountColumn}</th><th className="py-2 pr-3 text-left">{text.code}</th><th className="py-2 pr-3 text-left">{text.name}</th><th className="py-2 pr-3 text-right">{text.quantity}</th><th className="py-2 pr-3 text-right">{text.avgCost}</th><th className="py-2 pr-3 text-right">{text.entryCost}</th><th className="py-2 text-right">{text.action}</th>
                </tr></thead>
                <tbody>{activeStockHoldings.map((item) => (
                  <tr key={item.id} className="border-b border-white/5">
                    <td className="py-3 pr-3 text-secondary">{item.securitiesAccount}</td><td className="py-3 pr-3 font-mono text-foreground">{item.code || '--'}</td><td className="py-3 pr-3 text-foreground">{item.name}</td><td className="py-3 pr-3 text-right">{item.quantity.toFixed(2)}</td><td className="py-3 pr-3 text-right">{item.averageCost.toFixed(4)}</td><td className="py-3 pr-3 text-right">{formatMoney(item.quantity * item.averageCost)}</td><td className="py-3 text-right"><span className="inline-flex gap-3"><button type="button" className="inline-flex items-center gap-1 text-xs text-cyan" onClick={() => openEdit(item, 'stock')}><Pencil className="h-3.5 w-3.5" />{text.edit}</button><button type="button" className="inline-flex items-center gap-1 text-xs text-danger" onClick={() => confirmRemove(item.id, 'stock', item.name)}><Trash2 className="h-3.5 w-3.5" />{text.remove}</button></span></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </Card>
        ) : null}

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
            activeStockHoldings.length === 0 ? <EmptyState title={text.noStockTitle} description={text.noStockDescription} className="border-none bg-transparent px-4 py-8 shadow-none" /> : <InlineAlert variant="info" message="快速录入股票已显示在上方；接入行情后再计算当前价格、市值和收益。" />
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
            <button type="button" disabled={!isPrimaryUser} className="btn-secondary shrink-0 text-sm" onClick={() => navigate('/stocks/portfolio/manage')}>{text.openStockTools}</button>
          </div>
        </Card>
      </section> : null}

      {showStocks ? <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">{text.riskTitle}</h2>
        {riskWarning ? <InlineAlert variant="warning" message={text.riskUnavailable} /> : null}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Card padding="md"><p className="text-xs text-secondary">{text.topWeight}</p><p className="mt-2 text-lg font-semibold text-foreground">{riskValue(risk?.concentration?.topWeightPct)}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.currentDrawdown}</p><p className="mt-2 text-lg font-semibold text-foreground">{riskValue(risk?.drawdown?.currentDrawdownPct)}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.stopLoss}</p><p className="mt-2 text-lg font-semibold text-foreground">{isPrimaryUser ? stopLossCount : '--'}</p></Card>
          <Card padding="md"><p className="text-xs text-secondary">{text.aiRisk}</p><p className="mt-2 text-lg font-semibold text-foreground">{isPrimaryUser ? risk?.decisionSignalRisk?.total ?? 0 : '--'}</p></Card>
        </div>
      </section> : null}

      <QuickHoldingEntryDrawer
        isOpen={entryOpen}
        initialMode={entryMode}
        fixedAssetType={domain}
        editingHolding={editingHolding}
        onClose={() => { setEntryOpen(false); setEditingHolding(null); }}
      />
    </div>
  );
};

export default PersonalPortfolioPage;
