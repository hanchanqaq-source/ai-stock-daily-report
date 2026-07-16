import type React from 'react';
import { createContext, useCallback, useContext, useMemo, useState } from 'react';

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
  addUser: (name: string) => PortfolioUserProfile | null;
  renameUser: (id: string, name: string) => boolean;
  removeUser: (id: string) => boolean;
  setActiveUserId: (id: string) => void;
  addFundHolding: (input: FundHoldingInput) => QuickFundHolding;
  addStockHolding: (input: StockHoldingInput) => QuickStockHolding;
  removeFundHolding: (holdingId: string) => void;
  removeStockHolding: (holdingId: string) => void;
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
  addUser: () => null,
  renameUser: () => false,
  removeUser: () => false,
  setActiveUserId: () => undefined,
  addFundHolding: (input) => ({ ...input, id: 'fallback-fund' }),
  addStockHolding: (input) => ({ ...input, id: 'fallback-stock' }),
  removeFundHolding: () => undefined,
  removeStockHolding: () => undefined,
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

  const activeUser = users.find((user) => user.id === activeUserId) ?? users[0] ?? PRIMARY_USER;
  const activeFundHoldings = fundHoldingsByUser[activeUser.id] ?? EMPTY_FUND_HOLDINGS;
  const activeStockHoldings = stockHoldingsByUser[activeUser.id] ?? EMPTY_STOCK_HOLDINGS;

  const setActiveUserId = useCallback((id: string) => {
    setActiveUserIdState((current) => (users.some((user) => user.id === id) ? id : current));
  }, [users]);

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
    return nextUser;
  }, []);

  const renameUser = useCallback((id: string, name: string): boolean => {
    const normalized = normalizeName(name);
    if (!normalized || !users.some((user) => user.id === id)) return false;

    setUsers((current) => current.map((user) => (
      user.id === id ? { ...user, name: normalized } : user
    )));
    return true;
  }, [users]);

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
    return true;
  }, [users]);

  const addFundHolding = useCallback((input: FundHoldingInput): QuickFundHolding => {
    const holding = { ...input, id: createHoldingId('fund') };
    setFundHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: [...(current[activeUser.id] ?? EMPTY_FUND_HOLDINGS), holding],
    }));
    return holding;
  }, [activeUser.id]);

  const addStockHolding = useCallback((input: StockHoldingInput): QuickStockHolding => {
    const holding = { ...input, id: createHoldingId('stock') };
    setStockHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: [...(current[activeUser.id] ?? EMPTY_STOCK_HOLDINGS), holding],
    }));
    return holding;
  }, [activeUser.id]);

  const removeFundHolding = useCallback((holdingId: string) => {
    setFundHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: (current[activeUser.id] ?? EMPTY_FUND_HOLDINGS).filter((item) => item.id !== holdingId),
    }));
  }, [activeUser.id]);

  const removeStockHolding = useCallback((holdingId: string) => {
    setStockHoldingsByUser((current) => ({
      ...current,
      [activeUser.id]: (current[activeUser.id] ?? EMPTY_STOCK_HOLDINGS).filter((item) => item.id !== holdingId),
    }));
  }, [activeUser.id]);

  const value = useMemo<PortfolioUserContextValue>(() => ({
    users,
    activeUser,
    activeUserId: activeUser.id,
    activeFundHoldings,
    activeStockHoldings,
    addUser,
    renameUser,
    removeUser,
    setActiveUserId,
    addFundHolding,
    addStockHolding,
    removeFundHolding,
    removeStockHolding,
  }), [
    activeFundHoldings,
    activeStockHoldings,
    activeUser,
    addFundHolding,
    addStockHolding,
    addUser,
    removeFundHolding,
    removeStockHolding,
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
