import { beforeEach, describe, expect, it } from 'vitest';
import {
  WORKSPACE_CENTER_STORAGE_KEY,
  centerFromPath,
  isStockAskRoute,
  readRememberedCenter,
  rememberCenter,
} from '../workspaceCenter';

describe('workspaceCenter', () => {
  beforeEach(() => localStorage.clear());

  it('derives only explicit stock and fund workspace routes', () => {
    expect(centerFromPath('/stocks/portfolio')).toBe('stocks');
    expect(centerFromPath('/funds/industry-cycle')).toBe('funds');
    expect(centerFromPath('/settings')).toBeNull();
  });

  it('remembers the last center without changing the default', () => {
    expect(readRememberedCenter()).toBe('stocks');
    rememberCenter('funds');
    expect(localStorage.getItem(WORKSPACE_CENTER_STORAGE_KEY)).toBe('funds');
    expect(readRememberedCenter()).toBe('funds');
  });

  it('treats both the new and legacy paths as stock chat routes', () => {
    expect(isStockAskRoute('/stocks/ask')).toBe(true);
    expect(isStockAskRoute('/chat')).toBe(true);
    expect(isStockAskRoute('/funds/ask')).toBe(false);
  });
});
