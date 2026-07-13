import type { RealDailyReportDryRunInput, RealDailyReportDryRunSourceType } from './realDailyReportDryRunTypes'

export interface RealDailyReportDryRunValidationResult {
  readonly status: 'passed' | 'blocked'
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
}

const PROJECT_NAME = '股票基金质量分析系统'
const REPORT_DISPLAY_NAME = 'AI股票基金每日信息报告'
const ALLOWED_SOURCE_TYPES = new Set<RealDailyReportDryRunSourceType>(['mock-only', 'dry-run', 'real-readonly'])
const VALUE_PATH_SEPARATOR = '.'

const suspiciousValuePatterns = [
  { pattern: new RegExp(['h', 'ttps?://'].join(''), 'i'), code: 'sensitive-pattern.external-url' },
  { pattern: new RegExp(['web', 'hook'].join(''), 'i'), code: 'sensitive-pattern.delivery-endpoint' },
  { pattern: new RegExp(['tok', 'en'].join(''), 'i'), code: 'sensitive-pattern.secret-marker' },
  { pattern: new RegExp(['api', '[_-]?key'].join(''), 'i'), code: 'sensitive-pattern.secret-marker' },
  { pattern: /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i, code: 'sensitive-pattern.personal-contact' },
  { pattern: /(?:\+?\d[\s-]?){8,}/, code: 'sensitive-pattern.personal-contact' },
] as const

const makeResult = (errors: string[], warnings: string[] = []): RealDailyReportDryRunValidationResult => ({
  status: errors.length === 0 ? 'passed' : 'blocked',
  errors,
  warnings,
  fallbackMode: 'mock-only',
  canFallbackToMockOnly: true,
})

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const collectSuspiciousValueErrors = (value: unknown, path = 'input'): string[] => {
  if (typeof value === 'string') {
    const matchedPattern = suspiciousValuePatterns.find(({ pattern }) => pattern.test(value))
    return matchedPattern ? [`${matchedPattern.code}:${path}`] : []
  }

  if (Array.isArray(value)) {
    return value.flatMap((item, index) => collectSuspiciousValueErrors(item, `${path}[${index}]`))
  }

  if (isRecord(value)) {
    return Object.entries(value).flatMap(([key, childValue]) =>
      collectSuspiciousValueErrors(childValue, `${path}${VALUE_PATH_SEPARATOR}${key}`),
    )
  }

  return []
}

export const validateRealDailyReportDryRunInput = (
  input: RealDailyReportDryRunInput,
): RealDailyReportDryRunValidationResult => {
  const errors: string[] = []

  if (!isRecord(input)) {
    return makeResult(['input.invalid-object'])
  }

  if (typeof input.contractVersion !== 'string' || input.contractVersion.trim().length === 0) {
    errors.push('contractVersion.required')
  }
  if (input.mode !== 'dry-run') errors.push('mode.must-be-dry-run')
  if (input.dryRun !== true) errors.push('dryRun.must-be-true')
  if (input.projectName !== PROJECT_NAME) errors.push('projectName.invalid')
  if (input.reportDisplayName !== REPORT_DISPLAY_NAME) errors.push('reportDisplayName.invalid')

  if (!isRecord(input.source)) {
    errors.push('source.invalid')
  } else if (!ALLOWED_SOURCE_TYPES.has(input.source.sourceType as RealDailyReportDryRunSourceType)) {
    errors.push('source.sourceType.invalid')
  }

  if (!isRecord(input.report)) {
    errors.push('report.invalid')
  } else {
    if (input.report.title !== REPORT_DISPLAY_NAME) errors.push('report.title.invalid')
    if (!Array.isArray(input.report.sections) || input.report.sections.length === 0) {
      errors.push('report.sections.required')
    }
  }

  if (!isRecord(input.safety)) {
    errors.push('safety.invalid')
  } else {
    if (input.safety.allowRealProvider !== false) errors.push('safety.allowRealProvider.must-be-false')
    if (input.safety.allowRealAccountRead !== false) errors.push('safety.allowRealAccountRead.must-be-false')
    if (input.safety.allowNotificationSend !== false) errors.push('safety.allowNotificationSend.must-be-false')
    if (input.safety.allowTrading !== false) errors.push('safety.allowTrading.must-be-false')
    if (input.safety.allowAiCall !== false) errors.push('safety.allowAiCall.must-be-false')
    if (input.safety.requiresHumanApproval !== true) errors.push('safety.requiresHumanApproval.must-be-true')
  }

  if (!isRecord(input.redaction)) {
    errors.push('redaction.invalid')
  } else {
    if (input.redaction.containsSecrets !== false) errors.push('redaction.containsSecrets.must-be-false')
    if (input.redaction.containsWebhook !== false) errors.push('redaction.containsWebhook.must-be-false')
    if (input.redaction.containsToken !== false) errors.push('redaction.containsToken.must-be-false')
    if (input.redaction.containsApiKey !== false) errors.push('redaction.containsApiKey.must-be-false')
    if (input.redaction.containsPersonalContact !== false) errors.push('redaction.containsPersonalContact.must-be-false')
  }

  if (!isRecord(input.rollback)) {
    errors.push('rollback.invalid')
  } else {
    if (input.rollback.fallbackMode !== 'mock-only') errors.push('rollback.fallbackMode.must-be-mock-only')
    if (input.rollback.canFallbackToMockOnly !== true) errors.push('rollback.canFallbackToMockOnly.must-be-true')
  }

  if (!isRecord(input.validation)) {
    errors.push('validation.invalid')
  } else {
    if (!Array.isArray(input.validation.errors)) errors.push('validation.errors.must-be-array')
    if (!Array.isArray(input.validation.warnings)) errors.push('validation.warnings.must-be-array')
  }

  errors.push(...collectSuspiciousValueErrors(input))

  return makeResult([...new Set(errors)])
}
