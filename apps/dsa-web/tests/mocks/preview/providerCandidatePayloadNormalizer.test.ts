import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE,
  type ProviderCandidatePayload,
} from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { normalizeProviderCandidatePayloadToDryRunInput } from '../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'

type Mutable<T> = { -readonly [P in keyof T]: T[P] extends readonly (infer U)[] ? Mutable<U>[] : T[P] }
type MutableProviderCandidatePayload = Mutable<ProviderCandidatePayload>

const clonePayload = (): MutableProviderCandidatePayload =>
  structuredClone(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE) as MutableProviderCandidatePayload

const stringify = (value: unknown): string => JSON.stringify(value)
const forbiddenTradeWords = ['买入', '卖出', '加仓', '减仓', '清仓', '下单', '交易建议'] as const
const forbiddenRawFields = [
  'candidatePayload',
  'rawCandidate',
  'rawResponse',
  'providerResponse',
  'requestUrl',
  'endpoint',
  'token',
  'webhook',
  'apiKey',
  'headers',
  'cookies',
  'accountId',
  'transaction',
  'viewModel',
  'DailyReportViewModel',
  'normalizedRawData',
] as const

describe('provider candidate payload normalizer', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.resetModules()
  })

  it('normalizes the Web-P45 fixture into a valid RealDailyReportDryRunInput with fixed safety switches', () => {
    const result = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)

    expect(result.status).toBe('normalized')
    expect(result.errors).toEqual([])
    expect(result.fallbackMode).toBe('mock-only')
    expect(result.canFallbackToMockOnly).toBe(true)
    expect(result.normalizedInput).toBeDefined()
    expect(result).not.toHaveProperty('viewModel')
    expect(result).not.toHaveProperty('DailyReportViewModel')

    const normalizedInput = result.normalizedInput!
    expect(validateRealDailyReportDryRunInput(normalizedInput).status).toBe('passed')
    expect(normalizedInput.mode).toBe('dry-run')
    expect(normalizedInput.dryRun).toBe(true)
    expect(normalizedInput.projectName).toBe('股票基金质量分析系统')
    expect(normalizedInput.reportDisplayName).toBe('AI股票基金每日信息报告')
    expect(normalizedInput.safety.allowNotificationSend).toBe(false)
    expect(normalizedInput.safety.allowTrading).toBe(false)
    expect(normalizedInput.safety.allowAiCall).toBe(false)
    expect(normalizedInput.safety.requiresHumanApproval).toBe(true)
    expect(normalizedInput.rollback.fallbackMode).toBe('mock-only')
    expect(normalizedInput.rollback.canFallbackToMockOnly).toBe(true)
    expect(normalizedInput.source.providerName).toBe('REDACTED_PROVIDER_LABEL')
  })

  it('does not expose provider identity, candidate id, raw provider response fields, or a view model', () => {
    const result = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    expect(result.status).toBe('normalized')
    const serialized = stringify(result)

    expect(serialized).not.toContain(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.providerType)
    expect(serialized).not.toContain(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.candidateId)
    for (const forbiddenField of forbiddenRawFields) expect(serialized).not.toContain(forbiddenField)
  })

  it('keeps section order stable and maps only low-sensitivity metric labels', () => {
    const result = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    expect(result.status).toBe('normalized')
    const normalizedSections = result.normalizedInput!.report.sections

    expect(normalizedSections.map((section) => section.sectionId)).toEqual(
      MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.sections.map((section) => section.sectionId),
    )
    expect(normalizedSections.map((section) => section.title)).toEqual(
      MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.sections.map((section) => section.title),
    )
    for (const section of normalizedSections) {
      expect(['MOCK_AMOUNT', 'MOCK_RATIO', 'REDACTED_VALUE']).toContain(section.amountLabel)
      expect(['MOCK_AMOUNT', 'MOCK_RATIO', 'REDACTED_VALUE']).toContain(section.ratioLabel)
      expect(section.summary).toBe('REDACTED_VALUE')
    }
  })

  it('normalizes risk signals without producing trading instructions', () => {
    const result = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    expect(result.status).toBe('normalized')
    const riskText = stringify({
      riskLevel: result.normalizedInput!.report.riskLevel,
      portfolioAction: result.normalizedInput!.report.portfolioAction,
    })
    for (const forbiddenWord of forbiddenTradeWords) expect(riskText).not.toContain(forbiddenWord)
  })

  it('blocks before normalization when the candidate validator rejects drift or raw fields', () => {
    const cases: MutableProviderCandidatePayload[] = []

    const providerTypeDrift = clonePayload()
    providerTypeDrift.providerType = 'MOCK_EXTERNAL_PROVIDER_TYPE'
    cases.push(providerTypeDrift)

    const sourceLabelDrift = clonePayload()
    sourceLabelDrift.sourceLabel = 'MOCK_EXTERNAL_SOURCE_LABEL'
    cases.push(sourceLabelDrift)

    const missingSafetyLabel = clonePayload()
    missingSafetyLabel.safetyLabels = ['mock-only', 'dry-run only', '非真实账户', '不发送通知', '不交易']
    cases.push(missingSafetyLabel)

    const externalMarker = clonePayload()
    externalMarker.sections[0].summary = ['ht', 'tps://', 'mock.invalid'].join('')
    cases.push(externalMarker)

    const rawResponsePayload = clonePayload() as MutableProviderCandidatePayload & Record<string, unknown>
    rawResponsePayload.rawResponse = 'MOCK_EXTERNAL_RAW_VALUE'
    cases.push(rawResponsePayload)

    for (const candidate of cases) {
      const result = normalizeProviderCandidatePayloadToDryRunInput(candidate)
      expect(result.status).toBe('blocked')
      expect(result.errors).toEqual(['candidate-validation.blocked'])
      expect(result.normalizedInput).toBeUndefined()
      expect(stringify(result)).not.toContain('MOCK_EXTERNAL_RAW_VALUE')
      expect(stringify(result)).not.toContain(candidate.candidateId)
    }
  })

  it('returns blocked without normalizedInput when dry-run validation blocks the normalized payload', async () => {
    vi.resetModules()
    vi.doMock('../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator', () => ({
      validateRealDailyReportDryRunInput: vi.fn(() => ({
        status: 'blocked',
        errors: ['mocked-dry-run-error-without-raw-value'],
        warnings: [],
        fallbackMode: 'mock-only',
        canFallbackToMockOnly: true,
      })),
    }))

    const { normalizeProviderCandidatePayloadToDryRunInput: normalizeWithBlockedDryRun } = await import(
      '../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer'
    )
    const result = normalizeWithBlockedDryRun(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)

    expect(result.status).toBe('blocked')
    expect(result.errors).toEqual(['normalized-dry-run-validation.blocked'])
    expect(result.fallbackMode).toBe('mock-only')
    expect(result.canFallbackToMockOnly).toBe(true)
    expect(result.normalizedInput).toBeUndefined()
    expect(stringify(result)).not.toContain(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.sourceLabel)
  })

  it('does not mutate input, works with the frozen fixture, and returns deterministic output', () => {
    const payload = clonePayload()
    const before = stringify(payload)
    const first = normalizeProviderCandidatePayloadToDryRunInput(payload)
    const second = normalizeProviderCandidatePayloadToDryRunInput(payload)

    expect(stringify(payload)).toBe(before)
    expect(Object.isFrozen(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)).toBe(true)
    expect(normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE).status).toBe(
      'normalized',
    )
    expect(second).toEqual(first)
  })

  it('does not call the dry-run adapter or access network, file, browser storage, environment, time, or random globals', async () => {
    const forbidden = vi.fn(() => {
      throw new Error('external capability must not be used')
    })
    vi.stubGlobal('fetch', forbidden)
    vi.stubGlobal('XMLHttpRequest', forbidden)
    vi.stubGlobal('WebSocket', forbidden)
    vi.stubGlobal('localStorage', { getItem: forbidden })
    vi.stubGlobal('sessionStorage', { getItem: forbidden })
    vi.stubGlobal('indexedDB', forbidden)
    const processEnvSpy = vi.spyOn(process, 'env', 'get')
    const dateNowSpy = vi.spyOn(Date, 'now')
    const randomSpy = vi.spyOn(Math, 'random')

    const adapter = await import('../../../src/mocks/preview/dry-run/realDailyReportDryRunAdapter')
    const adapterSpy = vi.spyOn(adapter, 'adaptRealDailyReportDryRunInputToViewModel')

    expect(normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE).status).toBe(
      'normalized',
    )
    expect(adapterSpy).not.toHaveBeenCalled()
    expect(forbidden).not.toHaveBeenCalled()
    expect(processEnvSpy).not.toHaveBeenCalled()
    expect(dateNowSpy).not.toHaveBeenCalled()
    expect(randomSpy).not.toHaveBeenCalled()
  })
})
