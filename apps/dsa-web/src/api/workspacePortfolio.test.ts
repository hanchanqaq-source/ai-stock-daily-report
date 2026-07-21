import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiClientMock = vi.hoisted(() => ({
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock('./index', () => ({ default: apiClientMock }));

import { workspacePortfolioApi } from './workspacePortfolio';

describe('workspacePortfolioApi fund watchlist', () => {
  beforeEach(() => vi.clearAllMocks());

  it('uses the current-user local fund watchlist endpoints for create, update, and remove', async () => {
    const item = { id: 'fund-watch-1', code: '000001', name: '测试基金', notes: '等待观察' };

    await workspacePortfolioApi.createFundWatchlistItem('user-a', item);
    await workspacePortfolioApi.updateFundWatchlistItem('user-a', item);
    await workspacePortfolioApi.removeFundWatchlistItem('user-a', item.id);

    expect(apiClientMock.post).toHaveBeenCalledWith(
      '/api/v1/workspace-portfolio/users/user-a/fund-watchlist',
      { id: 'fund-watch-1', code: '000001', name: '测试基金', notes: '等待观察' },
    );
    expect(apiClientMock.patch).toHaveBeenCalledWith(
      '/api/v1/workspace-portfolio/users/user-a/fund-watchlist/fund-watch-1',
      { id: 'fund-watch-1', code: '000001', name: '测试基金', notes: '等待观察' },
    );
    expect(apiClientMock.delete).toHaveBeenCalledWith(
      '/api/v1/workspace-portfolio/users/user-a/fund-watchlist/fund-watch-1',
    );
  });
});
