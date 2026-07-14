import { useCallback, useMemo, useRef, useState } from 'react';
import { createParsedApiError, getParsedApiError, type ParsedApiError } from '../api/error';
import { systemConfigApi, SystemConfigConflictError, SystemConfigValidationError } from '../api/systemConfig';
import type {
  ConfigValidationIssue,
  SystemConfigCategorySchema,
  SystemConfigItem,
  SystemConfigUpdateAction,
  SystemConfigUpdateItem,
} from '../types/systemConfig';

type ToastState = {
  type: 'success';
  message: string;
} | {
  type: 'error';
  error: ParsedApiError;
} | null;

type RetryAction = 'load' | 'save' | null;

type SaveResult = {
  success: boolean;
  message?: string;
  issues?: ConfigValidationIssue[];
};

const CATEGORY_DISPLAY_ORDER: Record<string, number> = {
  base: 10,
  ai_model: 20,
  data_source: 30,
  notification: 40,
  system: 50,
  agent: 55,
  backtest: 60,
  uncategorized: 99,
};

function sortItemsByOrder(items: SystemConfigItem[]): SystemConfigItem[] {
  return [...items].sort((a, b) => {
    const left = a.schema?.displayOrder ?? 9999;
    const right = b.schema?.displayOrder ?? 9999;
    if (left !== right) {
      return left - right;
    }
    return a.key.localeCompare(b.key);
  });
}

export type SensitiveDraftMode = 'keep' | 'editing' | 'clear';

export function isSensitiveConfigured(item: SystemConfigItem | undefined): boolean {
  return Boolean(item?.schema?.isSensitive && item.rawValueExists && item.isMasked);
}

export function isProtectedSensitivePlaceholder(value: string, maskToken: string): boolean {
  const normalized = value.trim();
  if (!normalized) {
    return false;
  }
  return normalized === maskToken
    || normalized.toLowerCase() === 'masked-value'
    || /^\*{4,}$/.test(normalized);
}

export function toSensitiveUpdateItem(
  item: SystemConfigItem,
  draftValue: string,
  mode: SensitiveDraftMode | undefined,
  maskToken: string,
): SystemConfigUpdateItem | null {
  if (!item.schema?.isSensitive) {
    return null;
  }
  const action: SystemConfigUpdateAction = mode === 'clear' ? 'clear' : mode === 'editing' ? 'set' : 'keep';
  if (action === 'keep') {
    return null;
  }
  if (action === 'clear') {
    return { key: item.key, action: 'clear' };
  }
  const normalizedValue = normalizeFieldValue(draftValue, item.schema);
  if (!normalizedValue || isProtectedSensitivePlaceholder(normalizedValue, maskToken)) {
    return null;
  }
  return { key: item.key, action: 'set', value: normalizedValue };
}

function isMultiValueSchema(schema: SystemConfigItem['schema'] | undefined): boolean {
  const validation = (schema?.validation ?? {}) as Record<string, unknown>;
  return Boolean(validation.multiValue ?? validation.multi_value);
}

function normalizeFieldValue(value: string, schema: SystemConfigItem['schema'] | undefined): string {
  if (!isMultiValueSchema(schema)) {
    return value;
  }

  return value
    .split(',')
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)
    .join(',');
}

export function useSystemConfig() {
  // Server state
  const [configVersion, setConfigVersion] = useState<string>('');
  const [maskToken, setMaskToken] = useState<string>('******');
  const [serverItems, setServerItems] = useState<SystemConfigItem[]>([]);

  // UI state
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [sensitiveDraftModes, setSensitiveDraftModes] = useState<Record<string, SensitiveDraftMode>>({});
  const [activeCategory, setActiveCategory] = useState<string>('base');
  const [validationIssues, setValidationIssues] = useState<ConfigValidationIssue[]>([]);
  const [toast, setToast] = useState<ToastState>(null);

  // Request state
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState<ParsedApiError | null>(null);
  const [saveError, setSaveError] = useState<ParsedApiError | null>(null);
  const [retryAction, setRetryAction] = useState<RetryAction>(null);
  const serverItemByKeyRef = useRef<Record<string, SystemConfigItem>>({});

  const mergedItems = useMemo(() => {
    return sortItemsByOrder(
      serverItems.map((item) => ({
        ...item,
        value: item.schema?.isSensitive && sensitiveDraftModes[item.key] !== 'editing'
          ? item.value
          : draftValues[item.key] ?? item.value,
      })),
    );
  }, [draftValues, sensitiveDraftModes, serverItems]);

  const serverItemByKey = useMemo(() => {
    const map: Record<string, SystemConfigItem> = {};
    for (const item of serverItems) {
      map[item.key] = item;
    }
    serverItemByKeyRef.current = map;
    return map;
  }, [serverItems]);

  const categories = useMemo<SystemConfigCategorySchema[]>(() => {
    // Infer tabs from loaded config item schema metadata.
    const categoryMap = new Map<string, SystemConfigCategorySchema>();
    for (const item of mergedItems) {
      if (!item.schema) {
        continue;
      }

      const category = item.schema.category;
      if (!categoryMap.has(category)) {
        categoryMap.set(category, {
          category,
          title: category.replace('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
          description: '',
          displayOrder: CATEGORY_DISPLAY_ORDER[category] ?? 999,
          fields: [],
        });
      }
      categoryMap.get(category)?.fields.push(item.schema);
    }

    return [...categoryMap.values()].sort((a, b) => a.displayOrder - b.displayOrder);
  }, [mergedItems]);

  const itemsByCategory = useMemo(() => {
    const map: Record<string, SystemConfigItem[]> = {};
    for (const item of mergedItems) {
      const category = item.schema?.category ?? 'uncategorized';
      if (!map[category]) {
        map[category] = [];
      }
      map[category].push(item);
    }
    return map;
  }, [mergedItems]);

  const dirtyKeys = useMemo(() => {
    const keys: string[] = [];
    for (const item of serverItems) {
      if (item.schema?.isSensitive) {
        if (toSensitiveUpdateItem(item, draftValues[item.key] ?? '', sensitiveDraftModes[item.key], maskToken)) {
          keys.push(item.key);
        }
        continue;
      }

      const draftRaw = draftValues[item.key];
      if (draftRaw === undefined) {
        continue;
      }

      const normalizedDraft = normalizeFieldValue(draftRaw, item.schema);
      const normalizedCurrent = normalizeFieldValue(item.value, item.schema);
      if (normalizedDraft !== normalizedCurrent) {
        keys.push(item.key);
      }
    }
    return keys;
  }, [draftValues, maskToken, sensitiveDraftModes, serverItems]);

  const hasDirty = dirtyKeys.length > 0;

  const issueByKey = useMemo(() => {
    const map: Record<string, ConfigValidationIssue[]> = {};
    for (const issue of validationIssues) {
      if (!map[issue.key]) {
        map[issue.key] = [];
      }
      map[issue.key].push(issue);
    }
    return map;
  }, [validationIssues]);

  const applyServerPayload = useCallback(
    (
      items: SystemConfigItem[],
      version: string,
      token: string,
      options?: { preserveDirty?: boolean; committedKeys?: string[] },
    ) => {
      const sorted = sortItemsByOrder(items);
      const previousServerMap = serverItemByKeyRef.current;
      const committedKeys = new Set(options?.committedKeys ?? []);
      const preserveDirty = options?.preserveDirty ?? false;

      setServerItems(sorted);
      setConfigVersion(version);
      setMaskToken(token || '******');

      setSensitiveDraftModes((prevModes) => {
        if (!preserveDirty) {
          return {};
        }
        const nextModes: Record<string, SensitiveDraftMode> = {};
        for (const item of sorted) {
          if (committedKeys.has(item.key)) {
            continue;
          }
          const previousMode = prevModes[item.key];
          if (item.schema?.isSensitive && previousMode && previousMode !== 'keep') {
            nextModes[item.key] = previousMode;
          }
        }
        return nextModes;
      });

      setDraftValues((prevDraft) => {
        const nextDraft: Record<string, string> = {};
        for (const item of sorted) {
          if (committedKeys.has(item.key)) {
            nextDraft[item.key] = item.schema?.isSensitive ? '' : item.value;
            continue;
          }

          if (preserveDirty) {
            const previousServerValue = previousServerMap[item.key]?.value;
            const hasDraft = prevDraft[item.key] !== undefined;
            const wasDirty = item.schema?.isSensitive
              ? Boolean(prevDraft[item.key])
              : hasDraft && prevDraft[item.key] !== previousServerValue;
            nextDraft[item.key] = wasDirty ? prevDraft[item.key] : item.schema?.isSensitive ? '' : item.value;
            continue;
          }

          nextDraft[item.key] = item.schema?.isSensitive ? '' : item.value;
        }
        return nextDraft;
      });

      const defaultCategory = sorted[0]?.schema?.category || 'base';
      setActiveCategory((current) => {
        const exists = sorted.some((item) => item.schema?.category === current);
        return exists ? current : defaultCategory;
      });
      setValidationIssues([]);
    },
    [],
  );

  const load = useCallback(async (): Promise<boolean> => {
    setIsLoading(true);
    setLoadError(null);
    setRetryAction(null);

    try {
      const config = await systemConfigApi.getConfig(true);
      applyServerPayload(config.items, config.configVersion, config.maskToken);
      setToast(null);
      return true;
    } catch (error: unknown) {
      setLoadError(getParsedApiError(error));
      setRetryAction('load');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [applyServerPayload]);

  const resetDraft = useCallback(() => {
    const next: Record<string, string> = {};
    for (const item of serverItems) {
      next[item.key] = item.schema?.isSensitive ? '' : item.value;
    }
    setDraftValues(next);
    setSensitiveDraftModes({});
    setValidationIssues([]);
    setSaveError(null);
  }, [serverItems]);

  const applyPartialUpdate = useCallback((updatedItems: Array<{ key: string; value: string }>) => {
    setDraftValues((prevDraft) => {
      const nextDraft = { ...prevDraft };
      for (const item of updatedItems) {
        nextDraft[item.key] = item.value;
      }
      return nextDraft;
    });
  }, []);

  const refreshAfterExternalSave = useCallback(
    async (committedKeys: string[]) => {
      const config = await systemConfigApi.getConfig(true);
      applyServerPayload(config.items, config.configVersion, config.maskToken, {
        preserveDirty: true,
        committedKeys,
      });
    },
    [applyServerPayload],
  );

  const setDraftValue = useCallback((key: string, value: string) => {
    const serverItem = serverItemByKeyRef.current[key];
    setDraftValues((previous) => ({
      ...previous,
      [key]: value,
    }));
    if (serverItem?.schema?.isSensitive) {
      setSensitiveDraftModes((previous) => ({
        ...previous,
        [key]: 'editing',
      }));
    }
  }, []);

  const beginSensitiveEdit = useCallback((key: string) => {
    setDraftValues((previous) => ({ ...previous, [key]: '' }));
    setSensitiveDraftModes((previous) => ({ ...previous, [key]: 'editing' }));
  }, []);

  const cancelSensitiveEdit = useCallback((key: string) => {
    setDraftValues((previous) => ({ ...previous, [key]: '' }));
    setSensitiveDraftModes((previous) => {
      const next = { ...previous };
      delete next[key];
      return next;
    });
  }, []);

  const markSensitiveClear = useCallback((key: string) => {
    setDraftValues((previous) => ({ ...previous, [key]: '' }));
    setSensitiveDraftModes((previous) => ({ ...previous, [key]: 'clear' }));
  }, []);

  const getSensitiveFieldState = useCallback((key: string) => {
    const item = serverItemByKeyRef.current[key];
    const mode = sensitiveDraftModes[key] ?? 'keep';
    return {
      mode,
      isConfigured: isSensitiveConfigured(item),
      isDirty: Boolean(item && toSensitiveUpdateItem(item, draftValues[key] ?? '', mode, maskToken)),
    };
  }, [draftValues, maskToken, sensitiveDraftModes]);

  const getChangedItems = useCallback((): SystemConfigUpdateItem[] => {
    return dirtyKeys
      .map((key) => {
        const serverItem = serverItemByKey[key];
        if (serverItem?.schema?.isSensitive) {
          return toSensitiveUpdateItem(serverItem, draftValues[key] ?? '', sensitiveDraftModes[key], maskToken);
        }
        const normalizedValue = normalizeFieldValue(draftValues[key] ?? '', serverItem?.schema);
        return {
          key,
          value: normalizedValue,
        };
      })
      .filter((item): item is SystemConfigUpdateItem => {
        if (!item) {
          return false;
        }
        const serverItem = serverItemByKey[item.key];
        if (serverItem?.schema?.isSensitive) {
          return true;
        }
        const normalizedCurrent = normalizeFieldValue(serverItem?.value ?? '', serverItem?.schema);
        return item.value !== normalizedCurrent;
      });
  }, [dirtyKeys, draftValues, maskToken, sensitiveDraftModes, serverItemByKey]);

  const save = useCallback(async (changedItems?: SystemConfigUpdateItem[]): Promise<SaveResult> => {
    const explicitItems = changedItems ?? [];
    const resolvedChangedItems = explicitItems.length > 0 ? explicitItems : getChangedItems();

    if (!explicitItems.length && !hasDirty) {
      setToast({ type: 'success', message: '当前没有可保存的修改。' });
      return { success: true, message: '当前没有可保存的修改' };
    }

    if (!resolvedChangedItems.length) {
      setToast({ type: 'success', message: '当前没有可保存的修改。' });
      return { success: true, message: '当前没有可保存的修改' };
    }

    setIsSaving(true);
    setSaveError(null);
    setRetryAction(null);

    try {
      const validateResult = await systemConfigApi.validate({ items: resolvedChangedItems });
      setValidationIssues(validateResult.issues || []);

      if (!validateResult.valid) {
        setSaveError(createParsedApiError({
          title: '配置校验未通过',
          message: '请先修正表单错误后再保存。',
          rawMessage: '配置校验未通过，请先修正表单错误。',
          category: 'http_error',
        }));
        setRetryAction('save');
        return {
          success: false,
          message: '配置校验未通过',
          issues: validateResult.issues,
        };
      }

      const updateResult = await systemConfigApi.update({
        configVersion,
        maskToken,
        reloadNow: true,
        items: resolvedChangedItems,
      });

      const refreshed = await systemConfigApi.getConfig(true);
      applyServerPayload(refreshed.items, refreshed.configVersion, refreshed.maskToken);

      const warningText = updateResult.warnings?.length
        ? `；警告：${updateResult.warnings.join('；')}`
        : '';
      setToast({ type: 'success', message: `配置已更新${warningText}` });
      return { success: true };
    } catch (error: unknown) {
      if (error instanceof SystemConfigValidationError) {
        setValidationIssues(error.issues);
        setSaveError(error.parsedError);
      } else if (error instanceof SystemConfigConflictError) {
        setSaveError(createParsedApiError({
          title: '配置版本冲突',
          message: `${error.message}，请先重新加载配置。`,
          rawMessage: error.parsedError.rawMessage,
          status: error.parsedError.status,
          category: error.parsedError.category,
        }));
      } else {
        setSaveError(getParsedApiError(error));
      }

      setToast({ type: 'error', error: getParsedApiError(error) });
      setRetryAction('save');
      return { success: false, message: '保存失败' };
    } finally {
      setIsSaving(false);
    }
  }, [
    applyServerPayload,
    configVersion,
    getChangedItems,
    hasDirty,
    maskToken,
  ]);

  const retry = useCallback(async () => {
    if (retryAction === 'load') {
      await load();
      return;
    }
    if (retryAction === 'save') {
      await save();
    }
  }, [load, retryAction, save]);

  const clearToast = useCallback(() => {
    setToast(null);
  }, []);

  return {
    // Server state
    configVersion,
    maskToken,
    serverItems,
    categories,
    itemsByCategory,
    issueByKey,

    // UI state
    activeCategory,
    setActiveCategory,
    hasDirty,
    dirtyCount: dirtyKeys.length,
    toast,
    clearToast,

    // Request state
    isLoading,
    isSaving,
    loadError,
    saveError,
    retryAction,

    // Actions
    load,
    retry,
    save,
    resetDraft,
    setDraftValue,
    beginSensitiveEdit,
    cancelSensitiveEdit,
    markSensitiveClear,
    getSensitiveFieldState,
    getChangedItems,
    applyPartialUpdate,
    refreshAfterExternalSave,
  };
}
