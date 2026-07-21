import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePortfolioUsers } from '../../contexts/PortfolioUserContext';
import FundWatchlistPanel from './FundWatchlistPanel';

vi.mock('../../contexts/PortfolioUserContext', () => ({
  usePortfolioUsers: vi.fn(),
}));

const addFundWatchlistItem = vi.fn();
const updateFundWatchlistItem = vi.fn();
const removeFundWatchlistItem = vi.fn();
const mockedUsePortfolioUsers = vi.mocked(usePortfolioUsers);

function setContext(items: Array<{ id: string; code: string; name: string; notes?: string }> = []) {
  mockedUsePortfolioUsers.mockReturnValue({
    activeUser: { id: 'self', name: '本人', isPrimary: true },
    activeFundWatchlist: items,
    persistenceStatus: 'ready',
    addFundWatchlistItem,
    updateFundWatchlistItem,
    removeFundWatchlistItem,
  } as unknown as ReturnType<typeof usePortfolioUsers>);
}

describe('FundWatchlistPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    addFundWatchlistItem.mockResolvedValue(true);
    updateFundWatchlistItem.mockResolvedValue(true);
    removeFundWatchlistItem.mockResolvedValue(true);
    setContext();
  });

  it('adds a manually entered fund without automatically loading external data', async () => {
    render(<FundWatchlistPanel language="zh" />);

    expect(screen.getByText('当前用户还没有基金自选')).toBeInTheDocument();
    const submit = screen.getByRole('button', { name: '加入自选' });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '000001abc' } });
    fireEvent.change(screen.getByLabelText('基金名称'), { target: { value: '  测试   基金  ' } });
    fireEvent.change(screen.getByLabelText('备注（可选）'), { target: { value: ' 等待回调 ' } });
    expect(screen.getByLabelText('基金代码')).toHaveValue('000001');
    fireEvent.click(submit);

    await waitFor(() => expect(addFundWatchlistItem).toHaveBeenCalledWith({
      code: '000001',
      name: '测试 基金',
      notes: '等待回调',
    }));
    expect(screen.getByText('基金已加入自选。')).toBeInTheDocument();
  });

  it('rejects duplicate codes inside the active user watchlist', async () => {
    setContext([{ id: 'watch-1', code: '000001', name: '已有基金' }]);
    render(<FundWatchlistPanel language="zh" />);

    fireEvent.change(screen.getByLabelText('基金代码'), { target: { value: '000001' } });
    fireEvent.change(screen.getByLabelText('基金名称'), { target: { value: '重复基金' } });
    fireEvent.click(screen.getByRole('button', { name: '加入自选' }));

    expect(await screen.findByText('该基金已经在当前用户的自选中。')).toBeInTheDocument();
    expect(addFundWatchlistItem).not.toHaveBeenCalled();
  });

  it('edits an item and requires a second action before removing it', async () => {
    setContext([{ id: 'watch-1', code: '000001', name: '原基金', notes: '原备注' }]);
    render(<FundWatchlistPanel language="zh" />);

    fireEvent.click(screen.getByRole('button', { name: '编辑' }));
    expect(screen.getByLabelText('基金代码')).toHaveValue('000001');
    fireEvent.change(screen.getByLabelText('基金名称'), { target: { value: '新基金名称' } });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
    await waitFor(() => expect(updateFundWatchlistItem).toHaveBeenCalledWith({
      id: 'watch-1', code: '000001', name: '新基金名称', notes: '原备注',
    }));

    fireEvent.click(screen.getByRole('button', { name: '移出自选' }));
    expect(removeFundWatchlistItem).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '确认移出' }));
    await waitFor(() => expect(removeFundWatchlistItem).toHaveBeenCalledWith('watch-1'));
  });
});
