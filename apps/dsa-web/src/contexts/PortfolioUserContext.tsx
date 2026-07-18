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
  const localMutationStarted = useRef(false);

  const persist = useCallback((operation: Promise<void>) => {
    operation.then(() => setPersistenceStatus('ready')).catch(() => setPersistenceStatus('error'));
  }, []);

  const replaceWorkspaceState = useCallback((state: WorkspacePortfolioStateDto) => {
    localMutationStarted.current = true;
    const nextUsers = state.users.length ? state.users : [PRIMARY_USER];
    setUsers(nextUsers);
    setFundHoldingsByUser(state.fundHoldingsByUser);
    setStockHoldingsByUser(state.stockHoldingsByUser);
    setActiveUserIdState(nextUsers.some((user) => user.id === state.activeUserId) ? state.activeUserId : PRIMARY_USER.id);
    setPersistenceStatus('ready');
  }, []);

  useEffect(() => {
    let active = true;
    workspacePortfolioApi.getState().then((state) => {
      if (!active || localMutationStarted.current) return;
      setUsers(state.users.length ? state.users : [PRIMARY_USER]);
      setFundHoldingsByUser(state.fundHoldingsByUser);
      setStockHoldingsByUser(state.stockHoldingsByUser);
      setActiveUserIdState(state.users.some((user) => user.id === state.activeUserId) ? state.activeUserId : PRIMARY_USER.id);
      setPersistenceStatus('ready');
    }).catch(() => {
      if (active) setPersistenceStatus('error');
    });
    return () => { active = false; };
  }, []);

  const activeUser = users.find((user) => user.id === activeUserId) ?? users[0] ?? PRIMARY_USER;
  const activeFundHoldings = fundHoldingsByUser[activeUser.id] ?? EMPTY_FUND_HOLDINGS;
  const activeStockHoldings = stockHoldingsByUser[activeUser.id] ?? EMPTY_STOCK_HOLDINGS;

  const setActiveUserId = useCallback((id: string) => {
    if (!users.some((user) => user.id === id)) return;
    setActiveUserIdState(id);
    persist(workspacePortfolioApi.setActiveUser(id).then(replaceWorkspaceState));
  }, [persist, replaceWorkspaceState, users]);

  const addUser = useCallback((name: string): PortfolioUserProfile | null => {
    const normalized = normalizeName(name);
    if (!normalized) return null;

    const nextUser: PortfolioUserProfile = {
      id: createHoldingId('user'),
      name: normalized,
      isPrimary: false,
    };
    localMutationStarted.current = true;
    setUsers((current) => [...current, nextUser]);
    setFundHoldingsByUser((current) => ({ ...current, [nextUser.id]: EMPTY_FUND_HOLDINGS }));
    setStockHoldingsByUser((current) => ({ ...current, [nextUser.id]: EMPTY_STOCK_HOLDINGS }));
    setActiveUserIdState(nextUser.id);
    persist(workspacePortfolioApi.createUser(nextUser).then(() => workspacePortfolioApi.setActiveUser(nextUser.id)).then(replaceWorkspaceState));
    return nextUser;
  }, [persist, replaceWorkspaceState]);

  const renameUser = useCallback((id: string, name: string): boolean => {
    const normalized = normalizeName(name);
    if (!normalized || !users.some((user) => user.id === id)) return false;

    localMutationStarted.current = true;
    setUsers((current) => current.map((user) => (
      user.id === id ? { ...user, name: normalized } : user
    )));
    persist(workspacePortfolioApi.renameUser(id, normalized));
    return true;
  }, [persist, users]);

  const removeUser = useCallback((id: string): boolean => {
    const target = users.find((user) => user.id === id);
    if (!target || target.isPrimary) return false;

    localMutationStarted.current = true;
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
    persist(workspacePortfolioApi.removeUser(id));
    return true;
  }, [persist, users]);

  const addFundHolding = useCallback((input: FundHoldingInput): QuickFundHolding => {
    const holding = { ...input, id: createHoldingId('fund') };
    localMutationStarted.current = true;
    setFundHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: [...(current[activeUser.id] ?? EMPTY_FUND_HOLDINGS), holding],
    }));
    persist(workspacePortfolioApi.createFund(activeUser.id, holding));
    return holding;
  }, [activeUser.id, persist]);

  const addStockHolding = useCallback((input: StockHoldingInput): QuickStockHolding => {
    const holding = { ...input, id: createHoldingId('stock') };
    localMutationStarted.current = true;
    setStockHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: [...(current[activeUser.id] ?? EMPTY_STOCK_HOLDINGS), holding],
    }));
    persist(workspacePortfolioApi.createStock(activeUser.id, holding));
    return holding;
  }, [activeUser.id, persist]);

  const removeFundHolding = useCallback((holdingId: string) => {
    localMutationStarted.current = true;
    setFundHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: (current[activeUser.id] ?? EMPTY_FUND_HOLDINGS).filter((item) => item.id !== holdingId),
    }));
    persist(workspacePortfolioApi.removeFund(activeUser.id, holdingId));
  }, [activeUser.id, persist]);

  const removeStockHolding = useCallback((holdingId: string) => {
    localMutationStarted.current = true;
    setStockHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: (current[activeUser.id] ?? EMPTY_STOCK_HOLDINGS).filter((item) => item.id !== holdingId),
    }));
    persist(workspacePortfolioApi.removeStock(activeUser.id, holdingId));
  }, [activeUser.id, persist]);

  const updateFundHolding = useCallback(async (holding: QuickFundHolding): Promise<boolean> => {
    if (!(fundHoldingsByUser[activeUser.id] ?? []).some((item) => item.id === holding.id)) return false;
    try {
      await workspacePortfolioApi.updateFund(activeUser.id, holding);
      localMutationStarted.current = true;
      setFundHoldingsByUser((current) => ({ ...current, [activeUser.id]: (current[activeUser.id] ?? EMPTY_FUND_HOLDINGS).map((item) => item.id === holding.id ? holding : item) }));
      setPersistenceStatus('ready');
      return true;
    } catch { setPersistenceStatus('error'); return false; }
  }, [activeUser.id, fundHoldingsByUser]);

  const updateStockHolding = useCallback(async (holding: QuickStockHolding): Promise<boolean> => {
    if (!(stockHoldingsByUser[activeUser.id] ?? []).some((item) => item.id === holding.id)) return false;
    try {
      await workspacePortfolioApi.updateStock(activeUser.id, holding);
      localMutationStarted.current = true;
      setStockHoldingsByUser((current) => ({ ...current, [activeUser.id]: (current[activeUser.id] ?? EMPTY_STOCK_HOLDINGS).map((item) => item.id === holding.id ? holding : item) }));
      setPersistenceStatus('ready');
      return true;
    } catch { setPersistenceStatus('error'); return false; }
  }, [activeUser.id, stockHoldingsByUser]);

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
