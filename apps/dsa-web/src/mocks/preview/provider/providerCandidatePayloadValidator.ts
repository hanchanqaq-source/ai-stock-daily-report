import type {
  ProviderCandidateMetric,
  ProviderCandidatePayload,
  ProviderCandidateRiskSignal,
  ProviderCandidateSection,
} from './providerCandidatePayloadFixture'

export interface ProviderCandidatePayloadValidationResult {
  readonly status: 'passed' | 'blocked'
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
  readonly normalizationAllowed: boolean
}

type UnknownRecord = Record<string, unknown>

const REQUIRED_REDACTION_LABELS = ['REDACTED FIXTURE DATA', '静态脱敏候选数据', '非真实来源'] as const
const REQUIRED_SAFETY_LABELS = ['mock-only', 'dry-run only', '非真实账户', '不发送通知', '不交易', '不调用 AI'] as const
const REQUIRED_MOCK_ONLY_NOTE_FRAGMENTS = [
  '不是 RealDailyReportDryRunInput',
  '不是 DailyReportViewModel',
  'schema normalization',
  'validator passed 后才允许',
  '任意失败必须 fallback mock-only',
] as const

const EXACT_MOCK_VALUES = {
  candidateId: 'MOCK_PROVIDER_CANDIDATE_ID',
  candidateType: 'MOCK_CANDIDATE_TYPE',
  providerType: 'PROVIDER_TYPE_PLACEHOLDER',
  sourceLabel: 'REDACTED_PROVIDER_LABEL',
  dataFreshnessLabel: 'MOCK_FRESHNESS_LABEL',
} as const

const FORBIDDEN_RAW_OR_CREDENTIAL_KEYS = new Set([
  'rawresponse',
  'responsebody',
  'payloadraw',
  'providerrawresponse',
  'headers',
  'cookies',
  'requesturl',
  'endpoint',
  'token',
  'webhook',
  'apikey',
  'secret',
  'password',
  'credential',
  'authorization',
])

const safeResult = (errors: string[]): ProviderCandidatePayloadValidationResult => ({
  status: errors.length === 0 ? 'passed' : 'blocked',
  errors,
  warnings: [],
  fallbackMode: 'mock-only',
  canFallbackToMockOnly: true,
  normalizationAllowed: errors.length === 0,
})

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
const isNonEmptyString = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0
const isStringArray = (value: unknown): value is readonly string[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'string')
const hasAllLabels = (labels: readonly string[], requiredLabels: readonly string[]): boolean =>
  requiredLabels.every((requiredLabel) => labels.includes(requiredLabel))
const hasNoteFragment = (notes: readonly string[], fragment: string): boolean =>
  notes.some((note) => note.includes(fragment))
const isAllowedMockValue = (value: string): boolean =>
  value === 'MOCK_AMOUNT' ||
  value === 'MOCK_RATIO' ||
  value === 'REDACTED_VALUE' ||
  value === 'MOCK_METRIC' ||
  value.startsWith('MOCK_')

const appendError = (errors: string[], code: string, path?: string): void => {
  errors.push(path ? `${code}:${path}` : code)
}

const normalizeFieldName = (value: string): string => value.replace(/[_\s-]/g, '').toLowerCase()
const externalUrlPattern = new RegExp(
  `(?:${['ht', 'tp'].join('')}s?:\\/\\/|${['local', 'host'].join('')}|${['127', '0', '0', '1'].join('\\.')}|${['0', '0', '0', '0'].join('\\.')})`,
  'i',
)
const personalContactPattern = new RegExp(
  '(?:[A-Z0-9._%+-]+\\s*@\\s*[A-Z0-9.-]+\\.[A-Z]{2,}|1[3-9]\\d{9})',
  'i',
)
const secretMarkerPattern = new RegExp(
  ['tok' + 'en', 'web' + 'hook', 'api[_ -]?key', 'authorization', 'pass' + 'word', 'sec' + 'ret', 'bear' + 'er'].join('|'),
  'i',
)
const rawProviderValuePattern = new RegExp(
  ['raw' + 'Response', 'response' + 'Body', 'payload' + 'Raw', 'provider' + 'RawResponse', 'request' + 'Url'].join('|'),
  'i',
)
const preciseValuePattern = /(?:[$¥€]\s*\d+(?:,\d{3})*(?:\.\d{2,})?|\b\d+(?:,\d{3})*\.\d{2,}\b|\b\d+(?:\.\d+)?%\b)/
const realisticCodePattern = /\b(?:[0-9]{6}|hk\d{5})\b/i
const affirmativeTradePattern = /(?:^|[^不非无未勿没])(?:买入|卖出|清仓|加仓|减仓|自动交易|下单|执行交易)/

const scanString = (value: string, path: string, errors: string[]): void => {
  if (externalUrlPattern.test(value)) appendError(errors, 'sensitive-pattern.external-url', path)
  if (personalContactPattern.test(value)) appendError(errors, 'sensitive-pattern.personal-contact', path)
  if (secretMarkerPattern.test(value)) appendError(errors, 'sensitive-pattern.secret-marker', path)
  if (rawProviderValuePattern.test(value)) appendError(errors, 'sensitive-pattern.raw-provider-field', path)
  if (preciseValuePattern.test(value)) appendError(errors, 'sensitive-pattern.precise-value', path)
  if (realisticCodePattern.test(value) && !value.startsWith('MOCK_')) {
    appendError(errors, 'sensitive-pattern.realistic-code', path)
  }
  if (affirmativeTradePattern.test(value)) appendError(errors, 'riskSignal.invalid', path)
}

const scanSensitiveContent = (value: unknown, path: string, errors: string[]): void => {
  if (typeof value === 'string') {
    scanString(value, path, errors)
    return
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => scanSensitiveContent(item, `${path}[${index}]`, errors))
    return
  }
  if (isRecord(value)) {
    for (const [key, item] of Object.entries(value)) {
      const fieldPath = `${path}.${key}`
      if (FORBIDDEN_RAW_OR_CREDENTIAL_KEYS.has(normalizeFieldName(key))) {
        appendError(errors, 'sensitive-pattern.raw-provider-field', fieldPath)
      }
      scanSensitiveContent(item, fieldPath, errors)
    }
  }
}

const validateSection = (section: unknown, index: number, errors: string[]): void => {
  if (!isRecord(section)) {
    appendError(errors, 'section.invalid', `input.sections[${index}]`)
    return
  }
  const candidate = section as Partial<ProviderCandidateSection>
  if (
    !isNonEmptyString(candidate.sectionId) ||
    !isNonEmptyString(candidate.title) ||
    !isNonEmptyString(candidate.summary) ||
    !isStringArray(candidate.notes)
  ) {
    appendError(errors, 'section.invalid', `input.sections[${index}]`)
  }
}

const validateMetric = (metric: unknown, index: number, errors: string[]): void => {
  if (!isRecord(metric)) {
    appendError(errors, 'metric.invalid', `input.metrics[${index}]`)
    return
  }
  const candidate = metric as Partial<ProviderCandidateMetric>
  if (
    !isNonEmptyString(candidate.metricId) ||
    !isNonEmptyString(candidate.label) ||
    !isNonEmptyString(candidate.valueLabel) ||
    !isNonEmptyString(candidate.unitLabel) ||
    !isStringArray(candidate.notes)
  ) {
    appendError(errors, 'metric.invalid', `input.metrics[${index}]`)
    return
  }
  if (!isAllowedMockValue(candidate.valueLabel)) {
    appendError(errors, 'metric.valueLabel.invalid', `input.metrics[${index}].valueLabel`)
  }
}

const validateRiskSignal = (signal: unknown, index: number, errors: string[]): void => {
  if (!isRecord(signal)) {
    appendError(errors, 'riskSignal.invalid', `input.riskSignals[${index}]`)
    return
  }
  const candidate = signal as Partial<ProviderCandidateRiskSignal>
  if (
    !isNonEmptyString(candidate.signalId) ||
    !isNonEmptyString(candidate.label) ||
    !isNonEmptyString(candidate.levelLabel) ||
    !isNonEmptyString(candidate.valueLabel) ||
    !isStringArray(candidate.notes)
  ) {
    appendError(errors, 'riskSignal.invalid', `input.riskSignals[${index}]`)
    return
  }
  if (!isAllowedMockValue(candidate.levelLabel)) {
    appendError(errors, 'riskSignal.levelLabel.invalid', `input.riskSignals[${index}].levelLabel`)
  }
  if (!isAllowedMockValue(candidate.valueLabel)) {
    appendError(errors, 'riskSignal.valueLabel.invalid', `input.riskSignals[${index}].valueLabel`)
  }
}

export const validateProviderCandidatePayload = (
  input: ProviderCandidatePayload,
): ProviderCandidatePayloadValidationResult => {
  const errors: string[] = []
  if (!isRecord(input)) return safeResult(['input.invalid-object'])

  const candidate = input as Partial<ProviderCandidatePayload>
  for (const [fieldName, expectedValue] of Object.entries(EXACT_MOCK_VALUES)) {
    const actualValue = candidate[fieldName as keyof typeof EXACT_MOCK_VALUES]
    if (!isNonEmptyString(actualValue)) appendError(errors, `${fieldName}.invalid`)
    else if (actualValue !== expectedValue) appendError(errors, 'candidate.not-mock-only', `input.${fieldName}`)
  }

  if (!Array.isArray(candidate.sections) || candidate.sections.length === 0) appendError(errors, 'sections.required')
  else candidate.sections.forEach((section, index) => validateSection(section, index, errors))

  if (!Array.isArray(candidate.metrics) || candidate.metrics.length === 0) appendError(errors, 'metrics.required')
  else candidate.metrics.forEach((metric, index) => validateMetric(metric, index, errors))

  if (!Array.isArray(candidate.riskSignals) || candidate.riskSignals.length === 0) {
    appendError(errors, 'riskSignals.required')
  } else candidate.riskSignals.forEach((signal, index) => validateRiskSignal(signal, index, errors))

  if (!isStringArray(candidate.redactionLabels)) appendError(errors, 'redactionLabels.required')
  else if (!hasAllLabels(candidate.redactionLabels, REQUIRED_REDACTION_LABELS)) appendError(errors, 'redactionLabel.missing')

  if (!isStringArray(candidate.safetyLabels)) appendError(errors, 'safetyLabels.required')
  else if (!hasAllLabels(candidate.safetyLabels, REQUIRED_SAFETY_LABELS)) appendError(errors, 'safetyLabel.missing')

  if (!isStringArray(candidate.mockOnlyNotes)) appendError(errors, 'mockOnlyNotes.required')
  else {
    for (const fragment of REQUIRED_MOCK_ONLY_NOTE_FRAGMENTS) {
      if (!hasNoteFragment(candidate.mockOnlyNotes, fragment)) appendError(errors, 'mockOnlyNote.missing')
    }
  }

  scanSensitiveContent(input, 'input', errors)
  return safeResult([...new Set(errors)])
}
