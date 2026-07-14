import type {
  ConfigValidationIssue,
  SystemConfigResponse,
  SystemConfigUpdateItem,
  ValidateSystemConfigResponse,
} from '../types/systemConfig';

const CREDENTIAL_KEY_PATTERN = /^[A-Z][A-Z0-9_]{1,127}$/;
const DEFAULT_MASK_TOKEN = '******';

export type RawDesktopCredentialResult = {
  success?: unknown;
  configured?: unknown;
  supported?: unknown;
  errorCode?: unknown;
};

export type DesktopCredentialBridge = {
  getCredentialStatus?: (key: string) => Promise<RawDesktopCredentialResult>;
  setCredential?: (key: string, value: string) => Promise<RawDesktopCredentialResult>;
  clearCredential?: (key: string) => Promise<RawDesktopCredentialResult>;
};

type DesktopWindow = Window & {
  dsaDesktop?: DesktopCredentialBridge;
};

export type DesktopCredentialSplit = {
  desktopItems: SystemConfigUpdateItem[];
  serverItems: SystemConfigUpdateItem[];
};

type NormalizedDesktopCredentialResult = {
  success: boolean;
  configured: boolean;
  supported: boolean;
  errorCode: string | null;
};

export class DesktopCredentialOperationError extends Error {
  key: string;
  errorCode: string;

  constructor(key: string, errorCode: string) {
    super(`桌面安全凭证操作失败（${errorCode}）`);
    this.name = 'DesktopCredentialOperationError';
    this.key = key;
    this.errorCode = errorCode;
  }
}

export function getDesktopCredentialBridge(): DesktopCredentialBridge | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const bridge = (window as DesktopWindow).dsaDesktop;
  return bridge && typeof bridge === 'object' ? bridge : null;
}

export function hasDesktopCredentialMethods(bridge: DesktopCredentialBridge | null): boolean {
  return Boolean(
    bridge
    && typeof bridge.getCredentialStatus === 'function'
    && typeof bridge.setCredential === 'function'
    && typeof bridge.clearCredential === 'function',
  );
}

export function isDesktopCredentialUpdate(item: SystemConfigUpdateItem): boolean {
  return item.action === 'set' || item.action === 'clear';
}

export function splitDesktopCredentialUpdates(items: SystemConfigUpdateItem[]): DesktopCredentialSplit {
  const desktopItems: SystemConfigUpdateItem[] = [];
  const serverItems: SystemConfigUpdateItem[] = [];

  for (const item of items) {
    if (isDesktopCredentialUpdate(item)) {
      desktopItems.push(item);
    } else {
      serverItems.push(item);
    }
  }

  return { desktopItems, serverItems };
}

function makeValidationIssue(key: string, code: string, message: string): ConfigValidationIssue {
  return {
    key,
    code,
    message,
    severity: 'error',
  };
}

export function validateDesktopCredentialUpdates(
  items: SystemConfigUpdateItem[],
  bridge: DesktopCredentialBridge | null,
): ValidateSystemConfigResponse {
  const issues: ConfigValidationIssue[] = [];

  if (items.length > 0 && !hasDesktopCredentialMethods(bridge)) {
    issues.push(makeValidationIssue(
      '__desktop_credential_store__',
      'desktop_credential_bridge_unavailable',
      '当前桌面端版本未提供安全凭证存储能力，请更新桌面端后重试。',
    ));
    return { valid: false, issues };
  }

  for (const item of items) {
    if (!CREDENTIAL_KEY_PATTERN.test(item.key)) {
      issues.push(makeValidationIssue(item.key, 'invalid_credential_key', '安全凭证键名不合法。'));
      continue;
    }

    if (item.action === 'set') {
      const value = typeof item.value === 'string' ? item.value : '';
      const normalized = value.trim();
      if (!normalized || normalized === DEFAULT_MASK_TOKEN || /^\*{4,}$/.test(normalized)) {
        issues.push(makeValidationIssue(item.key, 'invalid_credential_value', '请输入新的安全凭证值，不能提交空值或掩码占位符。'));
      }
      continue;
    }

    if (item.action === 'clear') {
      if (item.value !== undefined) {
        issues.push(makeValidationIssue(item.key, 'invalid_clear_payload', '清除安全凭证时不能同时提交值。'));
      }
      continue;
    }

    issues.push(makeValidationIssue(item.key, 'invalid_credential_action', '安全凭证操作必须是设置或清除。'));
  }

  return { valid: issues.length === 0, issues };
}

function normalizeDesktopCredentialResult(result: RawDesktopCredentialResult): NormalizedDesktopCredentialResult {
  if (!result || typeof result !== 'object') {
    return {
      success: false,
      configured: false,
      supported: false,
      errorCode: 'invalid_desktop_credential_result',
    };
  }

  return {
    success: result.success === true,
    configured: result.configured === true,
    supported: result.supported === true,
    errorCode: typeof result.errorCode === 'string' && result.errorCode.trim()
      ? result.errorCode.trim()
      : null,
  };
}

function resolveFailureCode(result: NormalizedDesktopCredentialResult, fallback: string): string {
  if (!result.supported) {
    return result.errorCode || 'desktop_credential_store_unsupported';
  }
  return result.errorCode || fallback;
}

export async function applyDesktopCredentialUpdates(
  bridge: DesktopCredentialBridge | null,
  items: SystemConfigUpdateItem[],
): Promise<string[]> {
  const validation = validateDesktopCredentialUpdates(items, bridge);
  if (!validation.valid) {
    const firstIssue = validation.issues[0];
    throw new DesktopCredentialOperationError(firstIssue?.key || '__desktop_credential_store__', firstIssue?.code || 'invalid_credential_update');
  }

  const resolvedBridge = bridge as Required<DesktopCredentialBridge>;
  const appliedKeys: string[] = [];

  for (const item of items) {
    let rawResult: RawDesktopCredentialResult;
    try {
      rawResult = item.action === 'set'
        ? await resolvedBridge.setCredential(item.key, item.value as string)
        : await resolvedBridge.clearCredential(item.key);
    } catch {
      throw new DesktopCredentialOperationError(item.key, 'desktop_credential_ipc_failed');
    }

    const result = normalizeDesktopCredentialResult(rawResult);
    const expectedConfigured = item.action === 'set';
    if (!result.success || !result.supported || result.configured !== expectedConfigured) {
      throw new DesktopCredentialOperationError(
        item.key,
        resolveFailureCode(result, expectedConfigured ? 'desktop_credential_set_failed' : 'desktop_credential_clear_failed'),
      );
    }
    appliedKeys.push(item.key);
  }

  return appliedKeys;
}

export async function overlayDesktopCredentialStatuses(
  config: SystemConfigResponse,
  bridge: DesktopCredentialBridge | null,
): Promise<SystemConfigResponse> {
  if (!bridge || typeof bridge.getCredentialStatus !== 'function') {
    return config;
  }

  const sensitiveItems = config.items.filter((item) => item.schema?.isSensitive);
  if (sensitiveItems.length === 0) {
    return config;
  }

  const statusEntries = await Promise.all(sensitiveItems.map(async (item) => {
    try {
      const status = normalizeDesktopCredentialResult(await bridge.getCredentialStatus?.(item.key) ?? {});
      return [item.key, status] as const;
    } catch {
      return [item.key, null] as const;
    }
  }));
  const statusByKey = new Map(statusEntries);
  const maskToken = config.maskToken || DEFAULT_MASK_TOKEN;

  return {
    ...config,
    items: config.items.map((item) => {
      if (!item.schema?.isSensitive) {
        return item;
      }
      const status = statusByKey.get(item.key);
      if (!status || !status.success || !status.supported) {
        return item;
      }
      return {
        ...item,
        value: status.configured ? maskToken : '',
        rawValueExists: status.configured,
        isMasked: status.configured,
      };
    }),
  };
}
