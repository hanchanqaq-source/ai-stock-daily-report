import type React from 'react';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { workspacePortfolioApi } from '../api/workspacePortfolio';
import type { WorkspacePortfolioStateDto } from '../api/workspacePortfolio';

export type PortfolioUserProfile = {
  id: string;
  name: string;
  isPrimary: boolean;
};

export type QuickFundHolding = {
  id: string;
  code: string;
  name: string;
  amount: number;
  profit: number;
  targetAllocation?: number;
  notes?: string;
};

export type QuickStockHolding = {
  id: string;
  code: string;
  name: string;
  quantity: number;
  averageCost: number;
  securitiesAccount: string;
  notes?: string;
};

type FundHoldingInput = Omit<QuickFundHolding, 'id'>;
type StockHoldingInput = Omit<QuickStockHolding, 'id'>;

type PortfolioUserContextValue = {
  users: PortfolioUserProfile[];
  activeUser: PortfolioUserProfile;
  activeUserId: string;
  activeFundHoldings: readonly QuickFundHolding[];
  activeStockHoldings: readonly QuickStockHolding[];
  persistenceStatus: 'loading' | 'ready' | 'error';
  addUser: (name: string) => PortfolioUserProfile | null;
  renameUser: (id: string, name: string) => boolean;
  removeUser: (id: string) => boolean;
  setActiveUserId: (id: string) => void;
  addFundHolding: (input: FundHoldingInput) => QuickFundHolding;
  addStockHolding: (input: StockHoldingInput) => QuickStockHolding;
  removeFundHolding: (holdingId: string) => void;
  removeStockHolding: (holdingId: string) => void;
  updateFundHolding: (holding: QuickFundHolding) => Promise<boolean>;
  updateStockHolding: (holding: QuickStockHolding) => Promise<boolean>;
  replaceWorkspaceState: (state: WorkspacePortfolioStateDto) => void;
};

const PRIMARY_USER: PortfolioUserProfile = {
  id: 'self',
  name: '本人',
  isPrimary: true,
};

const EMPTY_FUND_HOLDINGS: readonly QuickFundHolding[] = [];
const EMPTY_STOCK_HOLDINGS: readonly QuickStockHolding[] = [];

const fallbackContext: PortfolioUserContextValue = {
  users: [PRIMARY_USER],
  activeUser: PRIMARY_USER,
  activeUserId: PRIMARY_USER.id,
  activeFundHoldings: EMPTY_FUND_HOLDINGS,
  activeStockHoldings: EMPTY_STOCK_HOLDINGS,
  persistenceStatus: 'ready',
  addUser: () => null,
  renameUser: () => false,
  removeUser: () => false,
  setActiveUserId: () => undefined,
  addFundHolding: (input) => ({ ...input, id: 'fallback-fund' }),
  addStockHolding: (input) => ({ ...input, id: 'fallback-stock' }),
  removeFundHolding: () => undefined,
  removeStockHolding: () => undefined,
  updateFundHolding: async () => false,
  updateStockHolding: async () => false,
  replaceWorkspaceState: () => undefined,
};

const PortfolioUserContext = createContext<PortfolioUserContextValue | null>(null);

function normalizeName(name: string): string {
  return name.trim().replace(/\s+/g, ' ').slice(0, 24);
}

function createHoldingId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export const PortfolioUserProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [users, setUsers] = useState<PortfolioUserProfile[]>([PRIMARY_USER]);
  const [activeUserId, setActiveUserIdState] = useState(PRIMARY_USER.id);
  const [fundHoldingsByUser, setFundHoldingsByUser] = useState<Record<string, readonly QuickFundHolding[]>>({
    [PRIMARY_USER.id]: EMPTY_FUND_HOLDINGS,
  });
  const [stockHoldingsByUser, setStockHoldingsByUser] = useState<Record<string, readonly QuickStockHolding[]>>({
    [PRIMARY_USER.id]: EMPTY_STOCK_HOLDINGS,
  });
  const [persistenceStatus, setPersistenceStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const requestSeq = useRef(0);
  const mutationQueue = useRef<Promise<void>>(Promise.resolve());

  const applyWorkspaceState = useCallback((state: WorkspacePortfolioStateDto) => {
    const nextUsers = state.users.length ? state.users : [PRIMARY_USER];
    setUsers(nextUsers);
    setFundHoldingsByUser(state.fundHoldingsByUser);
    setStockHoldingsByUser(state.stockHoldingsByUser);
    setActiveUserIdState(nextUsers.some((user) => user.id === state.activeUserId) ? state.activeUserId : PRIMARY_USER.id);
  }, []);

  const refreshFromServer = useCallback(async (requestId: number): Promise<boolean> => {
    const state = await workspacePortfolioApi.getState();
    if (requestId !== requestSeq.current) return false;
    applyWorkspaceState(state);
    return true;
  }, [applyWorkspaceState]);

  const runMutation = useCallback(async (
    operation: () => Promise<void | WorkspacePortfolioStateDto>,
  ): Promise<boolean> => {
    const requestId = ++requestSeq.current;
    setPersistenceStatus('loading');
    const pendingOperation = mutationQueue.current.then(() => operation());
    mutationQueue.current = pendingOperation.then(() => undefined, () => undefined);
    try {
      const state = await pendingOperation;
      if (requestId !== requestSeq.current) return true;
      if (state) applyWorkspaceState(state);
      else await refreshFromServer(requestId);
      if (requestId === requestSeq.current) setPersistenceStatus('ready');
      return true;
    } catch {
      if (requestId !== requestSeq.current) return false;
      try {
        await refreshFromServer(requestId);
      } catch {
        // Keep the visible error state if both the mutation and reconciliation fail.
      }
      if (requestId === requestSeq.current) setPersistenceStatus('error');
      return false;
    }
  }, [applyWorkspaceState, refreshFromServer]);

  const replaceWorkspaceState = useCallback((state: WorkspacePortfolioStateDto) => {
    requestSeq.current += 1;
    applyWorkspaceState(state);
    setPersistenceStatus('ready');
  }, [applyWorkspaceState]);

  useEffect(() => {
    let active = true;
    const requestId = ++requestSeq.current;
    workspacePortfolioApi.getState().then((state) => {
      if (!active || requestId !== requestSeq.current) return;
      applyWorkspaceState(state);
      setPersistenceStatus('ready');
    }).catch(() => {
      if (active && requestId === requestSeq.current) setPersistenceStatus('error');
    });
    return () => { active = false; };
  }, [applyWorkspaceState]);

  const activeUser = users.find((user) => user.id === activeUserId) ?? users[0] ?? PRIMARY_USER;
  const activeFundHoldings = fundHoldingsByUser[activeUser.id] ?? EMPTY_FUND_HOLDINGS;
  const activeStockHoldings = stockHoldingsByUser[activeUser.id] ?? EMPTY_STOCK_HOLDINGS;

  const setActiveUserId = useCallback((id: string) => {
    if (!users.some((user) => user.id === id)) return;
    setActiveUserIdState(id);
    void runMutation(() => workspacePortfolioApi.setActiveUser(id));
  }, [runMutation, users]);

  const addUser = useCallback((name: string): PortfolioUserProfile | null => {
    const normalized = normalizeName(name);
    if (!normalized) return null;

    const nextUser: PortfolioUserProfile = {
      id: createHoldingId('user'),
      name: normalized,
      isPrimary: false,
    };
    setUsers((current) => [...current, nextUser]);
    setFundHoldingsByUser((current) => ({ ...current, [nextUser.id]: EMPTY_FUND_HOLDINGS }));
    setStockHoldingsByUser((current) => ({ ...current, [nextUser.id]: EMPTY_STOCK_HOLDINGS }));
    setActiveUserIdState(nextUser.id);
    void runMutation(async () => {
      await workspacePortfolioApi.createUser(nextUser);
      return workspacePortfolioApi.setActiveUser(nextUser.id);
    });
    return nextUser;
  }, [runMutation]);

  const renameUser = useCallback((id: string, name: string): boolean => {
    const normalized = normalizeName(name);
    if (!normalized || !users.some((user) => user.id === id)) return false;

    setUsers((current) => current.map((user) => (
      user.id === id ? { ...user, name: normalized } : user
    )));
    void runMutation(() => workspacePortfolioApi.renameUser(id, normalized));
    return true;
  }, [runMutation, users]);

  const removeUser = useCallback((id: string): boolean => {
    const target = users.find((user) => user.id === id);
    if (!target || target.isPrimary) return false;

    setUsers((current) => current.filter((user) => user.id !== id));
    setFundHoldingsByUser((current) => {
      const next = { ...current };
      delete next[id];
      return next;
    });
    setStockHoldingsByUser((current) => {
      const next = { ...current };
      delete next[id];
      return next;
    });
    setActiveUserIdState((current) => (current === id ? PRIMARY_USER.id : current));
    void runMutation(() => workspacePortfolioApi.removeUser(id));
    return true;
  }, [runMutation, users]);

  const addFundHolding = useCallback((input: FundHoldingInput): QuickFundHolding => {
    const holding = { ...input, id: createHoldingId('fund') };
    setFundHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: [...(current[activeUser.id] ?? EMPTY_FUND_HOLDINGS), holding],
    }));
    void runMutation(() => workspacePortfolioApi.createFund(activeUser.id, holding));
    return holding;
  }, [activeUser.id, runMutation]);

  const addStockHolding = useCallback((input: StockHoldingInput): QuickStockHolding => {
    const holding = { ...input, id: createHoldingId('stock') };
    setStockHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: [...(current[activeUser.id] ?? EMPTY_STOCK_HOLDINGS), holding],
    }));
    void runMutation(() => workspacePortfolioApi.createStock(activeUser.id, holding));
    return holding;
  }, [activeUser.id, runMutation]);

  const removeFundHolding = useCallback((holdingId: string) => {
    setFundHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: (current[activeUser.id] ?? EMPTY_FUND_HOLDINGS).filter((item) => item.id !== holdingId),
    }));
    void runMutation(() => workspacePortfolioApi.removeFund(activeUser.id, holdingId));
  }, [activeUser.id, runMutation]);

  const removeStockHolding = useCallback((holdingId: string) => {
    setStockHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: (current[activeUser.id] ?? EMPTY_STOCK_HOLDINGS).filter((item) => item.id !== holdingId),
    }));
    void runMutation(() => workspacePortfolioApi.removeStock(activeUser.id, holdingId));
  }, [activeUser.id, runMutation]);

  const updateFundHolding = useCallback(async (holding: QuickFundHolding): Promise<boolean> => {
    if (!(fundHoldingsByUser[activeUser.id] ?? []).some((item) => item.id === holding.id)) return false;
    return runMutation(() => workspacePortfolioApi.updateFund(activeUser.id, holding));
  }, [activeUser.id, fundHoldingsByUser, runMutation]);

  const updateStockHolding = useCallback(async (holding: QuickStockHolding): Promise<boolean> => {
    if (!(stockHoldingsByUser[activeUser.id] ?? []).some((item) => item.id === holding.id)) return false;
    return runMutation(() => workspacePortfolioApi.updateStock(activeUser.id, holding));
  }, [activeUser.id, runMutation, stockHoldingsByUser]);

  const value = useMemo<PortfolioUserContextValue>(() => ({
    users,
    activeUser,
    activeUserId: activeUser.id,
    activeFundHoldings,
    activeStockHoldings,
    persistenceStatus,
    addUser,
    renameUser,
    removeUser,
    setActiveUserId,
    addFundHolding,
    addStockHolding,
    removeFundHolding,
    removeStockHolding,
    updateFundHolding,
    updateStockHolding,
    replaceWorkspaceState,
  }), [
    activeFundHoldings,
    activeStockHoldings,
    persistenceStatus,
    activeUser,
    addFundHolding,
    addStockHolding,
    addUser,
    removeFundHolding,
    removeStockHolding,
    updateFundHolding,
    updateStockHolding,
    replaceWorkspaceState,
    removeUser,
    renameUser,
    setActiveUserId,
    users,
  ]);

  return (
    <PortfolioUserContext.Provider value={value}>
      {children}
    </PortfolioUserContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components -- hook is co-located with its provider
export function usePortfolioUsers(): PortfolioUserContextValue {
  return useContext(PortfolioUserContext) ?? fallbackContext;
}
