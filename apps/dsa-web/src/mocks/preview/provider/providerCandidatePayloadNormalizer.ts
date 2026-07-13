import type { RealDailyReportDryRunInput } from '../dry-run/realDailyReportDryRunTypes'
import { validateRealDailyReportDryRunInput } from '../dry-run/realDailyReportDryRunValidator'
import type {
  ProviderCandidateMetric,
  ProviderCandidatePayload,
  ProviderCandidateRiskSignal,
  ProviderCandidateSection,
} from './providerCandidatePayloadFixture'
import { validateProviderCandidatePayload } from './providerCandidatePayloadValidator'

export interface ProviderCandidatePayloadNormalizationResult {
  readonly status: 'normalized' | 'blocked'
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
  readonly normalizedInput?: RealDailyReportDryRunInput
}

const PROJECT_NAME = '股票基金质量分析系统'
const REPORT_DISPLAY_NAME = 'AI股票基金每日信息报告'
const REDACTED_PROVIDER_LABEL = 'REDACTED_PROVIDER_LABEL'
const REDACTED_VALUE = 'REDACTED_VALUE'
const MOCK_AMOUNT = 'MOCK_AMOUNT'
const MOCK_RATIO = 'MOCK_RATIO'
const MOCK_FRESHNESS_LABEL = 'MOCK_FRESHNESS_LABEL'
const DRY_RUN_CONTRACT_VERSION = 'dry-run-contract-v1'
const MOCK_SCHEMA_VERSION = 'mock-schema-v1'
const DRY_RUN_REPORT_ID = 'DRY_RUN_REPORT_ID'

const blockedResult = (errors: readonly string[], warnings: readonly string[] = []): ProviderCandidatePayloadNormalizationResult => ({
  status: 'blocked',
  errors,
  warnings,
  fallbackMode: 'mock-only',
  canFallbackToMockOnly: true,
})

const normalizedResult = (
  normalizedInput: RealDailyReportDryRunInput,
  warnings: readonly string[],
): ProviderCandidatePayloadNormalizationResult => ({
  status: 'normalized',
  errors: [],
  warnings,
  fallbackMode: 'mock-only',
  canFallbackToMockOnly: true,
  normalizedInput,
})

const normalizeMetricValue = (metric: ProviderCandidateMetric): 'MOCK_AMOUNT' | 'MOCK_RATIO' | 'REDACTED_VALUE' => {
  if (metric.valueLabel === MOCK_AMOUNT) return MOCK_AMOUNT
  if (metric.valueLabel === MOCK_RATIO) return MOCK_RATIO
  return REDACTED_VALUE
}

const firstMetricValue = (
  metrics: readonly ProviderCandidateMetric[],
  expectedValue: 'MOCK_AMOUNT' | 'MOCK_RATIO',
): 'MOCK_AMOUNT' | 'MOCK_RATIO' | 'REDACTED_VALUE' => {
  const matchedMetric = metrics.find((metric) => normalizeMetricValue(metric) === expectedValue)
  return matchedMetric ? expectedValue : REDACTED_VALUE
}

const normalizeRiskSignal = (signal: ProviderCandidateRiskSignal | undefined): string => {
  if (!signal) return REDACTED_VALUE
  if (signal.levelLabel === 'MOCK_RISK_LEVEL') return 'MOCK_RISK_LEVEL'
  if (signal.valueLabel === 'MOCK_SIGNAL') return 'MOCK_SIGNAL'
  return REDACTED_VALUE
}

const normalizeSection = (
  section: ProviderCandidateSection,
  metrics: readonly ProviderCandidateMetric[],
): RealDailyReportDryRunInput['report']['sections'][number] => ({
  sectionId: section.sectionId,
  title: section.title,
  summary: REDACTED_VALUE,
  amountLabel: firstMetricValue(metrics, MOCK_AMOUNT),
  ratioLabel: firstMetricValue(metrics, MOCK_RATIO),
})

const buildDryRunInput = (input: ProviderCandidatePayload): RealDailyReportDryRunInput => ({
  contractVersion: DRY_RUN_CONTRACT_VERSION,
  mode: 'dry-run',
  dryRun: true,
  projectName: PROJECT_NAME,
  reportDisplayName: REPORT_DISPLAY_NAME,
  source: {
    sourceType: 'mock-only',
    providerName: REDACTED_PROVIDER_LABEL,
    isMock: true,
    isRealReadOnly: false,
    isRedacted: true,
    collectedAtLabel: input.dataFreshnessLabel === MOCK_FRESHNESS_LABEL ? MOCK_FRESHNESS_LABEL : REDACTED_VALUE,
  },
  report: {
    reportId: DRY_RUN_REPORT_ID,
    reportDateLabel: MOCK_FRESHNESS_LABEL,
    generatedAtLabel: MOCK_FRESHNESS_LABEL,
    title: REPORT_DISPLAY_NAME,
    headline: REDACTED_VALUE,
    marketMood: REDACTED_VALUE,
    riskLevel: normalizeRiskSignal(input.riskSignals[0]),
    portfolioAction: REDACTED_VALUE,
    sections: input.sections.map((section) => normalizeSection(section, input.metrics)),
  },
  safety: {
    allowRealProvider: false,
    allowRealAccountRead: false,
    allowNotificationSend: false,
    allowTrading: false,
    allowAiCall: false,
    requiresHumanApproval: true,
  },
  redaction: {
    containsRealAccountData: false,
    containsSecrets: false,
    containsWebhook: false,
    containsToken: false,
    containsApiKey: false,
    containsPersonalContact: false,
    redactionStatus: REDACTED_VALUE,
  },
  validation: {
    schemaVersion: MOCK_SCHEMA_VERSION,
    status: 'pending',
    errors: [],
    warnings: [],
  },
  rollback: {
    fallbackMode: 'mock-only',
    fallbackReason: 'mock-only fallback',
    canFallbackToMockOnly: true,
  },
})

export const normalizeProviderCandidatePayloadToDryRunInput = (
  input: ProviderCandidatePayload,
): ProviderCandidatePayloadNormalizationResult => {
  try {
    const candidateValidation = validateProviderCandidatePayload(input)
    if (candidateValidation.status === 'blocked') {
      return blockedResult(['candidate-validation.blocked'], candidateValidation.warnings)
    }

    const normalizedInput = buildDryRunInput(input)
    const dryRunValidation = validateRealDailyReportDryRunInput(normalizedInput)
    if (dryRunValidation.status === 'blocked') {
      return blockedResult(['normalized-dry-run-validation.blocked'], dryRunValidation.warnings)
    }

    return normalizedResult(normalizedInput, dryRunValidation.warnings)
  } catch {
    return blockedResult(['normalization.failed'])
  }
}
