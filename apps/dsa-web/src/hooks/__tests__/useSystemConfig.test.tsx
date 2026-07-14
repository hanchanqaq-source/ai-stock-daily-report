import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { isProtectedSensitivePlaceholder, toSensitiveUpdateItem, useSystemConfig } from '../useSystemConfig';

const { getConfig, validate, update } = vi.hoisted(() => ({
  getConfig: vi.fn(),
  validate: vi.fn(),
  update: vi.fn(),
}));

vi.mock('../../api/systemConfig', () => ({
  systemConfigApi: {
    getConfig,
    validate,
    update,
  },
  SystemConfigConflictError: class extends Error {},
  SystemConfigValidationError: class extends Error {
    issues: unknown[] = [];
    parsedError = {
      title: 'validation error',
      message: 'validation error',
      rawMessage: 'validation error',
      category: 'http_error',
    };
  },
}));


const sensitiveItem = {
  key: 'OPENAI_API_KEY',
  value: 'masked-placeholder',
  rawValueExists: true,
  isMasked: true,
  schema: {
    key: 'OPENAI_API_KEY',
    category: 'ai_model' as const,
    dataType: 'string' as const,
    uiControl: 'password' as const,
    isSensitive: true,
    isRequired: false,
    isEditable: true,
    options: [],
    validation: {},
    displayOrder: 2,
  },
};

const sampleConfig = {
  configVersion: 'v1',
  maskToken: '******',
  items: [
    {
      key: 'STOCK_LIST',
      value: 'SH600000',
      rawValueExists: true,
      isMasked: false,
      schema: {
        key: 'STOCK_LIST',
        category: 'base',
        dataType: 'string',
        uiControl: 'textarea',
        isSensitive: false,
        isRequired: false,
        isEditable: true,
        options: [],
        validation: {},
        displayOrder: 1,
      },
    },
  ],
};

const sampleLlmConfig = {
  ...sampleConfig,
  items: [
    ...sampleConfig.items,
    {
      key: 'LLM_CHANNELS',
      value: 'primary',
      rawValueExists: true,
      isMasked: false,
      schema: {
        key: 'LLM_CHANNELS',
        category: 'ai_model',
        dataType: 'string',
        uiControl: 'textarea',
        isSensitive: false,
        isRequired: false,
        isEditable: true,
        options: [],
        validation: {},
        displayOrder: 10,
      },
    },
    {
      key: 'LITELLM_MODEL',
      value: 'gpt-5.0',
      rawValueExists: true,
      isMasked: false,
      schema: {
        key: 'LITELLM_MODEL',
        category: 'ai_model',
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
    {
      key: 'OPENAI_BASE_URL',
      value: 'https://api.openai.com/v1',
      rawValueExists: true,
      isMasked: false,
      schema: {
        key: 'OPENAI_BASE_URL',
        category: 'ai_model',
        dataType: 'string',
        uiControl: 'text',
        isSensitive: false,
        isRequired: false,
        isEditable: true,
        options: [],
        validation: {},
        displayOrder: 30,
      },
    },
    {
      key: 'OPENAI_VISION_MODEL',
      value: 'gpt-4o-vision',
      rawValueExists: true,
      isMasked: false,
      schema: {
        key: 'OPENAI_VISION_MODEL',
        category: 'ai_model',
        dataType: 'string',
        uiControl: 'text',
        isSensitive: false,
        isRequired: false,
        isEditable: true,
        options: [],
        validation: {},
        displayOrder: 35,
      },
    },
  ],
};

describe('useSystemConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getConfig.mockResolvedValue(sampleConfig);
    validate.mockResolvedValue({ valid: true, issues: [] });
    update.mockResolvedValue({ warnings: [] });
  });



  it('maps sensitive draft modes to keep set clear without submitting placeholders', () => {
    expect(toSensitiveUpdateItem(sensitiveItem, 'masked-placeholder', 'keep', 'masked-placeholder')).toBeNull();
    expect(toSensitiveUpdateItem(sensitiveItem, 'new-test-key', 'editing', 'masked-placeholder')).toEqual({
      key: 'OPENAI_API_KEY',
      action: 'set',
      value: 'new-test-key',
    });
    expect(toSensitiveUpdateItem(sensitiveItem, 'masked-placeholder', 'editing', 'masked-placeholder')).toBeNull();
    expect(toSensitiveUpdateItem(sensitiveItem, '********', 'editing', 'masked-placeholder')).toBeNull();
    expect(toSensitiveUpdateItem(sensitiveItem, '', 'clear', 'masked-placeholder')).toEqual({
      key: 'OPENAI_API_KEY',
      action: 'clear',
    });
    expect(isProtectedSensitivePlaceholder('masked-value', 'masked-placeholder')).toBe(true);
  });

  it('keeps configured sensitive fields clean until explicit edit or clear', async () => {
    const config = { ...sampleConfig, maskToken: 'masked-placeholder', items: [...sampleConfig.items, sensitiveItem] };
    getConfig.mockResolvedValueOnce(config);

    const { result } = renderHook(() => useSystemConfig());
    await act(async () => {
      await result.current.load();
    });

    expect(result.current.getSensitiveFieldState('OPENAI_API_KEY')).toMatchObject({ mode: 'keep', isConfigured: true, isDirty: false });
    expect(result.current.getChangedItems()).toEqual([]);

    act(() => {
      result.current.beginSensitiveEdit('OPENAI_API_KEY');
    });
    expect(result.current.getChangedItems()).toEqual([]);

    act(() => {
      result.current.setDraftValue('OPENAI_API_KEY', 'new-test-key');
    });
    expect(result.current.getChangedItems()).toEqual([{ key: 'OPENAI_API_KEY', action: 'set', value: 'new-test-key' }]);

    act(() => {
      result.current.cancelSensitiveEdit('OPENAI_API_KEY');
    });
    expect(result.current.getSensitiveFieldState('OPENAI_API_KEY')).toMatchObject({ mode: 'keep', isDirty: false });
    expect(result.current.getChangedItems()).toEqual([]);

    act(() => {
      result.current.markSensitiveClear('OPENAI_API_KEY');
    });
    expect(result.current.getChangedItems()).toEqual([{ key: 'OPENAI_API_KEY', action: 'clear' }]);
  });

  it('resets sensitive edit state after a successful save reload', async () => {
    const config = { ...sampleConfig, maskToken: 'masked-placeholder', items: [...sampleConfig.items, sensitiveItem] };
    getConfig.mockResolvedValueOnce(config);
    getConfig.mockResolvedValueOnce(config);

    const { result } = renderHook(() => useSystemConfig());
    await act(async () => {
      await result.current.load();
    });
    act(() => {
      result.current.beginSensitiveEdit('OPENAI_API_KEY');
      result.current.setDraftValue('OPENAI_API_KEY', 'new-test-key');
    });

    await act(async () => {
      await result.current.save();
    });

    expect(update).toHaveBeenCalledWith(expect.objectContaining({
      items: [{ key: 'OPENAI_API_KEY', action: 'set', value: 'new-test-key' }],
    }));
    expect(result.current.getSensitiveFieldState('OPENAI_API_KEY')).toMatchObject({ mode: 'keep', isDirty: false });
  });

  it('keeps load callback stable after a successful load', async () => {
    const { result } = renderHook(() => useSystemConfig());
    const firstLoad = result.current.load;

    await act(async () => {
      await result.current.load();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(getConfig).toHaveBeenCalledTimes(1);
    expect(result.current.load).toBe(firstLoad);
  });

  it('keeps legacy LLM provider fields in save payload without hidden-field migration', async () => {
    const savedConfig = {
      ...sampleLlmConfig,
      items: sampleLlmConfig.items.map((item) => {
        if (item.key === 'LITELLM_MODEL') {
          return { ...item, value: 'qwen/qwen2.5' };
        }
        if (item.key === 'OPENAI_BASE_URL') {
          return { ...item, value: 'https://api.example.org/v1' };
        }
        if (item.key === 'OPENAI_VISION_MODEL') {
          return { ...item, value: 'gpt-4o-mini-vision' };
        }
        return item;
      }),
    };

    getConfig.mockResolvedValueOnce(sampleLlmConfig);
    getConfig.mockResolvedValueOnce(savedConfig);

    const { result } = renderHook(() => useSystemConfig());

    await act(async () => {
      await result.current.load();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setDraftValue('LITELLM_MODEL', 'qwen/qwen2.5');
      result.current.setDraftValue('OPENAI_BASE_URL', 'https://api.example.org/v1');
      result.current.setDraftValue('OPENAI_VISION_MODEL', 'gpt-4o-mini-vision');
    });

    expect(result.current.hasDirty).toBe(true);

    await act(async () => {
      await result.current.save();
    });

    expect(validate).toHaveBeenCalledTimes(1);
    expect(validate).toHaveBeenCalledWith({
      items: [
        { key: 'LITELLM_MODEL', value: 'qwen/qwen2.5' },
        { key: 'OPENAI_BASE_URL', value: 'https://api.example.org/v1' },
        { key: 'OPENAI_VISION_MODEL', value: 'gpt-4o-mini-vision' },
      ],
    });
    expect(update).toHaveBeenCalledTimes(1);
    expect(update).toHaveBeenCalledWith({
      configVersion: 'v1',
      maskToken: '******',
      reloadNow: true,
      items: [
        { key: 'LITELLM_MODEL', value: 'qwen/qwen2.5' },
        { key: 'OPENAI_BASE_URL', value: 'https://api.example.org/v1' },
        { key: 'OPENAI_VISION_MODEL', value: 'gpt-4o-mini-vision' },
      ],
    });
    expect(result.current.serverItems.find((item) => item.key === 'OPENAI_BASE_URL')?.value).toBe('https://api.example.org/v1');
    expect(result.current.serverItems.find((item) => item.key === 'OPENAI_VISION_MODEL')?.value).toBe('gpt-4o-mini-vision');
    expect(result.current.hasDirty).toBe(false);
    expect(result.current.dirtyCount).toBe(0);
  });

  it('only resets local draft edits without mutating server values for LLM fields', async () => {
    const current = sampleLlmConfig;
    getConfig.mockResolvedValueOnce(current);

    const { result } = renderHook(() => useSystemConfig());

    await act(async () => {
      await result.current.load();
    });

    act(() => {
      result.current.setDraftValue('LITELLM_MODEL', 'qwen/qwen2.5');
      result.current.setDraftValue('OPENAI_BASE_URL', 'https://api.example.org/v1');
    });

    expect(result.current.hasDirty).toBe(true);
    expect(result.current.dirtyCount).toBe(2);

    act(() => {
      result.current.resetDraft();
    });

    expect(result.current.hasDirty).toBe(false);
    expect(result.current.dirtyCount).toBe(0);

    await act(async () => {
      await result.current.save();
    });

    expect(validate).not.toHaveBeenCalled();
    expect(update).not.toHaveBeenCalled();
  });

  it('preserves unrelated runtime model fields when saving non-runtime config keys', async () => {
    const stockUpdatedConfig = {
      ...sampleLlmConfig,
      items: sampleLlmConfig.items.map((item) => {
        if (item.key === 'STOCK_LIST') {
          return { ...item, value: 'SH600000,SH600519' };
        }
        return item;
      }),
    };

    getConfig.mockResolvedValueOnce(sampleLlmConfig);
    getConfig.mockResolvedValueOnce(stockUpdatedConfig);

    const { result } = renderHook(() => useSystemConfig());

    await act(async () => {
      await result.current.load();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setDraftValue('STOCK_LIST', 'SH600000,SH600519');
    });

    expect(result.current.hasDirty).toBe(true);
    expect(result.current.dirtyCount).toBe(1);

    await act(async () => {
      await result.current.save();
    });

    expect(validate).toHaveBeenCalledTimes(1);
    expect(validate).toHaveBeenCalledWith({
      items: [{ key: 'STOCK_LIST', value: 'SH600000,SH600519' }],
    });
    expect(update).toHaveBeenCalledTimes(1);
    expect(update).toHaveBeenCalledWith({
      configVersion: 'v1',
      maskToken: '******',
      reloadNow: true,
      items: [{ key: 'STOCK_LIST', value: 'SH600000,SH600519' }],
    });

    expect(result.current.serverItems.find((item) => item.key === 'LITELLM_MODEL')?.value).toBe('gpt-5.0');
    expect(result.current.serverItems.find((item) => item.key === 'OPENAI_BASE_URL')?.value).toBe('https://api.openai.com/v1');
    expect(result.current.serverItems.find((item) => item.key === 'OPENAI_VISION_MODEL')?.value).toBe('gpt-4o-vision');
    expect(result.current.hasDirty).toBe(false);
    expect(result.current.dirtyCount).toBe(0);
  });
});
