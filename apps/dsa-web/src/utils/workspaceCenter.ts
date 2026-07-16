export type WorkspaceCenter = 'stocks' | 'funds';

export const WORKSPACE_CENTER_STORAGE_KEY = 'dsa_workspace_center';

export function centerFromPath(pathname: string): WorkspaceCenter | null {
  if (pathname === '/funds' || pathname.startsWith('/funds/')) return 'funds';
  if (pathname === '/stocks' || pathname.startsWith('/stocks/')) return 'stocks';
  return null;
}

export function readRememberedCenter(): WorkspaceCenter {
  if (typeof localStorage === 'undefined') return 'stocks';
  return localStorage.getItem(WORKSPACE_CENTER_STORAGE_KEY) === 'funds' ? 'funds' : 'stocks';
}

export function rememberCenter(center: WorkspaceCenter): void {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(WORKSPACE_CENTER_STORAGE_KEY, center);
  }
}

export function isStockAskRoute(pathname: string): boolean {
  return pathname === '/stocks/ask' || pathname === '/chat';
}
