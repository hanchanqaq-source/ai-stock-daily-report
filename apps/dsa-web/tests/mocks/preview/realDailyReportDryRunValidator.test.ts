import { describe, expect, it } from 'vitest'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'
import type { RealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunTypes'

const MOCK_AMOUNT = 'MOCK_AMOUNT'
const MOCK_RATIO = 'MOCK_RATIO'
const REDACTED_VALUE = 'REDACTED_VALUE'
const REDACTED_PROVIDER_LABEL = 'REDACTED_PROVIDER_LABEL'
const DRY_RUN_REPORT_ID = 'DRY_RUN_REPORT_ID'
const DRY_RUN_DATE_LABEL = 'DRY_RUN_DATE_LABEL'

const createValidPayload = (): RealDailyReportDryRunInput => ({
  contractVersion: 'dry-run-contract-v1',
  mode: 'dry-run',
  dryRun: true,
  projectName: '股票基金质量分析系统',
  reportDisplayName: 'AI股票基金每日信息报告',
  source: {
    sourceType: 'mock-only',
    providerName: REDACTED_PROVIDER_LABEL,
    isMock: true,
    isRealReadOnly: false,
    isRedacted: true,
    collectedAtLabel: DRY_RUN_DATE_LABEL,
  },
  report: {
    reportId: DRY_RUN_REPORT_ID,
    reportDateLabel: DRY_RUN_DATE_LABEL,
    generatedAtLabel: DRY_RUN_DATE_LABEL,
    title: 'AI股票基金每日信息报告',
    headline: REDACTED_VALUE,
    marketMood: REDACTED_VALUE,
    riskLevel: REDACTED_VALUE,
    portfolioAction: REDACTED_VALUE,
    sections: [
      {
        sectionId: 'mock-section-1',
        title: REDACTED_VALUE,
        summary: REDACTED_VALUE,
        amountLabel: MOCK_AMOUNT,
        ratioLabel: MOCK_RATIO,
      },
    ],
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
    schemaVersion: 'mock-schema-v1',
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

type MutableDryRunPayload = Record<string, unknown> & {
  readonly source: Record<string, unknown>
  readonly report: Record<string, unknown> & { readonly sections: Record<string, unknown>[] }
  readonly safety: Record<string, unknown>
  readonly redaction: Record<string, unknown>
  readonly rollback: Record<string, unknown>
}

const validateMutation = (mutate: (payload: MutableDryRunPayload) => void) => {
  const payload = createValidPayload() as unknown as MutableDryRunPayload
  mutate(payload)
  return validateRealDailyReportDryRunInput(payload as RealDailyReportDryRunInput)
}

describe('real daily report dry-run validator', () => {
  it('passes a valid dry-run mock payload', () => {
    expect(validateRealDailyReportDryRunInput(createValidPayload())).toEqual({
      status: 'passed',
      errors: [],
      warnings: [],
      fallbackMode: 'mock-only',
      canFallbackToMockOnly: true,
    })
  })

  it.each([
    ['blocks a non dry-run mode', (payload: MutableDryRunPayload) => (payload.mode = 'preview'), 'mode.must-be-dry-run'],
    ['blocks dryRun=false', (payload: MutableDryRunPayload) => (payload.dryRun = false), 'dryRun.must-be-true'],
    ['blocks an invalid project name', (payload: MutableDryRunPayload) => (payload.projectName = '错误项目'), 'projectName.invalid'],
    [
      'blocks an invalid report display name',
      (payload: MutableDryRunPayload) => (payload.reportDisplayName = '错误日报'),
      'reportDisplayName.invalid',
    ],
    [
      'blocks allowNotificationSend=true',
      (payload: MutableDryRunPayload) => (payload.safety.allowNotificationSend = true),
      'safety.allowNotificationSend.must-be-false',
    ],
    [
      'blocks allowTrading=true',
      (payload: MutableDryRunPayload) => (payload.safety.allowTrading = true),
      'safety.allowTrading.must-be-false',
    ],
    [
      'blocks allowAiCall=true',
      (payload: MutableDryRunPayload) => (payload.safety.allowAiCall = true),
      'safety.allowAiCall.must-be-false',
    ],
    [
      'blocks containsSecrets=true',
      (payload: MutableDryRunPayload) => (payload.redaction.containsSecrets = true),
      'redaction.containsSecrets.must-be-false',
    ],
    [
      'blocks containsWebhook=true',
      (payload: MutableDryRunPayload) => (payload.redaction.containsWebhook = true),
      'redaction.containsWebhook.must-be-false',
    ],
    [
      'blocks containsToken=true',
      (payload: MutableDryRunPayload) => (payload.redaction.containsToken = true),
      'redaction.containsToken.must-be-false',
    ],
    [
      'blocks containsApiKey=true',
      (payload: MutableDryRunPayload) => (payload.redaction.containsApiKey = true),
      'redaction.containsApiKey.must-be-false',
    ],
    [
      'blocks containsPersonalContact=true',
      (payload: MutableDryRunPayload) => (payload.redaction.containsPersonalContact = true),
      'redaction.containsPersonalContact.must-be-false',
    ],
    [
      'blocks a non mock-only fallback mode',
      (payload: MutableDryRunPayload) => (payload.rollback.fallbackMode = 'real-provider'),
      'rollback.fallbackMode.must-be-mock-only',
    ],
    [
      'blocks canFallbackToMockOnly=false',
      (payload: MutableDryRunPayload) => (payload.rollback.canFallbackToMockOnly = false),
      'rollback.canFallbackToMockOnly.must-be-true',
    ],
    [
      'blocks empty sections',
      (payload: MutableDryRunPayload) => (payload.report.sections = []),
      'report.sections.required',
    ],
  ])('%s', (_name, mutate, expectedError) => {
    const result = validateMutation(mutate)
    expect(result.status).toBe('blocked')
    expect(result.fallbackMode).toBe('mock-only')
    expect(result.canFallbackToMockOnly).toBe(true)
    expect(result.errors).toContain(expectedError)
  })

  it('blocks suspicious external URL text without throwing', () => {
    const result = validateMutation((payload) => {
      payload.report.headline = ['h', 'ttps://example.invalid/mock'].join('')
    })
    expect(result.status).toBe('blocked')
    expect(result.errors).toContain('sensitive-pattern.external-url:input.report.headline')
  })

  it('blocks suspicious secret marker text without throwing', () => {
    const result = validateMutation((payload) => {
      payload.report.headline = ['mock ', 'api', '_key marker'].join('')
    })
    expect(result.status).toBe('blocked')
    expect(result.errors).toContain('sensitive-pattern.secret-marker:input.report.headline')
  })

  it('returns low-sensitivity errors and never echoes suspicious raw values', () => {
    const suspiciousValue = ['mock-', 'tok', 'en-value'].join('')
    const result = validateMutation((payload) => {
      payload.report.sections[0].summary = suspiciousValue
    })
    expect(result.status).toBe('blocked')
    expect(() => validateRealDailyReportDryRunInput({ report: suspiciousValue } as unknown as RealDailyReportDryRunInput)).not.toThrow()
    expect(result.errors.join('\n')).not.toContain(suspiciousValue)
  })
})
