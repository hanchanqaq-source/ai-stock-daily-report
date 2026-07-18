import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PortfolioUserProvider, usePortfolioUsers } from '../../../contexts/PortfolioUserContext';
import { UiLanguageProvider } from '../../../contexts/UiLanguageContext';
import { QuickHoldingEntryDrawer } from '../QuickHoldingEntryDrawer';

const HoldingsProbe = () => {
  const { activeFundHoldings, activeStockHoldings } = usePortfolioUsers();
  return (
    <div>
      <span data-testid="fund-count">{activeFundHoldings.length}</span>
      <span data-testid="stock-count">{activeStockHoldings.length}</span>
    </div>
  );
};

function renderDrawer(initialMode: 'manual' | 'screenshot' = 'manual', fixedAssetType?: 'fund' | 'stock') {
  render(
    <UiLanguageProvider>
      <PortfolioUserProvider>
        <HoldingsProbe />
        <QuickHoldingEntryDrawer isOpen initialMode={initialMode} fixedAssetType={fixedAssetType} onClose={() => undefined} />
      </PortfolioUserProvider>
    </UiLanguageProvider>,
  );
}

describe('QuickHoldingEntryDrawer', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('adds a fund holding to the current user', () => {
    renderDrawer();

    fireEvent.change(screen.getByPlaceholderText('如 017811'), { target: { value: '017811' } });
    fireEvent.change(screen.getByText('持有金额').parentElement!.querySelector('input')!, { target: { value: '10000' } });
    fireEvent.click(screen.getByRole('button', { name: '确认添加持仓' }));

    expect(screen.getByTestId('fund-count')).toHaveTextContent('1');
    expect(screen.getByText('已添加到 本人 的基金持仓。')).toBeInTheDocument();
  });

  it('requires a local screenshot preview before manual confirmation entry', () => {
    renderDrawer('screenshot');

    expect(screen.getByText('本机截图确认区')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '按截图手动填写并确认' })).toBeDisabled();
    expect(screen.getByText('支持 PNG、JPG、WEBP；当前只在本机预览，不上传。')).toBeInTheDocument();
  });

  it('opens the manually confirmed form only after a local screenshot is selected', () => {
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:holding-preview'), revokeObjectURL: vi.fn() });
    renderDrawer('screenshot', 'fund');

    const file = new File(['image'], 'fund-holdings.png', { type: 'image/png' });
    fireEvent.change(screen.getByLabelText('选择持仓截图文件'), { target: { files: [file] } });

    expect(screen.getByAltText('持仓截图预览')).toBeInTheDocument();
    const confirmButton = screen.getByRole('button', { name: '按截图手动填写并确认' });
    expect(confirmButton).toBeEnabled();
    fireEvent.click(confirmButton);

    expect(screen.getByText('截图待确认录入')).toBeInTheDocument();
    expect(screen.getByText('当前位于基金中心，本次只录入基金持仓。')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('如 017811')).toBeInTheDocument();
  });

  it('locks quick entry to stocks inside the stock center', () => {
    renderDrawer('manual', 'stock');

    expect(screen.getByText('当前位于股票中心，本次只录入股票持仓。')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('如 600519')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '基金' })).not.toBeInTheDocument();
  });

  it('writes a stock-center entry only to the active stock domain', () => {
    renderDrawer('manual', 'stock');

    fireEvent.change(screen.getByPlaceholderText('如 600519'), { target: { value: '600519' } });
    fireEvent.change(screen.getByText('持有数量').parentElement!.querySelector('input')!, { target: { value: '10' } });
    fireEvent.change(screen.getByText('平均成本').parentElement!.querySelector('input')!, { target: { value: '1500' } });
    fireEvent.click(screen.getByRole('button', { name: '确认添加持仓' }));

    expect(screen.getByTestId('stock-count')).toHaveTextContent('1');
    expect(screen.getByTestId('fund-count')).toHaveTextContent('0');
    expect(screen.getByText('已添加到 本人 的股票持仓。')).toBeInTheDocument();
  });
});
