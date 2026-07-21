import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { workspacePortfolioApi } from '../../api/workspacePortfolio';
import type { WorkspacePortfolioStateDto } from '../../api/workspacePortfolio';
import { PortfolioUserProvider, usePortfolioUsers } from '../PortfolioUserContext';

vi.mock('../../api/workspacePortfolio', () => ({
  workspacePortfolioApi: {
    getState: vi.fn(),
    createUser: vi.fn(),
    renameUser: vi.fn(),
    removeUser: vi.fn(),
    setActiveUser: vi.fn(),
    createStock: vi.fn(),
    updateStock: vi.fn(),
    removeStock: vi.fn(),
    createFund: vi.fn(),
    updateFund: vi.fn(),
    removeFund: vi.fn(),
    createFundWatchlistItem: vi.fn(),
    updateFundWatchlistItem: vi.fn(),
    removeFundWatchlistItem: vi.fn(),
  },
}));

const PRIMARY_USER = { id: 'self', name: '本人', isPrimary: true };
const api = vi.mocked(workspacePortfolioApi);
let serverState: WorkspacePortfolioStateDto;

function cloneState(state = serverState): WorkspacePortfolioStateDto {
  return JSON.parse(JSON.stringify(state)) as WorkspacePortfolioStateDto;
}

function createServerState(): WorkspacePortfolioStateDto {
  return {
    users: [PRIMARY_USER],
    activeUserId: 'self',
    stockHoldingsByUser: { self: [] },
    fundHoldingsByUser: { self: [] },
    fundWatchlistByUser: { self: [] },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.clearAllMocks();
  serverState = createServerState();
  api.getState.mockImplementation(async () => cloneState());
  api.createUser.mockImplementation(async (user) => {
    serverState.users.push({ ...user, isPrimary: false });
    serverState.stockHoldingsByUser[user.id] = [];
    serverState.fundHoldingsByUser[user.id] = [];
    serverState.fundWatchlistByUser[user.id] = [];
  });
  api.renameUser.mockImplementation(async (id, name) => {
    serverState.users = serverState.users.map((user) => user.id === id ? { ...user, name } : user);
  });
  api.removeUser.mockImplementation(async (id) => {
    serverState.users = serverState.users.filter((user) => user.id !== id);
    delete serverState.stockHoldingsByUser[id];
    delete serverState.fundHoldingsByUser[id];
    delete serverState.fundWatchlistByUser[id];
    if (serverState.activeUserId === id) serverState.activeUserId = 'self';
  });
  api.setActiveUser.mockImplementation(async (id) => {
    serverState.activeUserId = id;
    return cloneState();
  });
  api.createStock.mockImplementation(async (userId, holding) => {
    serverState.stockHoldingsByUser[userId] = [...(serverState.stockHoldingsByUser[userId] ?? []), holding];
  });
  api.updateStock.mockImplementation(async (userId, holding) => {
    serverState.stockHoldingsByUser[userId] = (serverState.stockHoldingsByUser[userId] ?? []).map((item) => item.id === holding.id ? holding : item);
  });
  api.removeStock.mockImplementation(async (userId, id) => {
    serverState.stockHoldingsByUser[userId] = (serverState.stockHoldingsByUser[userId] ?? []).filter((item) => item.id !== id);
  });
  api.createFund.mockImplementation(async (userId, holding) => {
    serverState.fundHoldingsByUser[userId] = [...(serverState.fundHoldingsByUser[userId] ?? []), holding];
  });
  api.updateFund.mockImplementation(async (userId, holding) => {
    serverState.fundHoldingsByUser[userId] = (serverState.fundHoldingsByUser[userId] ?? []).map((item) => item.id === holding.id ? holding : item);
  });
  api.removeFund.mockImplementation(async (userId, id) => {
    serverState.fundHoldingsByUser[userId] = (serverState.fundHoldingsByUser[userId] ?? []).filter((item) => item.id !== id);
  });
  api.createFundWatchlistItem.mockImplementation(async (userId, item) => {
    serverState.fundWatchlistByUser[userId] = [...(serverState.fundWatchlistByUser[userId] ?? []), item];
  });
  api.updateFundWatchlistItem.mockImplementation(async (userId, item) => {
    serverState.fundWatchlistByUser[userId] = (serverState.fundWatchlistByUser[userId] ?? []).map((current) => current.id === item.id ? item : current);
  });
  api.removeFundWatchlistItem.mockImplementation(async (userId, id) => {
    serverState.fundWatchlistByUser[userId] = (serverState.fundWatchlistByUser[userId] ?? []).filter((item) => item.id !== id);
  });
});

const PortfolioStateProbe = () => {
  const {
    activeUser,
    activeUserId,
    activeFundHoldings,
    activeStockHoldings,
    activeFundWatchlist,
    persistenceStatus,
    addUser,
    removeUser,
    setActiveUserId,
    addFundHolding,
    addStockHolding,
    removeFundHolding,
    removeStockHolding,
    addFundWatchlistItem,
    removeFundWatchlistItem,
  } = usePortfolioUsers();

  return (
    <div>
      <span data-testid="active-user">{activeUser.name}</span>
      <span data-testid="fund-codes">{activeFundHoldings.map((item) => item.code).join(',')}</span>
      <span data-testid="stock-codes">{activeStockHoldings.map((item) => item.code).join(',')}</span>
      <span data-testid="fund-watchlist-codes">{activeFundWatchlist.map((item) => item.code).join(',')}</span>
      <span data-testid="persistence-status">{persistenceStatus}</span>
      <button type="button" onClick={() => addFundHolding({ code: `F-${activeUser.name}`, name: '基金', amount: 1000, profit: 10 })}>add-fund</button>
      <button type="button" onClick={() => addStockHolding({ code: `S-${activeUser.name}`, name: '股票', quantity: 2, averageCost: 20, securitiesAccount: '测试账户' })}>add-stock</button>
      <button type="button" onClick={() => void addFundWatchlistItem({ code: activeUser.id === 'self' ? '000001' : '110022', name: `自选-${activeUser.name}` })}>add-fund-watchlist</button>
      <button type="button" onClick={() => addUser('家人A')}>add-family</button>
      <button type="button" onClick={() => setActiveUserId('self')}>switch-self</button>
      <button type="button" onClick={() => setActiveUserId('user-a')}>switch-a</button>
      <button type="button" onClick={() => setActiveUserId('user-b')}>switch-b</button>
      <button type="button" onClick={() => setActiveUserId('missing-user')}>switch-invalid</button>
      <button type="button" onClick={() => removeUser(activeUserId)}>remove-active</button>
      <button type="button" onClick={() => activeFundHoldings[0] && removeFundHolding(activeFundHoldings[0].id)}>remove-fund</button>
      <button type="button" onClick={() => activeStockHoldings[0] && removeStockHolding(activeStockHoldings[0].id)}>remove-stock</button>
      <button type="button" onClick={() => activeFundWatchlist[0] && void removeFundWatchlistItem(activeFundWatchlist[0].id)}>remove-fund-watchlist</button>
    </div>
  );
};

function renderProbe() {
  render(<PortfolioUserProvider><PortfolioStateProbe /></PortfolioUserProvider>);
}

async function waitUntilReady() {
  await waitFor(() => expect(screen.getByTestId('persistence-status')).toHaveTextContent('ready'));
}

describe('PortfolioUserContext persistence consistency', () => {
  it('keeps stock and fund holdings isolated for every user', async () => {
    renderProbe();
    await waitUntilReady();

    fireEvent.click(screen.getByRole('button', { name: 'add-fund' }));
    await waitUntilReady();
    fireEvent.click(screen.getByRole('button', { name: 'add-stock' }));
    await waitUntilReady();
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-本人');
    expect(screen.getByTestId('stock-codes')).toHaveTextContent('S-本人');
    fireEvent.click(screen.getByRole('button', { name: 'add-fund-watchlist' }));
    await waitUntilReady();
    expect(screen.getByTestId('fund-watchlist-codes')).toHaveTextContent('000001');

    fireEvent.click(screen.getByRole('button', { name: 'add-family' }));
    await waitFor(() => expect(screen.getByTestId('active-user')).toHaveTextContent('家人A'));
    await waitUntilReady();
    expect(screen.getByTestId('fund-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('fund-watchlist-codes')).toBeEmptyDOMElement();

    fireEvent.click(screen.getByRole('button', { name: 'add-fund' }));
    await waitUntilReady();
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-家人A');
    expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement();
    fireEvent.click(screen.getByRole('button', { name: 'add-fund-watchlist' }));
    await waitUntilReady();
    expect(screen.getByTestId('fund-watchlist-codes')).toHaveTextContent('110022');

    fireEvent.click(screen.getByRole('button', { name: 'switch-self' }));
    await waitUntilReady();
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-本人');
    expect(screen.getByTestId('stock-codes')).toHaveTextContent('S-本人');
    expect(screen.getByTestId('fund-watchlist-codes')).toHaveTextContent('000001');

    fireEvent.click(screen.getByRole('button', { name: 'remove-fund-watchlist' }));
    await waitUntilReady();
    expect(screen.getByTestId('fund-watchlist-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-本人');

    fireEvent.click(screen.getByRole('button', { name: 'remove-stock' }));
    await waitUntilReady();
    expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('fund-watchlist-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-本人');
  });

  it('rejects invalid switches and clears holdings and watchlists when a secondary user is removed', async () => {
    renderProbe();
    await waitUntilReady();

    fireEvent.click(screen.getByRole('button', { name: 'add-family' }));
    await waitUntilReady();
    fireEvent.click(screen.getByRole('button', { name: 'add-fund' }));
    await waitUntilReady();
    fireEvent.click(screen.getByRole('button', { name: 'add-stock' }));
    await waitUntilReady();
    fireEvent.click(screen.getByRole('button', { name: 'add-fund-watchlist' }));
    await waitUntilReady();
    fireEvent.click(screen.getByRole('button', { name: 'switch-invalid' }));
    expect(screen.getByTestId('active-user')).toHaveTextContent('家人A');

    fireEvent.click(screen.getByRole('button', { name: 'remove-active' }));
    await waitUntilReady();
    expect(screen.getByTestId('active-user')).toHaveTextContent('本人');
    expect(screen.getByTestId('fund-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('fund-watchlist-codes')).toBeEmptyDOMElement();

    fireEvent.click(screen.getByRole('button', { name: 'remove-active' }));
    expect(screen.getByTestId('active-user')).toHaveTextContent('本人');
  });

  it('reloads authoritative server state after a failed optimistic mutation', async () => {
    const failedCreate = deferred<void>();
    api.createStock.mockImplementationOnce(() => failedCreate.promise);
    renderProbe();
    await waitUntilReady();

    fireEvent.click(screen.getByRole('button', { name: 'add-stock' }));
    expect(screen.getByTestId('stock-codes')).toHaveTextContent('S-本人');

    await act(async () => failedCreate.reject(new Error('database unavailable')));
    await waitFor(() => expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement());
    expect(screen.getByTestId('persistence-status')).toHaveTextContent('error');
  });

  it('rolls back a fund watchlist item when local persistence fails', async () => {
    const failedCreate = deferred<void>();
    api.createFundWatchlistItem.mockImplementationOnce(() => failedCreate.promise);
    renderProbe();
    await waitUntilReady();

    fireEvent.click(screen.getByRole('button', { name: 'add-fund-watchlist' }));
    expect(screen.getByTestId('fund-watchlist-codes')).toHaveTextContent('000001');

    await act(async () => failedCreate.reject(new Error('database unavailable')));
    await waitFor(() => expect(screen.getByTestId('fund-watchlist-codes')).toBeEmptyDOMElement());
    expect(screen.getByTestId('persistence-status')).toHaveTextContent('error');
  });

  it('serializes active-user writes so an older request cannot finish after the newer choice', async () => {
    serverState = {
      users: [
        PRIMARY_USER,
        { id: 'user-a', name: '用户A', isPrimary: false },
        { id: 'user-b', name: '用户B', isPrimary: false },
      ],
      activeUserId: 'self',
      stockHoldingsByUser: { self: [], 'user-a': [], 'user-b': [] },
      fundHoldingsByUser: { self: [], 'user-a': [], 'user-b': [] },
      fundWatchlistByUser: { self: [], 'user-a': [], 'user-b': [] },
    };
    const firstResponse = deferred<WorkspacePortfolioStateDto>();
    const secondResponse = deferred<WorkspacePortfolioStateDto>();
    api.setActiveUser
      .mockImplementationOnce(() => firstResponse.promise)
      .mockImplementationOnce(() => secondResponse.promise);
    renderProbe();
    await waitUntilReady();

    fireEvent.click(screen.getByRole('button', { name: 'switch-a' }));
    fireEvent.click(screen.getByRole('button', { name: 'switch-b' }));
    expect(screen.getByTestId('active-user')).toHaveTextContent('用户B');
    await waitFor(() => expect(api.setActiveUser).toHaveBeenCalledTimes(1));
    expect(api.setActiveUser).toHaveBeenLastCalledWith('user-a');

    await act(async () => firstResponse.resolve({ ...cloneState(), activeUserId: 'user-a' }));
    await waitFor(() => expect(api.setActiveUser).toHaveBeenCalledTimes(2));
    expect(api.setActiveUser).toHaveBeenLastCalledWith('user-b');
    expect(screen.getByTestId('active-user')).toHaveTextContent('用户B');

    await act(async () => secondResponse.resolve({ ...cloneState(), activeUserId: 'user-b' }));
    await waitUntilReady();
    expect(screen.getByTestId('active-user')).toHaveTextContent('用户B');
  });
});
