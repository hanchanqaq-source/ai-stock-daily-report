import { readFileSync } from 'node:fs'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunTypes'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'
import {
  MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE,
  type ProviderCandidatePayload,
} from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { normalizeProviderCandidatePayloadToDryRunInput } from '../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer'
import { validateProviderCandidatePayload } from '../../../src/mocks/preview/provider/providerCandidatePayloadValidator'

type Mutable<T> = { -readonly [P in keyof T]: T[P] extends readonly (infer U)[] ? Mutable<U>[] : T[P] }
type MutableCandidate = Mutable<ProviderCandidatePayload> & Record<string, unknown>
type MutableDryRunInput = Mutable<RealDailyReportDryRunInput> & Record<string, unknown>

const cloneCandidate = (): MutableCandidate =>
  structuredClone(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE) as MutableCandidate

const normalizeFixture = (): RealDailyReportDryRunInput => {
  const normalization = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
  expect(normalization.status).toBe('normalized')
  expect(normalization.normalizedInput).toBeDefined()
  return normalization.normalizedInput!
}

const stringify = (value: unknown): string => JSON.stringify(value)
const lowSensitivityNormalizerErrors = ['candidate-validation.blocked', 'normalization.failed'] as const
const allowedLabels = ['MOCK_AMOUNT', 'MOCK_RATIO', 'REDACTED_VALUE'] as const
const allowedRiskLabels = ['MOCK_RISK_LEVEL', 'MOCK_SIGNAL', 'REDACTED_VALUE'] as const
const forbiddenTradeWords = ['买入', '卖出', '加仓', '减仓', '清仓', '下单', '执行交易'] as const
const forbiddenLeakFields = [
  'candidatePayload',
  'rawCandidate',
  'rawResponse',
  'providerResponse',
  'requestUrl',
  'endpoint',
  'token',
  'webhook',
  'apiKey',
  'api_key',
  'secret',
  'password',
  'credential',
  'authorization',
  'headers',
  'cookies',
  'accountId',
  'transaction',
  'normalizedRawData',
  'viewModel',
  'DailyReportViewModel',
] as const

const expectNoLeaks = (value: unknown, extraForbidden: readonly string[] = []) => {
  const serialized = stringify(value)
  for (const forbidden of [...forbiddenLeakFields, ...extraForbidden]) expect(serialized).not.toContain(forbidden)
  expect(serialized).not.toContain('MOCK_PROVIDER_CANDIDATE_ID')
  expect(serialized).not.toContain('PROVIDER_TYPE_PLACEHOLDER')
}

const expectCandidateBlockedPropagation = (candidate: ProviderCandidatePayload, leakedValues: readonly string[] = []) => {
  const candidateValidation = validateProviderCandidatePayload(candidate)
  expect(candidateValidation.status).toBe('blocked')
  expect(candidateValidation.normalizationAllowed).toBe(false)

  const normalization = normalizeProviderCandidatePayloadToDryRunInput(candidate)
  expect(normalization.status).toBe('blocked')
  expect(normalization.errors.every((error) => lowSensitivityNormalizerErrors.includes(error as never))).toBe(true)
  expect(normalization.normalizedInput).toBeUndefined()
  expect(normalization.fallbackMode).toBe('mock-only')
  expect(normalization.canFallbackToMockOnly).toBe(true)
  expectNoLeaks(normalization, leakedValues)
}

const mutateDryRun = (mutate: (input: MutableDryRunInput) => void) => {
  const base = normalizeFixture()
  const cloned = structuredClone(base) as MutableDryRunInput
  mutate(cloned)
  const result = validateRealDailyReportDryRunInput(cloned as RealDailyReportDryRunInput)
  expect(validateRealDailyReportDryRunInput(base).status).toBe('passed')
  expect(result.status).toBe('blocked')
  expect(result.fallbackMode).toBe('mock-only')
  expect(result.canFallbackToMockOnly).toBe(true)
  return result
}

describe('Web-P47.1 provider candidate to dry-run validator chain review', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.resetModules()
  })

  it('executes the happy path in candidate validator, normalizer, then dry-run validator order', () => {
    const fixture = MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE
    const candidateValidation = validateProviderCandidatePayload(fixture)
    expect(candidateValidation.status).toBe('passed')
    expect(candidateValidation.errors).toEqual([])
    expect(candidateValidation.normalizationAllowed).toBe(true)
    expect(candidateValidation.fallbackMode).toBe('mock-only')
    expect(candidateValidation.canFallbackToMockOnly).toBe(true)

    const normalization = normalizeProviderCandidatePayloadToDryRunInput(fixture)
    expect(normalization.status).toBe('normalized')
    expect(normalization.errors).toEqual([])
    expect(normalization.normalizedInput).toBeDefined()
    expect(normalization.fallbackMode).toBe('mock-only')
    expect(normalization.canFallbackToMockOnly).toBe(true)

    const dryRunValidation = validateRealDailyReportDryRunInput(normalization.normalizedInput!)
    expect(dryRunValidation.status).toBe('passed')
    expect(dryRunValidation.errors).toEqual([])
    expect(dryRunValidation.fallbackMode).toBe('mock-only')
    expect(dryRunValidation.canFallbackToMockOnly).toBe(true)
  })

  it('locks normalizedInput safety, source, redaction, and rollback fields to mock-only dry-run values', () => {
    const normalizedInput = normalizeFixture()
    expect(normalizedInput).toMatchObject({
      mode: 'dry-run',
      dryRun: true,
      projectName: '股票基金质量分析系统',
      reportDisplayName: 'AI股票基金每日信息报告',
      source: {
        sourceType: 'mock-only',
        providerName: 'REDACTED_PROVIDER_LABEL',
        isMock: true,
        isRealReadOnly: false,
        isRedacted: true,
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
      },
      rollback: { fallbackMode: 'mock-only', canFallbackToMockOnly: true },
    })
  })

  it('preserves section order while mapping only validated candidate titles and low-sensitivity labels', () => {
    const normalizedInput = normalizeFixture()
    expect(normalizedInput.report.sections.map((section) => section.sectionId)).toEqual(
      MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.sections.map((section) => section.sectionId),
    )
    expect(normalizedInput.report.sections.map((section) => section.title)).toEqual(
      MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.sections.map((section) => section.title),
    )
    for (const section of normalizedInput.report.sections) {
      expect(section.summary).toBe('REDACTED_VALUE')
      expect(allowedLabels).toContain(section.amountLabel as never)
      expect(allowedLabels).toContain(section.ratioLabel as never)
    }
    expect(allowedRiskLabels).toContain(normalizedInput.report.riskLevel as never)
    for (const word of forbiddenTradeWords) expect(normalizedInput.report.portfolioAction).not.toContain(word)
  })

  it.each([
    ['providerType drift', (payload: MutableCandidate) => (payload.providerType = 'MOCK_EXTERNAL_PROVIDER_TYPE'), ['MOCK_EXTERNAL_PROVIDER_TYPE']],
    ['sourceLabel drift', (payload: MutableCandidate) => (payload.sourceLabel = 'MOCK_EXTERNAL_SOURCE_LABEL'), ['MOCK_EXTERNAL_SOURCE_LABEL']],
    ['candidateId drift', (payload: MutableCandidate) => (payload.candidateId = 'MOCK_EXTERNAL_CANDIDATE_ID'), ['MOCK_EXTERNAL_CANDIDATE_ID']],
    ['missing safety label', (payload: MutableCandidate) => (payload.safetyLabels = ['mock-only']), []],
    ['missing redaction label', (payload: MutableCandidate) => (payload.redactionLabels = ['REDACTED FIXTURE DATA']), []],
    ['empty sections', (payload: MutableCandidate) => (payload.sections = []), []],
    ['empty metrics', (payload: MutableCandidate) => (payload.metrics = []), []],
    ['empty risk signals', (payload: MutableCandidate) => (payload.riskSignals = []), []],
    ['rawResponse field', (payload: MutableCandidate) => (payload.rawResponse = 'MOCK_RAW_RESPONSE_BODY'), ['rawResponse', 'MOCK_RAW_RESPONSE_BODY']],
    ['apiKey field', (payload: MutableCandidate) => (payload.apiKey = 'MOCK_API_KEY_VALUE'), ['apiKey', 'MOCK_API_KEY_VALUE']],
    ['external URL marker', (payload: MutableCandidate) => (payload.sections[0].summary = ['ht', 'tps://mock.invalid/path'].join('')), ['mock.invalid']],
    ['precise decimal metric', (payload: MutableCandidate) => (payload.metrics[0].valueLabel = '1234.5678'), ['1234.5678']],
    ['risk signal trading instruction', (payload: MutableCandidate) => (payload.riskSignals[0].valueLabel = '立即执行交易'), ['立即执行交易']],
  ])('blocks candidate drift before exposing dry-run input: %s', (_name, mutate, leakedValues) => {
    const candidate = cloneCandidate()
    mutate(candidate)
    expectCandidateBlockedPropagation(candidate, leakedValues)
  })

  it.each([
    ['allowRealProvider=true', (input: MutableDryRunInput) => (input.safety.allowRealProvider = true)],
    ['allowRealAccountRead=true', (input: MutableDryRunInput) => (input.safety.allowRealAccountRead = true)],
    ['allowNotificationSend=true', (input: MutableDryRunInput) => (input.safety.allowNotificationSend = true)],
    ['allowTrading=true', (input: MutableDryRunInput) => (input.safety.allowTrading = true)],
    ['allowAiCall=true', (input: MutableDryRunInput) => (input.safety.allowAiCall = true)],
    ['requiresHumanApproval=false', (input: MutableDryRunInput) => (input.safety.requiresHumanApproval = false)],
    ['fallbackMode drift', (input: MutableDryRunInput) => (input.rollback.fallbackMode = 'real-provider')],
    ['canFallbackToMockOnly=false', (input: MutableDryRunInput) => (input.rollback.canFallbackToMockOnly = false)],
    ['mode drift', (input: MutableDryRunInput) => (input.mode = 'preview')],
    ['dryRun=false', (input: MutableDryRunInput) => (input.dryRun = false)],
    ['empty report sections', (input: MutableDryRunInput) => (input.report.sections = [])],
    ['external URL marker', (input: MutableDryRunInput) => (input.report.headline = ['ht', 'tps://mock.invalid/path'].join(''))],
    ['credential marker', (input: MutableDryRunInput) => (input.report.marketMood = 'MOCK_token_CREDENTIAL_MARKER')],
  ])('blocks mutated normalizedInput in the dry-run validator: %s', (_name, mutate) => {
    mutateDryRun(mutate)
  })

  it('does not leak forbidden field names or raw candidate identities from normalization results', () => {
    const normalization = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    expect(normalization.status).toBe('normalized')
    expectNoLeaks(normalization)
    expect(stringify(normalization).match(/REDACTED_PROVIDER_LABEL/g)?.length).toBe(1)
  })

  it('proves blocked dry-run validation results are not returned with normalizedInput', async () => {
    vi.doMock('../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator', () => ({
      validateRealDailyReportDryRunInput: vi.fn(() => ({
        status: 'blocked',
        errors: ['dry-run.blocked'],
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
    expect(result.normalizedInput).toBeUndefined()
    expectNoLeaks(result)
  })

  it('keeps normalizer source isolated from the dry-run adapter and DailyReportViewModel generation', () => {
    const source = readFileSync('src/mocks/preview/provider/providerCandidatePayloadNormalizer.ts', 'utf-8')
    expect(source).not.toContain('realDailyReportDryRunAdapter')
    expect(source).not.toContain('DailyReportViewModel')
    expect(source).not.toContain('adaptRealDailyReportDryRunInputToViewModel')
  })

  it('is deterministic, does not read time, random, or env, and does not mutate frozen fixture collections', () => {
    const before = stringify(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    const dateNowSpy = vi.spyOn(Date, 'now')
    const randomSpy = vi.spyOn(Math, 'random')
    const processEnvSpy = vi.spyOn(process, 'env', 'get')

    const first = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    const second = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)

    expect(second).toEqual(first)
    expect(stringify(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)).toBe(before)
    expect(Object.isFrozen(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)).toBe(true)
    expect(Object.isFrozen(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.sections)).toBe(true)
    expect(Object.isFrozen(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.metrics)).toBe(true)
    expect(Object.isFrozen(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE.riskSignals)).toBe(true)
    expect(validateProviderCandidatePayload(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE).status).toBe('passed')
    expect(first.status).toBe('normalized')
    expect(dateNowSpy).not.toHaveBeenCalled()
    expect(randomSpy).not.toHaveBeenCalled()
    expect(processEnvSpy).not.toHaveBeenCalled()
  })

  it.each([
    ['null', null],
    ['string', 'MOCK_EXTERNAL_STRING'],
    ['empty object', {}],
    ['missing arrays', { candidateId: 'MOCK_PROVIDER_CANDIDATE_ID' }],
    ['array member type mismatch', { ...cloneCandidate(), sections: [123] }],
    ['unknown field', { ...cloneCandidate(), rawResponse: 'MOCK_RAW_RESPONSE_BODY' }],
  ])('blocks malformed normalizer input without throwing or echoing raw content: %s', (_name, input) => {
    expect(() => normalizeProviderCandidatePayloadToDryRunInput(input as ProviderCandidatePayload)).not.toThrow()
    const result = normalizeProviderCandidatePayloadToDryRunInput(input as ProviderCandidatePayload)
    expect(result.status).toBe('blocked')
    expect(result.normalizedInput).toBeUndefined()
    expect(result.fallbackMode).toBe('mock-only')
    expect(result.canFallbackToMockOnly).toBe(true)
    expectNoLeaks(result, ['MOCK_EXTERNAL_STRING', 'MOCK_RAW_RESPONSE_BODY'])
  })
})
