import apiClient from './index';
import { toCamelCase } from './utils';

export type WorkspaceUserDto = { id: string; name: string; isPrimary: boolean };
export type WorkspaceStockHoldingDto = { id: string; code: string; name: string; quantity: number; averageCost: number; securitiesAccount: string; notes?: string };
export type WorkspaceFundHoldingDto = { id: string; code: string; name: string; amount: number; profit: number; targetAllocation?: number; notes?: string };
export type WorkspacePortfolioStateDto = {
  users: WorkspaceUserDto[];
  activeUserId: string;
  stockHoldingsByUser: Record<string, WorkspaceStockHoldingDto[]>;
  fundHoldingsByUser: Record<string, WorkspaceFundHoldingDto[]>;
};
export type WorkspacePortfolioBackupDto = WorkspacePortfolioStateDto & {
  format: 'dsa-workspace-portfolio-backup';
  version: 1;
  exportedAt: string;
};
export type WorkspacePortfolioBackupPreviewDto = {
  users: number;
  stockHoldings: number;
  fundHoldings: number;
  exportedAt: string;
  willReplaceCurrentWorkspace: boolean;
};
export type WorkspacePortfolioRestorePointDto = {
  id: string;
  reason: 'before_import' | 'before_restore';
  createdAt: string;
};
export type WorkspacePortfolioBackupImportResultDto = {
  state: WorkspacePortfolioStateDto;
  restorePointId: string;
};
export type WorkspaceHoldingRecycleItemDto = { id: string; assetType: 'stock' | 'fund'; holding: WorkspaceStockHoldingDto | WorkspaceFundHoldingDto; createdAt: string };
export type WorkspaceHoldingHistoryItemDto = { id: string; assetType: 'stock' | 'fund'; action: 'created' | 'updated' | 'deleted' | 'restored'; holding: WorkspaceStockHoldingDto | WorkspaceFundHoldingDto; previousHolding?: WorkspaceStockHoldingDto | WorkspaceFundHoldingDto; createdAt: string };

const snakeStock = (item: WorkspaceStockHoldingDto) => ({
  id: item.id, code: item.code, name: item.name, quantity: item.quantity,
  average_cost: item.averageCost, securities_account: item.securitiesAccount, notes: item.notes,
});
const snakeFund = (item: WorkspaceFundHoldingDto) => ({
  id: item.id, code: item.code, name: item.name, amount: item.amount, profit: item.profit,
  target_allocation: item.targetAllocation, notes: item.notes,
});

export const workspacePortfolioApi = {
  async getState(): Promise<WorkspacePortfolioStateDto> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/workspace-portfolio');
    return toCamelCase<WorkspacePortfolioStateDto>(response.data);
  },
  async createUser(user: WorkspaceUserDto): Promise<void> {
    await apiClient.post('/api/v1/workspace-portfolio/users', { id: user.id, name: user.name });
  },
  async renameUser(id: string, name: string): Promise<void> {
    await apiClient.patch(`/api/v1/workspace-portfolio/users/${encodeURIComponent(id)}`, { name });
  },
  async removeUser(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/workspace-portfolio/users/${encodeURIComponent(id)}`);
  },
  async setActiveUser(id: string): Promise<WorkspacePortfolioStateDto> {
    const response = await apiClient.put<Record<string, unknown>>(`/api/v1/workspace-portfolio/active-user/${encodeURIComponent(id)}`);
    return toCamelCase<WorkspacePortfolioStateDto>(response.data);
  },
  async createStock(userId: string, holding: WorkspaceStockHoldingDto): Promise<void> {
    await apiClient.post(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/stocks`, snakeStock(holding));
  },
  async removeStock(userId: string, id: string): Promise<void> {
    await apiClient.delete(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/stocks/${encodeURIComponent(id)}`);
  },
  async updateStock(userId: string, holding: WorkspaceStockHoldingDto): Promise<void> {
    await apiClient.patch(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/stocks/${encodeURIComponent(holding.id)}`, snakeStock(holding));
  },
  async createFund(userId: string, holding: WorkspaceFundHoldingDto): Promise<void> {
    await apiClient.post(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/funds`, snakeFund(holding));
  },
  async removeFund(userId: string, id: string): Promise<void> {
    await apiClient.delete(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/funds/${encodeURIComponent(id)}`);
  },
  async updateFund(userId: string, holding: WorkspaceFundHoldingDto): Promise<void> {
    await apiClient.patch(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/funds/${encodeURIComponent(holding.id)}`, snakeFund(holding));
  },
  async exportBackup(): Promise<WorkspacePortfolioBackupDto> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/workspace-portfolio/backup/export');
    return toCamelCase<WorkspacePortfolioBackupDto>(response.data);
  },
  async previewBackup(backup: unknown): Promise<WorkspacePortfolioBackupPreviewDto> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/workspace-portfolio/backup/preview', backup);
    return toCamelCase<WorkspacePortfolioBackupPreviewDto>(response.data);
  },
  async importBackup(backup: unknown): Promise<WorkspacePortfolioBackupImportResultDto> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/workspace-portfolio/backup/import', { backup, confirmed: true });
    return toCamelCase<WorkspacePortfolioBackupImportResultDto>(response.data);
  },
  async listRestorePoints(): Promise<WorkspacePortfolioRestorePointDto[]> {
    const response = await apiClient.get<Record<string, unknown>[]>('/api/v1/workspace-portfolio/backup/restore-points');
    return toCamelCase<WorkspacePortfolioRestorePointDto[]>(response.data);
  },
  async restoreBackup(id: string): Promise<WorkspacePortfolioBackupImportResultDto> {
    const response = await apiClient.post<Record<string, unknown>>(`/api/v1/workspace-portfolio/backup/restore-points/${encodeURIComponent(id)}`, { confirmed: true });
    return toCamelCase<WorkspacePortfolioBackupImportResultDto>(response.data);
  },
  async listRecycleBin(userId: string): Promise<WorkspaceHoldingRecycleItemDto[]> {
    const response = await apiClient.get<Record<string, unknown>[]>(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/recycle-bin`);
    return toCamelCase<WorkspaceHoldingRecycleItemDto[]>(response.data);
  },
  async restoreRecycleEntry(userId: string, id: string): Promise<void> {
    await apiClient.post(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/recycle-bin/${encodeURIComponent(id)}/restore`);
  },
  async listHoldingHistory(userId: string, assetType: 'stock' | 'fund'): Promise<WorkspaceHoldingHistoryItemDto[]> {
    const response = await apiClient.get<Record<string, unknown>[]>(`/api/v1/workspace-portfolio/users/${encodeURIComponent(userId)}/holding-history?asset_type=${assetType}`);
    return toCamelCase<WorkspaceHoldingHistoryItemDto[]>(response.data);
  },
};
