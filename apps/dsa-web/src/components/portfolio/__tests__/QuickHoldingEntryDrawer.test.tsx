import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PortfolioUserProvider, usePortfolioUsers } from '../../../contexts/PortfolioUserContext';
import { UiLanguageProvider } from '../../../contexts/UiLanguageContext';
import { QuickHoldingEntryDrawer } from '../QuickHoldingEntryDrawer';

const HoldingsProbe = () => {
  const { activeHoldings } = usePortfolioUsers();
  return (
    <div>
      <span data-testid="fund-count">{activeHoldings.funds.length}</span>
      <span data-testid="stock-count">{activeHoldings.stocks.length}</span>
    </div>
  );
};

function renderDrawer(initialMode: 'manual' | 'screenshot' = 'manual') {
  render(
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <HoldingsProbe />
        <QuickHoldingEntryDrawer isOpen initialMode={initialMode} onClose={() => undefined} />
      </PortfolioUserProvider>
    </UiLanguageProvider>,
  );
}

describe('QuickHoldingEntryDrawer', () => {
  it('adds a fund holding to the current user', () => {
    renderDrawer();

    fireEvent.change(screen.getByPlaceholderText('如 017811'), { target: { value: '017811' } });
    fireEvent.change(screen.getByText('持有金额').parentElement!.querySelector('input')!, { target: { value: '10000' } });
    fireEvent.click(screen.getByRole('button', { name: '确认添加持仓' }));

    expect(screen.getByTestId('fund-count')).toHaveTextContent('1');
    expect(screen.getByText('已添加到 本人 的基金持仓。')).toBeInTheDocument();
  });

  it('shows the screenshot preview and confirmation area', () => {
    renderDrawer('screenshot');

    expect(screen.getByText('识别结果确认区')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '等待识别服务接入' })).toBeDisabled();
  });
});
