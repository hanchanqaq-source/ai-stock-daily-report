import type React from 'react';
import { createContext, useCallback, useContext, useMemo, useState } from 'react';

export type PortfolioUserProfile = {
  id: string;
  name: string;
  isPrimary: boolean;
};

type PortfolioUserContextValue = {
  users: PortfolioUserProfile[];
  activeUser: PortfolioUserProfile;
  activeUserId: string;
  addUser: (name: string) => PortfolioUserProfile | null;
  renameUser: (id: string, name: string) => boolean;
  removeUser: (id: string) => boolean;
  setActiveUserId: (id: string) => void;
};

const PRIMARY_USER: PortfolioUserProfile = {
  id: 'self',
  name: '本人',
  isPrimary: true,
};

const fallbackContext: PortfolioUserContextValue = {
  users: [PRIMARY_USER],
  activeUser: PRIMARY_USER,
  activeUserId: PRIMARY_USER.id,
  addUser: () => null,
  renameUser: () => false,
  removeUser: () => false,
  setActiveUserId: () => undefined,
};

const PortfolioUserContext = createContext<PortfolioUserContextValue | null>(null);

function normalizeName(name: string): string {
  return name.trim().replace(/\s+/g, ' ').slice(0, 24);
}

export const PortfolioUserProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [users, setUsers] = useState<PortfolioUserProfile[]>([PRIMARY_USER]);
  const [activeUserId, setActiveUserIdState] = useState(PRIMARY_USER.id);

  const activeUser = users.find((user) => user.id === activeUserId) ?? users[0] ?? PRIMARY_USER;

  const setActiveUserId = useCallback((id: string) => {
    setActiveUserIdState((current) => (users.some((user) => user.id === id) ? id : current));
  }, [users]);

  const addUser = useCallback((name: string): PortfolioUserProfile | null => {
    const normalized = normalizeName(name);
    if (!normalized) return null;

    const nextUser: PortfolioUserProfile = {
      id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name: normalized,
      isPrimary: false,
    };
    setUsers((current) => [...current, nextUser]);
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
    setActiveUserIdState((current) => (current === id ? PRIMARY_USER.id : current));
    return true;
  }, [users]);

  const value = useMemo<PortfolioUserContextValue>(() => ({
    users,
    activeUser,
    activeUserId: activeUser.id,
    addUser,
    renameUser,
    removeUser,
    setActiveUserId,
  }), [activeUser, addUser, removeUser, renameUser, setActiveUserId, users]);

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
