import { describe, expect, it } from 'vitest'
import { MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE } from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'

const fixture = MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE
const serializedFixture = JSON.stringify(fixture)

const forbiddenExternalUrlPattern = /(?:https?:\/\/|\/api\/v\d+|localhost|127\.0\.0\.1|0\.0\.0\.0)/i
const suspiciousEmailPattern = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i
const suspiciousPhonePattern = /(?:\+?\d[\s-]?){10,}/
const preciseMoneyOrRatioPattern = /(?:¥|\$|￥)?\d{1,3}(?:,\d{3})*(?:\.\d{2,})|[+-]?\d+(?:\.\d+)?%/
const realisticFundCodePattern = /\b\d{6}\b|\b[A-Z]{2}\d{5}\b/

const forbiddenProviderRawFields = [
  'rawResponse',
  'responseBody',
  'payloadRaw',
  'providerRawResponse',
  'headers',
  'cookies',
  'requestUrl',
  'endpoint',
] as const

const forbiddenCredentialFields = [
  'token',
  'webhook',
  'apiKey',
  'api_key',
  'secret',
  'password',
  'credential',
  'authorization',
] as const

const realDryRunFinalFields = [
  'mode',
  'runtimeSafety',
  'report',
  'delivery',
  'providerMetadata',
  'fallback',
] as const

const dailyReportViewModelFields = [
  'metadata',
  'summaryCards',
  'dailyReportViewModel',
  'marketOverview',
  'portfolioObservation',
  'riskWarnings',
  'actionSuggestions',
] as const

describe('provider candidate payload mock-only fixture', () => {
  it('exists with a stable mock-only candidate structure', () => {
    expect(fixture).toEqual({
      candidateId: 'MOCK_PROVIDER_CANDIDATE_ID',
      candidateType: 'MOCK_CANDIDATE_TYPE',
      providerType: 'PROVIDER_TYPE_PLACEHOLDER',
      sourceLabel: 'REDACTED_PROVIDER_LABEL',
      dataFreshnessLabel: 'MOCK_FRESHNESS_LABEL',
      sections: expect.any(Array),
      metrics: expect.any(Array),
      riskSignals: expect.any(Array),
      redactionLabels: expect.any(Array),
      safetyLabels: expect.any(Array),
      mockOnlyNotes: expect.any(Array),
    })
  })

  it('uses explicit fictional provider and source placeholders', () => {
    expect(fixture.candidateId).toBe('MOCK_PROVIDER_CANDIDATE_ID')
    expect(fixture.providerType).toBe('PROVIDER_TYPE_PLACEHOLDER')
    expect(fixture.sourceLabel).toBe('REDACTED_PROVIDER_LABEL')
  })

  it('contains candidate sections, metrics, and risk signals for later validation tests', () => {
    expect(fixture.sections.length).toBeGreaterThan(0)
    expect(fixture.metrics.length).toBeGreaterThan(0)
    expect(fixture.riskSignals.length).toBeGreaterThan(0)
  })

  it('keeps required redaction labels and safety labels visible', () => {
    expect(fixture.redactionLabels).toEqual(
      expect.arrayContaining(['REDACTED FIXTURE DATA', '静态脱敏候选数据', '非真实来源']),
    )
    expect(fixture.safetyLabels).toEqual(
      expect.arrayContaining(['mock-only', 'dry-run only', '非真实账户', '不发送通知', '不交易', '不调用 AI']),
    )
  })

  it('documents that candidate payload is neither final dry-run input nor page view model', () => {
    expect(fixture.mockOnlyNotes.join('\n')).toContain('不是 RealDailyReportDryRunInput')
    expect(fixture.mockOnlyNotes.join('\n')).toContain('不是 DailyReportViewModel')
    expect(fixture.mockOnlyNotes.join('\n')).toContain('schema normalization')
    expect(fixture.mockOnlyNotes.join('\n')).toContain('validator passed')
    expect(fixture.mockOnlyNotes.join('\n')).toContain('fallback mock-only')
  })

  it('contains no external URL, email, phone, precise money, return ratio, or realistic fund code', () => {
    expect(serializedFixture).not.toMatch(forbiddenExternalUrlPattern)
    expect(serializedFixture).not.toMatch(suspiciousEmailPattern)
    expect(serializedFixture).not.toMatch(suspiciousPhonePattern)
    expect(serializedFixture).not.toMatch(preciseMoneyOrRatioPattern)
    expect(serializedFixture).not.toMatch(realisticFundCodePattern)
  })

  it('contains no provider raw response fields or credential fields', () => {
    for (const field of [...forbiddenProviderRawFields, ...forbiddenCredentialFields]) {
      expect(Object.hasOwn(fixture, field)).toBe(false)
      expect(serializedFixture.toLowerCase()).not.toContain(`"${field.toLowerCase()}"`)
    }
  })

  it('does not implement the complete RealDailyReportDryRunInput or DailyReportViewModel field shape', () => {
    for (const field of realDryRunFinalFields) {
      expect(Object.hasOwn(fixture, field)).toBe(false)
    }
    for (const field of dailyReportViewModelFields) {
      expect(Object.hasOwn(fixture, field)).toBe(false)
    }
  })

  it('keeps the core object and arrays frozen at runtime', () => {
    expect(Object.isFrozen(fixture)).toBe(true)
    expect(Object.isFrozen(fixture.sections)).toBe(true)
    expect(Object.isFrozen(fixture.metrics)).toBe(true)
    expect(Object.isFrozen(fixture.riskSignals)).toBe(true)
    expect(Object.isFrozen(fixture.redactionLabels)).toBe(true)
    expect(Object.isFrozen(fixture.safetyLabels)).toBe(true)
    expect(Object.isFrozen(fixture.mockOnlyNotes)).toBe(true)
    expect(() => (fixture.sections as unknown as unknown[]).push({})).toThrow()
  })
})
