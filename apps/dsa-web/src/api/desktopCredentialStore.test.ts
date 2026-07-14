import { describe, expect, it, vi } from 'vitest';
import {
  DesktopCredentialOperationError,
  applyDesktopCredentialUpdates,
  overlayDesktopCredentialStatuses,
  splitDesktopCredentialUpdates,
  validateDesktopCredentialUpdates,
  type DesktopCredentialBridge,
} from './desktopCredentialStore';
import type { SystemConfigResponse, SystemConfigUpdateItem } from '../types/systemConfig';

function makeConfig(): SystemConfigResponse {
  return {
    configVersion: 'v1',
    maskToken: '******',
    items: [
      {
        key: 'OPENAI_API_KEY',
        value: '',
        rawValueExists: false,
        isMasked: false,
        schema: {
          key: 'OPENAI_API_KEY',
          category: 'ai_model',
          dataType: 'string',
          uiControl: 'password',
          isSensitive: true,
          isRequired: false,
          isEditable: true,
          options: [],
          validation: {},
          displayOrder: 10,
        },
      },
      {
        key: 'STOCK_LIST',
        value: '600519',
        rawValueExists: true,
        isMasked: false,
        schema: {
          key: 'STOCK_LIST',
          category: 'base',
          dataType: 'string',
          uiControl: 'text',
          isSensitive: false,
          isRequired: false,
          isEditable: true,
          options: [],
          validation: {},
          displayOrder: 20,
        },
      },
    ],
  };
}

describe('desktop credential routing helpers', () => {
  it('splits sensitive set/clear actions from regular server updates', () => {
    const items: SystemConfigUpdateItem[] = [
      { key: 'OPENAI_API_KEY', action: 'set', value: 'fake-unit-test-value' },
      { key: 'TELEGRAM_BOT_TOKEN', action: 'clear' },
      { key: 'STOCK_LIST', value: '600519,000001' },
    ];

    const split = splitDesktopCredentialUpdates(items);
    expect(split.desktopItems.map((item) => item.key)).toEqual(['OPENAI_API_KEY', 'TELEGRAM_BOT_TOKEN']);
    expect(split.serverItems).toEqual([{ key: 'STOCK_LIST', value: '600519,000001' }]);
  });

  it('blocks missing bridge, blank values, and mask placeholders without echoing the submitted value', () => {
    const missingBridge = validateDesktopCredentialUpdates(
      [{ key: 'OPENAI_API_KEY', action: 'set', value: 'fake-unit-test-value' }],
      null,
    );
    expect(missingBridge.valid).toBe(false);
    expect(missingBridge.issues[0]?.code).toBe('desktop_credential_bridge_unavailable');

    const bridge: DesktopCredentialBridge = {
      getCredentialStatus: vi.fn(),
      setCredential: vi.fn(),
      clearCredential: vi.fn(),
    };
    const invalidValue = validateDesktopCredentialUpdates(
      [{ key: 'OPENAI_API_KEY', action: 'set', value: '******' }],
      bridge,
    );
    expect(invalidValue.valid).toBe(false);
    expect(JSON.stringify(invalidValue)).not.toContain('fake-unit-test-value');
    expect(invalidValue.issues[0]?.code).toBe('invalid_credential_value');
  });

  it('applies set and clear through the desktop bridge and returns only updated keys', async () => {
    const setCredential = vi.fn().mockResolvedValue({ success: true, supported: true, configured: true });
    const clearCredential = vi.fn().mockResolvedValue({ success: true, supported: true, configured: false });
    const bridge: DesktopCredentialBridge = {
      getCredentialStatus: vi.fn(),
      setCredential,
      clearCredential,
    };

    const result = await applyDesktopCredentialUpdates(bridge, [
      { key: 'OPENAI_API_KEY', action: 'set', value: 'fake-unit-test-value' },
      { key: 'TELEGRAM_BOT_TOKEN', action: 'clear' },
    ]);

    expect(result).toEqual(['OPENAI_API_KEY', 'TELEGRAM_BOT_TOKEN']);
    expect(setCredential).toHaveBeenCalledWith('OPENAI_API_KEY', 'fake-unit-test-value');
    expect(clearCredential).toHaveBeenCalledWith('TELEGRAM_BOT_TOKEN');
    expect(JSON.stringify(result)).not.toContain('fake-unit-test-value');
  });

  it('uses fixed low-sensitivity errors when desktop IPC fails', async () => {
    const bridge: DesktopCredentialBridge = {
      getCredentialStatus: vi.fn(),
      setCredential: vi.fn().mockRejectedValue(new Error('local path and secret must not escape')),
      clearCredential: vi.fn(),
    };

    await expect(applyDesktopCredentialUpdates(bridge, [
      { key: 'OPENAI_API_KEY', action: 'set', value: 'fake-unit-test-value' },
    ])).rejects.toMatchObject<Partial<DesktopCredentialOperationError>>({
      errorCode: 'desktop_credential_ipc_failed',
      key: 'OPENAI_API_KEY',
    });
  });

  it('overlays sensitive configured state from the desktop store without changing normal fields', async () => {
    const bridge: DesktopCredentialBridge = {
      getCredentialStatus: vi.fn().mockResolvedValue({ success: true, supported: true, configured: true }),
      setCredential: vi.fn(),
      clearCredential: vi.fn(),
    };
    const original = makeConfig();
    const overlaid = await overlayDesktopCredentialStatuses(original, bridge);

    expect(overlaid.items[0]).toMatchObject({
      key: 'OPENAI_API_KEY',
      value: '******',
      rawValueExists: true,
      isMasked: true,
    });
    expect(overlaid.items[1]).toEqual(original.items[1]);
    expect(original.items[0]).toMatchObject({ value: '', rawValueExists: false, isMasked: false });
  });
});
