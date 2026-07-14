import { beforeEach, describe, expect, it, vi } from 'vitest';
import { systemConfigApi } from '../systemConfig';

const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
const put = vi.hoisted(() => vi.fn());

vi.mock('../index', () => ({
  default: {
    get,
    post,
    put,
  },
}));

describe('systemConfigApi', () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    put.mockReset();
    put.mockResolvedValue({ data: { success: true, config_version: 'v2', applied_count: 1, skipped_masked_count: 0, reload_triggered: true, updated_keys: [], warnings: [] } });
    post.mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        error: null,
        error_code: null,
        stage: 'chat_completion',
        retryable: false,
        details: {},
        resolved_protocol: 'openai',
        resolved_model: 'openai/gpt-4o-mini',
        latency_ms: 10,
        capability_results: {},
      },
    });
  });

  it('omits capability_checks from basic LLM channel test payloads', async () => {
    await systemConfigApi.testLLMChannel({
      name: 'openai',
      protocol: 'openai',
      baseUrl: 'https://api.openai.com/v1',
      apiKey: 'sk-test',
      models: ['gpt-4o-mini'],
    });

    expect(post).toHaveBeenCalledWith(
      '/api/v1/system/config/llm/test-channel',
      expect.not.objectContaining({ capability_checks: expect.anything() }),
    );
  });

  it('sends capability_checks only for explicit runtime capability checks', async () => {
    await systemConfigApi.testLLMChannel({
      name: 'openai',
      protocol: 'openai',
      baseUrl: 'https://api.openai.com/v1',
      apiKey: 'sk-test',
      models: ['gpt-4o-mini'],
      capabilityChecks: ['json', 'stream'],
    });

    expect(post).toHaveBeenCalledWith(
      '/api/v1/system/config/llm/test-channel',
      expect.objectContaining({ capability_checks: ['json', 'stream'] }),
    );
  });

  it('sends notification channel test payloads with snake_case fields', async () => {
    post.mockResolvedValueOnce({
      data: {
        success: true,
        message: 'ok',
        error_code: null,
        stage: 'notification_send',
        retryable: false,
        latency_ms: 15,
        attempts: [
          {
            channel: 'custom',
            success: true,
            message: 'sent',
            target: 'https://example.com/hook?token=***',
            error_code: null,
            stage: 'notification_send',
            retryable: false,
            latency_ms: 15,
            http_status: 200,
          },
        ],
      },
    });

    const result = await systemConfigApi.testNotificationChannel({
      channel: 'custom',
      items: [{ key: 'CUSTOM_WEBHOOK_URLS', value: 'https://example.com/hook?token=secret' }],
      maskToken: '******',
      title: 'hello',
      content: 'world',
      timeoutSeconds: 7,
    });

    expect(post).toHaveBeenCalledWith(
      '/api/v1/system/config/notification/test-channel',
      {
        channel: 'custom',
        items: [{ key: 'CUSTOM_WEBHOOK_URLS', value: 'https://example.com/hook?token=secret' }],
        mask_token: '******',
        title: 'hello',
        content: 'world',
        timeout_seconds: 7,
      },
    );
    expect(result.latencyMs).toBe(15);
    expect(result.attempts[0].errorCode).toBeNull();
    expect(result.attempts[0].httpStatus).toBe(200);
  });



  it('serializes legacy and sensitive update actions without forcing empty values', async () => {
    await systemConfigApi.update({
      configVersion: 'v1',
      maskToken: 'masked-placeholder',
      items: [
        { key: 'NORMAL_FIELD', value: 'plain' },
        { key: 'OPENAI_API_KEY', action: 'set', value: 'new-test-key' },
        { key: 'KEEP_KEY', action: 'keep' },
        { key: 'CLEAR_KEY', action: 'clear' },
      ],
    });

    expect(put).toHaveBeenCalledWith('/api/v1/system/config', {
      config_version: 'v1',
      mask_token: 'masked-placeholder',
      reload_now: true,
      items: [
        { key: 'NORMAL_FIELD', value: 'plain' },
        { key: 'OPENAI_API_KEY', action: 'set', value: 'new-test-key' },
        { key: 'KEEP_KEY', action: 'keep' },
        { key: 'CLEAR_KEY', action: 'clear' },
      ],
    });
  });

  it('preserves actions when validating sensitive update items', async () => {
    post.mockResolvedValueOnce({ data: { valid: true, issues: [] } });

    await systemConfigApi.validate({
      items: [
        { key: 'OPENAI_API_KEY', action: 'clear' },
        { key: 'GEMINI_API_KEY', action: 'set', value: 'new-test-key' },
      ],
    });

    expect(post).toHaveBeenCalledWith('/api/v1/system/config/validate', {
      items: [
        { key: 'OPENAI_API_KEY', action: 'clear' },
        { key: 'GEMINI_API_KEY', action: 'set', value: 'new-test-key' },
      ],
    });
  });

  it('loads first-run setup status with camelCase fields', async () => {
    get.mockResolvedValueOnce({
      data: {
        is_complete: false,
        ready_for_smoke: false,
        required_missing_keys: ['llm_primary'],
        next_step_key: 'llm_primary',
        checks: [
          {
            key: 'llm_primary',
            title: 'LLM 主渠道',
            category: 'ai_model',
            required: true,
            status: 'needs_action',
            message: '缺少主模型配置',
            next_step: '打开系统设置',
          },
        ],
      },
    });

    const result = await systemConfigApi.getSetupStatus();

    expect(get).toHaveBeenCalledWith('/api/v1/system/config/setup/status');
    expect(result.isComplete).toBe(false);
    expect(result.nextStepKey).toBe('llm_primary');
    expect(result.checks[0].nextStep).toBe('打开系统设置');
  });
});
