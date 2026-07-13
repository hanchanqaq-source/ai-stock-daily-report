import { describe, expect, it } from 'vitest'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'
import { MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE } from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { runProviderDryRunGate } from '../../../src/mocks/preview/provider/providerDryRunGate'

type Mutable<T> = { -readonly [P in keyof T]: T[P] extends readonly (infer U)[] ? Mutable<U>[] : T[P] }
const enabledFlag = Object.freeze({ enabled: true })
const cloneCandidate = () => structuredClone(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE) as Mutable<typeof MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE>

describe('Web-P50.1 provider dry-run gate chain review', () => {
  it('covers the full status matrix without leaking normalizedInput on blocked paths', () => {
    const candidateBlocked = cloneCandidate()
    candidateBlocked.providerType = 'REAL_PROVIDER_TYPE_DRIFT'
    const dryRunBlocked = cloneCandidate()
    dryRunBlocked.dataFreshnessLabel = 'token marker'

    const cases = [
      [runProviderDryRunGate({ featureFlag: { enabled: false } }), 'disabled', false, false],
      [runProviderDryRunGate({ featureFlag: { allowRealProvider: true } }), 'blocked', false, false],
      [runProviderDryRunGate({ featureFlag: enabledFlag }), 'blocked', false, false],
      [runProviderDryRunGate({ featureFlag: enabledFlag, candidate: candidateBlocked }), 'blocked', true, false],
      [runProviderDryRunGate({ featureFlag: enabledFlag, candidate: dryRunBlocked }), 'blocked', true, false],
      [runProviderDryRunGate({ featureFlag: enabledFlag, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE }), 'completed-mock-only', true, true],
    ] as const

    for (const [result, status, candidateChainExecuted, hasNormalizedInput] of cases) {
      expect(result.status).toBe(status)
      expect(result.candidateChainExecuted).toBe(candidateChainExecuted)
      expect('normalizedInput' in result).toBe(hasNormalizedInput)
      expect(result.fallbackMode).toBe('mock-only')
      expect(result.canFallbackToMockOnly).toBe(true)
    }
  })

  it('reviews successful feature flag to normalizer to candidate validator to dry-run validator chain', () => {
    const result = runProviderDryRunGate({ featureFlag: enabledFlag, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
    expect(result.status).toBe('completed-mock-only')
    if (result.status !== 'completed-mock-only') throw new Error('expected completed')

    const validation = validateRealDailyReportDryRunInput(result.normalizedInput)
    expect(validation.status).toBe('passed')
    expect(result.normalizedInput.source.sourceType).toBe('mock-only')
    expect(result.normalizedInput.source.providerName).toBe('REDACTED_PROVIDER_LABEL')
    expect(result.normalizedInput.source.isMock).toBe(true)
    expect(result.normalizedInput.source.isRealReadOnly).toBe(false)
    expect(result.normalizedInput.safety.allowRealProvider).toBe(false)
    expect(result.normalizedInput.safety.allowRealAccountRead).toBe(false)
    expect(result.normalizedInput.safety.allowNotificationSend).toBe(false)
    expect(result.normalizedInput.safety.allowTrading).toBe(false)
    expect(result.normalizedInput.safety.allowAiCall).toBe(false)
    expect(result.normalizedInput.safety.requiresHumanApproval).toBe(true)
    expect(result.normalizedInput.rollback.fallbackMode).toBe('mock-only')
    expect(result.normalizedInput.rollback.canFallbackToMockOnly).toBe(true)
  })

  it('keeps gate result and normalized output free of real provider, ViewModel, and sensitive fields', () => {
    const result = runProviderDryRunGate({ featureFlag: enabledFlag, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
    const serialized = JSON.stringify(result)
    for (const forbidden of [
      'real-provider',
      'enabled-real-provider',
      'viewModel',
      'DailyReportViewModel',
      'rawResponse',
      'accountId',
      'endpoint',
      'token',
      'webhook',
      'apiKey',
      'credential',
      'transaction',
    ]) {
      expect(serialized).not.toContain(forbidden)
    }
  })
})
