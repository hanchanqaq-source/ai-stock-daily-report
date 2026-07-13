import { describe, expect, it, vi } from 'vitest'
import {
  MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE,
  type ProviderCandidatePayload,
} from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { validateProviderCandidatePayload } from '../../../src/mocks/preview/provider/providerCandidatePayloadValidator'

type Mutable<T> = { -readonly [P in keyof T]: T[P] extends readonly (infer U)[] ? Mutable<U>[] : T[P] }
type MutableProviderCandidatePayload = Mutable<ProviderCandidatePayload>

const clonePayload = (): MutableProviderCandidatePayload =>
  structuredClone(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE) as MutableProviderCandidatePayload

const expectBlocked = (payload: unknown) => {
  const result = validateProviderCandidatePayload(payload as ProviderCandidatePayload)
  expect(result.status).toBe('blocked')
  expect(result.fallbackMode).toBe('mock-only')
  expect(result.canFallbackToMockOnly).toBe(true)
  expect(result.normalizationAllowed).toBe(false)
  expect(result).not.toHaveProperty('payload')
  expect(result).not.toHaveProperty('normalized')
  expect(result).not.toHaveProperty('viewModel')
  return result
}

describe('provider candidate payload validator', () => {
  it('passes the Web-P45 mock-only provider candidate fixture', () => {
    const result = validateProviderCandidatePayload(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    expect(result).toEqual({
      status: 'passed',
      errors: [],
      warnings: [],
      fallbackMode: 'mock-only',
      canFallbackToMockOnly: true,
      normalizationAllowed: true,
    })
  })

  it('blocks null and non-object input without throwing', () => {
    expect(() => validateProviderCandidatePayload(null as never)).not.toThrow()
    expect(expectBlocked(null).errors).toContain('input.invalid-object')
    expect(expectBlocked('MOCK_EXTERNAL_VALUE').errors).toContain('input.invalid-object')
  })

  it('blocks fixed mock-only identity drift with low-sensitivity paths', () => {
    const candidateIdPayload = clonePayload()
    candidateIdPayload.candidateId = 'MOCK_EXTERNAL_VALUE'
    expect(expectBlocked(candidateIdPayload).errors).toContain('candidate.not-mock-only:input.candidateId')

    const providerTypePayload = clonePayload()
    providerTypePayload.providerType = 'MOCK_EXTERNAL_VALUE'
    expect(expectBlocked(providerTypePayload).errors).toContain('candidate.not-mock-only:input.providerType')

    const sourceLabelPayload = clonePayload()
    sourceLabelPayload.sourceLabel = 'MOCK_EXTERNAL_VALUE'
    expect(expectBlocked(sourceLabelPayload).errors).toContain('candidate.not-mock-only:input.sourceLabel')
  })

  it('blocks required collection and label omissions', () => {
    const emptySections = clonePayload()
    emptySections.sections = []
    expect(expectBlocked(emptySections).errors).toContain('sections.required')

    const emptyMetrics = clonePayload()
    emptyMetrics.metrics = []
    expect(expectBlocked(emptyMetrics).errors).toContain('metrics.required')

    const emptyRiskSignals = clonePayload()
    emptyRiskSignals.riskSignals = []
    expect(expectBlocked(emptyRiskSignals).errors).toContain('riskSignals.required')

    const missingRedaction = clonePayload()
    missingRedaction.redactionLabels = ['REDACTED FIXTURE DATA', '静态脱敏候选数据']
    expect(expectBlocked(missingRedaction).errors).toContain('redactionLabel.missing')

    const missingSafety = clonePayload()
    missingSafety.safetyLabels = ['mock-only', 'dry-run only', '非真实账户', '不发送通知', '不交易']
    expect(expectBlocked(missingSafety).errors).toContain('safetyLabel.missing')

    const missingNote = clonePayload()
    missingNote.mockOnlyNotes = ['MOCK_EXTERNAL_VALUE']
    expect(expectBlocked(missingNote).errors).toContain('mockOnlyNote.missing')
  })

  it('blocks invalid section, metric, and risk signal fields', () => {
    const sectionPayload = clonePayload()
    sectionPayload.sections[0].summary = ''
    expect(expectBlocked(sectionPayload).errors).toContain('section.invalid:input.sections[0]')

    const invalidNotesPayload = clonePayload()
    invalidNotesPayload.sections[0].notes = [123 as never]
    expect(expectBlocked(invalidNotesPayload).errors).toContain('section.invalid:input.sections[0]')

    const amountPayload = clonePayload()
    amountPayload.metrics[0].valueLabel = '123456.78'
    expect(expectBlocked(amountPayload).errors).toContain('metric.valueLabel.invalid:input.metrics[0].valueLabel')

    const percentPayload = clonePayload()
    percentPayload.metrics[1].valueLabel = '12.34%'
    expect(expectBlocked(percentPayload).errors).toContain('metric.valueLabel.invalid:input.metrics[1].valueLabel')

    const tradePayload = clonePayload()
    tradePayload.riskSignals[0].valueLabel = '执行交易'
    expect(expectBlocked(tradePayload).errors).toContain('riskSignal.valueLabel.invalid:input.riskSignals[0].valueLabel')
  })

  it('blocks sensitive strings without echoing original values', () => {
    const urlMarker = ['ht', 'tps://', 'mock.invalid'].join('')
    const emailMarker = ['mock-user', '@', 'example.invalid'].join('')
    const phoneMarker = ['139', '0000', '0000'].join('')
    const secretMarker = ['MOCK_', 'api', '_key', '_MARKER'].join('')
    const rawValueMarker = ['raw', 'Response'].join('')
    const codeMarker = ['123', '456'].join('')
    const preciseValueMarker = ['1234', '.56'].join('')

    const cases = [urlMarker, emailMarker, phoneMarker, secretMarker, rawValueMarker, codeMarker, preciseValueMarker]
    for (const marker of cases) {
      const payload = clonePayload()
      payload.sections[0].summary = marker
      const result = expectBlocked(payload)
      expect(result.errors.join('|')).not.toContain(marker)
    }
  })

  it('blocks raw provider and credential-like field names without returning their values', () => {
    const payload = clonePayload() as MutableProviderCandidatePayload & Record<string, unknown>
    const rawFieldName = ['raw', 'Response'].join('')
    payload[rawFieldName] = 'MOCK_EXTERNAL_VALUE'

    const result = expectBlocked(payload)
    expect(result.errors).toContain(`sensitive-pattern.raw-provider-field:input.${rawFieldName}`)
    expect(result.errors.join('|')).not.toContain('MOCK_EXTERNAL_VALUE')
  })

  it('does not mutate the input object and works with the frozen fixture', () => {
    const payload = clonePayload()
    const before = JSON.stringify(payload)
    validateProviderCandidatePayload(payload)
    expect(JSON.stringify(payload)).toBe(before)
    expect(Object.isFrozen(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)).toBe(true)
    expect(validateProviderCandidatePayload(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE).status).toBe('passed')
  })

  it('does not access network, file, browser storage, or environment globals', () => {
    const forbidden = vi.fn(() => {
      throw new Error('external capability must not be used')
    })
    vi.stubGlobal('fetch', forbidden)
    vi.stubGlobal('XMLHttpRequest', forbidden)
    vi.stubGlobal('WebSocket', forbidden)
    vi.stubGlobal('localStorage', { getItem: forbidden })
    const processEnvSpy = vi.spyOn(process, 'env', 'get')
    expect(validateProviderCandidatePayload(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE).status).toBe('passed')
    expect(forbidden).not.toHaveBeenCalled()
    expect(processEnvSpy).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })
})
