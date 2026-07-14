import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const apiClientMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}));

vi.mock('./index', () => ({ default: apiClientMock }));

import { systemConfigApi } from './systemConfig';
import type { DesktopCredentialBridge } from './desktopCredentialStore';

type DesktopTestWindow = Window & {
  dsaDesktop?: DesktopCredentialBridge;
};

function installDesktopBridge(bridge: DesktopCredentialBridge) {
  Object.defineProperty(window, 'dsaDesktop', {
    value: bridge,
    configurable: true,
    writable: true,
  });
}

describe('systemConfigApi desktop credential separation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    delete (window as DesktopTestWindow).dsaDesktop;
  });

  it('overlays sensitive configured state from Electron without reading a plaintext value', async () => {
    apiClientMock.get.mockResolvedValue({
      data: {
        config_version: 'v1',
        mask_token: '******',
        items: [
          {
            key: 'OPENAI_API_KEY',
            value: '',
            raw_value_exists: false,
            is_masked: false,
            schema: {
              key: 'OPENAI_API_KEY',
              category: 'ai_model',
              data_type: 'string',
              ui_control: 'password',
              is_sensitive: true,
              is_required: false,
              is_editable: true,
              options: [],
              validation: {},
              display_order: 10,
            },
          },
        ],
      },
    });
    const getCredentialStatus = vi.fn().mockResolvedValue({
      success: true,
      supported: true,
      configured: true,
    });
    installDesktopBridge({
      getCredentialStatus,
      setCredential: vi.fn(),
      clearCredential: vi.fn(),
    });

    const config = await systemConfigApi.getConfig(true);

    expect(getCredentialStatus).toHaveBeenCalledWith('OPENAI_API_KEY');
    expect(config.items[0]).toMatchObject({
      value: '******',
      rawValueExists: true,
      isMasked: true,
    });
  });

  it('validates sensitive desktop updates locally and never posts their value to the backend', async () => {
    const setCredential = vi.fn();
    installDesktopBridge({
      getCredentialStatus: vi.fn(),
      setCredential,
      clearCredential: vi.fn(),
    });

    const result = await systemConfigApi.validate({
      items: [{ key: 'OPENAI_API_KEY', action: 'set', value: 'fake-unit-test-value' }],
    });

    expect(result).toEqual({ valid: true, issues: [] });
    expect(apiClientMock.post).not.toHaveBeenCalled();
    expect(setCredential).not.toHaveBeenCalled();
  });

  it('sends only non-sensitive items to the backend and writes the secret through Electron IPC', async () => {
    apiClientMock.put.mockResolvedValue({
      data: {
        success: true,
        config_version: 'v2',
        applied_count: 1,
        skipped_masked_count: 0,
        reload_triggered: true,
        updated_keys: ['STOCK_LIST'],
        warnings: [],
      },
    });
    const setCredential = vi.fn().mockResolvedValue({
      success: true,
      supported: true,
      configured: true,
    });
    installDesktopBridge({
      getCredentialStatus: vi.fn(),
      setCredential,
      clearCredential: vi.fn(),
    });

    const result = await systemConfigApi.update({
      configVersion: 'v1',
      maskToken: '******',
      reloadNow: true,
      items: [
        { key: 'OPENAI_API_KEY', action: 'set', value: 'fake-unit-test-value' },
        { key: 'STOCK_LIST', value: '600519,000001' },
      ],
    });

    expect(apiClientMock.put).toHaveBeenCalledTimes(1);
    const backendPayload = apiClientMock.put.mock.calls[0]?.[1];
    expect(backendPayload).toMatchObject({
      config_version: 'v1',
      items: [{ key: 'STOCK_LIST', value: '600519,000001' }],
    });
    expect(JSON.stringify(backendPayload)).not.toContain('fake-unit-test-value');
    expect(setCredential).toHaveBeenCalledWith('OPENAI_API_KEY', 'fake-unit-test-value');
    expect(result).toMatchObject({
      success: true,
      appliedCount: 2,
      updatedKeys: ['STOCK_LIST', 'OPENAI_API_KEY'],
    });
  });
});
