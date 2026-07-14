import { useState } from 'react';
import type React from 'react';
import { Badge, Button, Select, Input } from '../common';
import type { ConfigValidationIssue, SystemConfigFieldSchema, SystemConfigItem } from '../../types/systemConfig';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { getSettingsHelpContent } from '../../locales/settingsHelp';
import { getFieldDescriptionZh, getFieldOptionLabel, getFieldTitleZh } from '../../utils/systemConfigI18n';
import type { UiLanguage, UiTextKey } from '../../i18n/uiText';
import { cn } from '../../utils/cn';
import { SettingsHelpButton } from './SettingsHelpButton';

function normalizeSelectOptions(key: string, options: SystemConfigFieldSchema['options'] = [], locale: UiLanguage) {
  return options.map((option) => {
    if (typeof option === 'string') {
      return { value: option, label: getFieldOptionLabel(key, option, undefined, locale) };
    }

    return {
      ...option,
      label: getFieldOptionLabel(key, option.value, option.label, locale),
    };
  });
}

function isMultiValueField(item: SystemConfigItem): boolean {
  const validation = (item.schema?.validation ?? {}) as Record<string, unknown>;
  return Boolean(validation.multiValue ?? validation.multi_value);
}

function parseMultiValues(value: string): string[] {
  if (!value) {
    return [''];
  }

  const values = value.split(',').map((entry) => entry.trim());
  return values.length ? values : [''];
}

function serializeMultiValues(values: string[]): string {
  return values.map((entry) => entry.trim()).join(',');
}

function inferPasswordIconType(key: string): 'password' | 'key' {
  return key.toUpperCase().includes('PASSWORD') ? 'password' : 'key';
}

function resolveDisplayValue(item: SystemConfigItem, value: string): string {
  const schema = item.schema;

  if (
    schema?.uiControl === 'select'
    && !value
    && item.rawValueExists === false
    && schema.defaultValue !== undefined
    && schema.defaultValue !== null
  ) {
    return schema.defaultValue;
  }

  return value;
}

interface SettingsFieldProps {
  item: SystemConfigItem;
  value: string;
  disabled?: boolean;
  onChange: (key: string, value: string) => void;
  issues?: ConfigValidationIssue[];
  sensitiveState?: { mode: 'keep' | 'editing' | 'clear'; isConfigured: boolean; isDirty: boolean };
  onBeginSensitiveEdit?: (key: string) => void;
  onCancelSensitiveEdit?: (key: string) => void;
  onRequestSensitiveClear?: (key: string) => void;
}

function renderFieldControl(
  item: SystemConfigItem,
  value: string,
  disabled: boolean,
  onChange: (nextValue: string) => void,
  isPasswordEditable: boolean,
  onPasswordFocus: () => void,
  controlId: string,
  language: UiLanguage,
  t: (key: UiTextKey) => string,
) {
  const schema = item.schema;
  const commonClass = 'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';
  const controlType = schema?.uiControl ?? 'text';
  const isMultiValue = isMultiValueField(item);

  if (controlType === 'textarea') {
    return (
      <textarea
        id={controlId}
        data-testid={`settings-field-control-${item.key}`}
        className={`${commonClass} min-h-[92px] resize-y py-3`}
        value={value}
        disabled={disabled || !schema?.isEditable}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }

  if (controlType === 'select' && schema?.options?.length) {
    return (
        <Select
          id={controlId}
          value={value}
          onChange={onChange}
          options={normalizeSelectOptions(item.key, schema.options, language)}
          disabled={disabled || !schema.isEditable}
          placeholder={t('common.selectPlaceholder')}
        />
      );
  }

  if (controlType === 'switch') {
    const checked = value.trim().toLowerCase() === 'true';
    return (
      <label className="inline-flex cursor-pointer items-center gap-3">
        <input
          id={controlId}
          type="checkbox"
          checked={checked}
          disabled={disabled || !schema?.isEditable}
          onChange={(event) => onChange(event.target.checked ? 'true' : 'false')}
        />
        <span className="text-sm text-secondary-text">{checked ? t('common.enabled') : t('common.disabled')}</span>
      </label>
    );
  }

  if (controlType === 'password') {
    const iconType = inferPasswordIconType(item.key);

    if (isMultiValue) {
      const values = parseMultiValues(value);

      return (
        <div className="space-y-2">
          {values.map((entry, index) => (
            <div className="flex items-center gap-2" key={`${item.key}-${index}`}>
              <div className="flex-1">
                <Input
                  type="password"
                  allowTogglePassword
                  iconType={iconType}
                  id={index === 0 ? controlId : `${controlId}-${index}`}
                  data-testid={index === 0 ? `settings-field-control-${item.key}` : `settings-field-control-${item.key}-${index}`}
                  readOnly={!isPasswordEditable}
                  onFocus={onPasswordFocus}
                  value={entry}
                  disabled={disabled || !schema?.isEditable}
                  onChange={(event) => {
                    const nextValues = [...values];
                    nextValues[index] = event.target.value;
                    onChange(serializeMultiValues(nextValues));
                  }}
                />
              </div>
              <Button
                type="button"
                variant="settings-secondary"
                size="lg"
                className="px-3 text-xs text-muted-text shadow-none hover:text-danger"
                disabled={disabled || !schema?.isEditable || values.length <= 1}
                onClick={() => {
                  const nextValues = values.filter((_, rowIndex) => rowIndex !== index);
                  onChange(serializeMultiValues(nextValues.length ? nextValues : ['']));
                }}
              >
                {t('settings.fieldDelete')}
              </Button>
            </div>
          ))}

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="settings-secondary"
              size="sm"
              className="text-xs shadow-none"
              disabled={disabled || !schema?.isEditable}
              onClick={() => onChange(serializeMultiValues([...values, '']))}
            >
              {t('settings.fieldAddKey')}
            </Button>
          </div>
        </div>
      );
    }

    return (
      <Input
        type="password"
        allowTogglePassword
        iconType={iconType}
        id={controlId}
        data-testid={`settings-field-control-${item.key}`}
        readOnly={!isPasswordEditable}
        onFocus={onPasswordFocus}
        value={value}
        disabled={disabled || !schema?.isEditable}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }

  const inputType = controlType === 'number' ? 'number' : controlType === 'time' ? 'time' : 'text';

  return (
    <input
      id={controlId}
      data-testid={`settings-field-control-${item.key}`}
      type={inputType}
      className={commonClass}
      value={value}
      disabled={disabled || !schema?.isEditable}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export const SettingsField: React.FC<SettingsFieldProps> = ({
  item,
  value,
  disabled = false,
  onChange,
  issues = [],
  sensitiveState,
  onBeginSensitiveEdit,
  onCancelSensitiveEdit,
  onRequestSensitiveClear,
}) => {
  const { language, t } = useUiLanguage();
  const schema = item.schema;
  const isMultiValue = isMultiValueField(item);
  const helpContent = getSettingsHelpContent(schema?.helpKey, schema?.description, language);
  const localizationKey = schema?.key ?? item.key;
  const fallbackTitle = schema?.title ?? item.key;
  const title = language === 'zh'
    ? getFieldTitleZh(localizationKey, getFieldTitleZh(item.key, fallbackTitle))
    : fallbackTitle;
  const description = language === 'en'
    ? helpContent?.summary ?? schema?.description ?? ''
    : getFieldDescriptionZh(localizationKey, getFieldDescriptionZh(item.key, schema?.description));
  const hasError = issues.some((issue) => issue.severity === 'error');
  const [isPasswordEditable, setIsPasswordEditable] = useState(false);
  const controlId = `setting-${item.key}`;
  const isSensitive = Boolean(schema?.isSensitive);
  const sensitiveMode = sensitiveState?.mode ?? 'keep';
  const isSensitiveEditing = isSensitive && sensitiveMode === 'editing';
  const isSensitiveClear = isSensitive && sensitiveMode === 'clear';
  const displayValue = isSensitive && schema?.uiControl === 'password'
    ? isSensitiveEditing ? value : ''
    : resolveDisplayValue(item, value);
  const passwordEditable = isSensitive ? isSensitiveEditing || !sensitiveState?.isConfigured : isPasswordEditable;

  return (
    <div
      className={cn(
        'rounded-[1.15rem] border bg-[var(--settings-surface)] p-4 shadow-soft-card transition-[background-color,border-color,box-shadow] duration-200',
        hasError ? 'border-danger/40 hover:border-danger/55' : 'border-[var(--settings-border)] hover:border-[var(--settings-border-strong)]',
        'hover:bg-[var(--settings-surface-hover)]',
      )}
      data-testid={`settings-field-${item.key}`}
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <label className="text-sm font-semibold text-foreground" htmlFor={controlId}>
          {title}
        </label>
        <SettingsHelpButton
          fieldKey={localizationKey}
          title={title}
          schema={schema}
          description={description}
        />
        {schema?.isSensitive ? (
          <Badge variant="history" size="sm">
            {t('common.sensitive')}
          </Badge>
        ) : null}
        {!schema?.isEditable ? (
          <Badge variant="default" size="sm">
            {t('common.readOnly')}
          </Badge>
        ) : null}
      </div>

      {description ? (
        <p className="mb-3 max-w-full text-xs leading-5 text-muted-text">
          {description}
        </p>
      ) : null}

      <div>
        {renderFieldControl(
          item,
          displayValue,
          disabled,
          (nextValue) => onChange(item.key, nextValue),
          passwordEditable,
          () => setIsPasswordEditable(true),
          controlId,
          language,
          t,
        )}
      </div>

      {schema?.isSensitive ? (
        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={sensitiveState?.isConfigured ? 'success' : 'default'} size="sm">
              {sensitiveState?.isConfigured ? '已配置' : '未配置'}
            </Badge>
            {isSensitiveClear ? (
              <Badge variant="danger" size="sm">待清除</Badge>
            ) : null}
            {sensitiveState?.isConfigured ? (
              <>
                <Button
                  type="button"
                  variant="settings-secondary"
                  size="sm"
                  className="text-xs shadow-none"
                  disabled={disabled || !schema?.isEditable || isSensitiveEditing}
                  aria-label={`修改 ${title}`}
                  onClick={() => onBeginSensitiveEdit?.(item.key)}
                >
                  修改
                </Button>
                {isSensitiveEditing || isSensitiveClear ? (
                  <Button
                    type="button"
                    variant="settings-secondary"
                    size="sm"
                    className="text-xs shadow-none"
                    disabled={disabled || !schema?.isEditable}
                    aria-label={`取消修改 ${title}`}
                    onClick={() => onCancelSensitiveEdit?.(item.key)}
                  >
                    取消修改
                  </Button>
                ) : null}
                <Button
                  type="button"
                  variant="settings-secondary"
                  size="sm"
                  className="text-xs text-danger shadow-none"
                  disabled={disabled || !schema?.isEditable}
                  aria-label={`清除 ${title}`}
                  onClick={() => onRequestSensitiveClear?.(item.key)}
                >
                  清除
                </Button>
              </>
            ) : null}
          </div>
          <p className="text-[11px] leading-5 text-secondary-text">
            {t('settings.fieldSensitiveHint')}
            {isMultiValue ? t('settings.fieldSensitiveMultiHint') : ''}
            已保存值不会回显；清空输入框不会等同于清除，清除需点击按钮并确认。
          </p>
        </div>
      ) : null}

      {issues.length ? (
        <div className="mt-2 space-y-1">
          {issues.map((issue, index) => (
            <p
              key={`${issue.code}-${issue.key}-${index}`}
              className={issue.severity === 'error' ? 'text-xs text-danger' : 'text-xs text-warning'}
            >
              {issue.message}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
};
