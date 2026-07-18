import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PortfolioUserProvider, usePortfolioUsers } from '../PortfolioUserContext';

vi.mock('../../api/workspacePortfolio', () => ({
  workspacePortfolioApi: {
    getState: vi.fn().mockResolvedValue({ users: [{ id: 'self', name: '本人', isPrimary: true }], activeUserId: 'self', stockHoldingsByUser: { self: [] }, fundHoldingsByUser: { self: [] } }),
    createUser: vi.fn().mockResolvedValue(undefined), renameUser: vi.fn().mockResolvedValue(undefined), removeUser: vi.fn().mockResolvedValue(undefined),
    setActiveUser: vi.fn().mockResolvedValue({ users: [{ id: 'self', name: '本人', isPrimary: true }], activeUserId: 'self', stockHoldingsByUser: { self: [] }, fundHoldingsByUser: { self: [] } }),
    createStock: vi.fn().mockResolvedValue(undefined), removeStock: vi.fn().mockResolvedValue(undefined),
    createFund: vi.fn().mockResolvedValue(undefined), removeFund: vi.fn().mockResolvedValue(undefined),
  },
}));

const PortfolioStateProbe = () => {
  const {
    activeUser,
    activeUserId,
    activeFundHoldings,
    activeStockHoldings,
    addUser,
    removeUser,
    setActiveUserId,
    addFundHolding,
    addStockHolding,
    removeFundHolding,
    removeStockHolding,
  } = usePortfolioUsers();

  return (
    <div>
      <span data-testid="active-user">{activeUser.name}</span>
      <span data-testid="fund-codes">{activeFundHoldings.map((item) => item.code).join(',')}</span>
      <span data-testid="stock-codes">{activeStockHoldings.map((item) => item.code).join(',')}</span>
      <button type="button" onClick={() => addFundHolding({ code: `F-${activeUser.name}`, name: '基金', amount: 1000, profit: 10 })}>add-fund</button>
      <button type="button" onClick={() => addStockHolding({ code: `S-${activeUser.name}`, name: '股票', quantity: 2, averageCost: 20, securitiesAccount: '测试账户' })}>add-stock</button>
      <button type="button" onClick={() => addUser('家人A')}>add-family</button>
      <button type="button" onClick={() => setActiveUserId('self')}>switch-self</button>
      <button type="button" onClick={() => setActiveUserId('missing-user')}>switch-invalid</button>
      <button type="button" onClick={() => removeUser(activeUserId)}>remove-active</button>
      <button type="button" onClick={() => activeFundHoldings[0] && removeFundHolding(activeFundHoldings[0].id)}>remove-fund</button>
      <button type="button" onClick={() => activeStockHoldings[0] && removeStockHolding(activeStockHoldings[0].id)}>remove-stock</button>
    </div>
  );
};

function renderProbe() {
  render(<PortfolioUserProvider><PortfolioStateProbe /></PortfolioUserProvider>);
}

describe('PortfolioUserContext domain isolation', () => {
  it('keeps stock and fund holdings isolated for every user', () => {
    renderProbe();

    fireEvent.click(screen.getByRole('button', { name: 'add-fund' }));
    fireEvent.click(screen.getByRole('button', { name: 'add-stock' }));
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-本人');
    expect(screen.getByTestId('stock-codes')).toHaveTextContent('S-本人');

    fireEvent.click(screen.getByRole('button', { name: 'add-family' }));
    expect(screen.getByTestId('active-user')).toHaveTextContent('家人A');
    expect(screen.getByTestId('fund-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement();

    fireEvent.click(screen.getByRole('button', { name: 'add-fund' }));
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-家人A');
    expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement();

    fireEvent.click(screen.getByRole('button', { name: 'switch-self' }));
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-本人');
    expect(screen.getByTestId('stock-codes')).toHaveTextContent('S-本人');

    fireEvent.click(screen.getByRole('button', { name: 'remove-stock' }));
    expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('fund-codes')).toHaveTextContent('F-本人');
  });

  it('rejects invalid switches and clears both domains when a secondary user is removed', () => {
    renderProbe();

    fireEvent.click(screen.getByRole('button', { name: 'add-family' }));
    fireEvent.click(screen.getByRole('button', { name: 'add-fund' }));
    fireEvent.click(screen.getByRole('button', { name: 'add-stock' }));
    fireEvent.click(screen.getByRole('button', { name: 'switch-invalid' }));
    expect(screen.getByTestId('active-user')).toHaveTextContent('家人A');

    fireEvent.click(screen.getByRole('button', { name: 'remove-active' }));
    expect(screen.getByTestId('active-user')).toHaveTextContent('本人');
    expect(screen.getByTestId('fund-codes')).toBeEmptyDOMElement();
    expect(screen.getByTestId('stock-codes')).toBeEmptyDOMElement();

    fireEvent.click(screen.getByRole('button', { name: 'remove-active' }));
    expect(screen.getByTestId('active-user')).toHaveTextContent('本人');
  });
});
