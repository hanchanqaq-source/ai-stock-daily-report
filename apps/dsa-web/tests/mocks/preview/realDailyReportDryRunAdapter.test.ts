import { describe, expect, it } from 'vitest'
import { adaptRealDailyReportDryRunInputToViewModel } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunAdapter'
import type { RealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunTypes'

const MOCK_AMOUNT = 'MOCK_AMOUNT'
const MOCK_RATIO = 'MOCK_RATIO'
const REDACTED_VALUE = 'REDACTED_VALUE'
const REDACTED_PROVIDER_LABEL = 'REDACTED_PROVIDER_LABEL'
const DRY_RUN_REPORT_ID = 'DRY_RUN_REPORT_ID'
const DRY_RUN_DATE_LABEL = 'DRY_RUN_DATE_LABEL'
const DRY_RUN_GENERATED_LABEL = 'DRY_RUN_GENERATED_LABEL'
const DRY_RUN_HEADLINE_REDACTED = 'DRY_RUN_HEADLINE_REDACTED'

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
    generatedAtLabel: DRY_RUN_GENERATED_LABEL,
    title: 'AI股票基金每日信息报告',
    headline: DRY_RUN_HEADLINE_REDACTED,
    marketMood: REDACTED_VALUE,
    riskLevel: REDACTED_VALUE,
    portfolioAction: REDACTED_VALUE,
    sections: [
      {
        sectionId: 'mock-section-1',
        title: '市场概览',
        summary: '静态脱敏草案，仅用于映射检查',
        amountLabel: MOCK_AMOUNT,
        ratioLabel: MOCK_RATIO,
      },
      {
        sectionId: 'mock-section-2',
        title: '组合观察',
        summary: REDACTED_VALUE,
        amountLabel: REDACTED_VALUE,
        ratioLabel: REDACTED_VALUE,
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
  readonly report: Record<string, unknown> & { sections: Record<string, unknown>[] }
  readonly safety: Record<string, unknown>
  readonly redaction: Record<string, unknown>
}

const adaptMutation = (mutate: (payload: MutableDryRunPayload) => void) => {
  const payload = createValidPayload() as unknown as MutableDryRunPayload
  mutate(payload)
  return adaptRealDailyReportDryRunInputToViewModel(payload as unknown as RealDailyReportDryRunInput)
}

describe('real daily report dry-run adapter', () => {
  it('adapts a valid dry-run payload after validator passes', () => {
    const result = adaptRealDailyReportDryRunInputToViewModel(createValidPayload())

    expect(result.status).toBe('adapted')
    expect(result.validationStatus).toBe('passed')
    expect(result.fallbackMode).toBe('mock-only')
    expect(result.canFallbackToMockOnly).toBe(true)
    expect(result.viewModel).toBeDefined()
    expect(result.viewModel).toMatchObject({
      id: DRY_RUN_REPORT_ID,
      projectName: '股票基金质量分析系统',
      title: 'AI股票基金每日信息报告',
      displayName: 'AI股票基金每日信息报告',
      dataSourceLabel: `${REDACTED_PROVIDER_LABEL} / dry-run / REDACTED / 非真实运行`,
      deliveryStatus: 'dry-run 未发送：不通知、不交易、不调用 AI',
    })
    expect(result.viewModel?.safetyLabels).toEqual(
      expect.arrayContaining(['dry-run 非真实运行', '不发送通知', '不交易', '不调用 AI']),
    )
    expect(result.viewModel?.redactionLabels).toEqual(expect.arrayContaining(['REDACTED dry-run input', '不读取凭据']))
  })

  it('redacts providerName before it can enter the view model', () => {
    const providerName = '真实来源占位名称'
    const result = adaptMutation((payload) => {
      payload.source.providerName = providerName
    })

    expect(result.status).toBe('adapted')
    expect(result.viewModel?.dataSourceLabel).toBe(`${REDACTED_PROVIDER_LABEL} / dry-run / REDACTED / 非真实运行`)
    expect(JSON.stringify(result.viewModel)).not.toContain(providerName)
  })

  it('keeps section order stable and maps only low-sensitivity section labels', () => {
    const result = adaptRealDailyReportDryRunInputToViewModel(createValidPayload())

    expect(result.viewModel?.sections).toEqual([
      {
        title: '市场概览',
        content: `静态脱敏草案，仅用于映射检查；amountLabel=${MOCK_AMOUNT}；ratioLabel=${MOCK_RATIO}`,
      },
      {
        title: '组合观察',
        content: `${REDACTED_VALUE}；amountLabel=${REDACTED_VALUE}；ratioLabel=${REDACTED_VALUE}`,
      },
    ])
  })

  it.each([
    ['non dry-run mode', (payload: MutableDryRunPayload) => (payload.mode = 'mock'), 'mode.must-be-dry-run'],
    [
      'allowTrading=true',
      (payload: MutableDryRunPayload) => (payload.safety.allowTrading = true),
      'safety.allowTrading.must-be-false',
    ],
    [
      'allowNotificationSend=true',
      (payload: MutableDryRunPayload) => (payload.safety.allowNotificationSend = true),
      'safety.allowNotificationSend.must-be-false',
    ],
    [
      'allowAiCall=true',
      (payload: MutableDryRunPayload) => (payload.safety.allowAiCall = true),
      'safety.allowAiCall.must-be-false',
    ],
    [
      'containsToken=true',
      (payload: MutableDryRunPayload) => (payload.redaction.containsToken = true),
      'redaction.containsToken.must-be-false',
    ],
    [
      'containsApiKey=true',
      (payload: MutableDryRunPayload) => (payload.redaction.containsApiKey = true),
      'redaction.containsApiKey.must-be-false',
    ],
    [
      'containsWebhook=true',
      (payload: MutableDryRunPayload) => (payload.redaction.containsWebhook = true),
      'redaction.containsWebhook.must-be-false',
    ],
    ['empty sections', (payload: MutableDryRunPayload) => (payload.report.sections = []), 'report.sections.required'],
  ])('returns blocked mock-only fallback for %s', (_name, mutate, expectedError) => {
    const result = adaptMutation(mutate)

    expect(result.status).toBe('blocked')
    expect(result.validationStatus).toBe('blocked')
    expect(result.fallbackMode).toBe('mock-only')
    expect(result.canFallbackToMockOnly).toBe(true)
    expect(result.errors).toContain(expectedError)
    expect(result.viewModel).toBeUndefined()
  })

  it('blocks suspicious external markers without echoing sensitive raw text', () => {
    const suspiciousValue = ['h', 'ttps://example.invalid/mock-', 'tok', 'en'].join('')
    const result = adaptMutation((payload) => {
      payload.report.headline = suspiciousValue
    })

    expect(result.status).toBe('blocked')
    expect(result.errors).toEqual(expect.arrayContaining(['sensitive-pattern.external-url:input.report.headline']))
    expect(result.errors.join('\n')).not.toContain(suspiciousValue)
    expect(result.viewModel).toBeUndefined()
  })

  it('does not throw for malformed blocked input', () => {
    expect(() => adaptRealDailyReportDryRunInputToViewModel(null as unknown as RealDailyReportDryRunInput)).not.toThrow()
    expect(adaptRealDailyReportDryRunInputToViewModel(null as unknown as RealDailyReportDryRunInput)).toMatchObject({
      status: 'blocked',
      validationStatus: 'blocked',
      fallbackMode: 'mock-only',
      canFallbackToMockOnly: true,
    })
  })

  it('does not mutate the input payload', () => {
    const payload = createValidPayload()
    const snapshot = JSON.stringify(payload)

    adaptRealDailyReportDryRunInputToViewModel(payload)

    expect(JSON.stringify(payload)).toBe(snapshot)
  })

  it('redacts section values that look like real holdings, precise amounts, codes, or contacts', () => {
    const result = adaptMutation((payload) => {
      payload.report.sections[0].summary = 'AAPL FUNDX contact example at mail dot invalid'
      payload.report.sections[0].amountLabel = '123456.78'
      payload.report.sections[0].ratioLabel = '12.34%'
    })

    expect(result.status).toBe('adapted')
    const viewModelText = JSON.stringify(result.viewModel)
    expect(viewModelText).not.toContain('AAPL')
    expect(viewModelText).not.toContain('FUNDX')
    expect(viewModelText).not.toContain('123456.78')
    expect(viewModelText).not.toContain('12.34%')
    expect(viewModelText).not.toContain('mail dot invalid')
    expect(viewModelText).toContain(REDACTED_VALUE)
  })
})
