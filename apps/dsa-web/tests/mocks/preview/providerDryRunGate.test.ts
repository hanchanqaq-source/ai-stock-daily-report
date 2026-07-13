import { afterEach, describe, expect, it, vi } from 'vitest'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'
import { MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE } from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { runProviderDryRunGate, type ProviderDryRunGateResult } from '../../../src/mocks/preview/provider/providerDryRunGate'

type Mutable<T> = { -readonly [P in keyof T]: T[P] extends readonly (infer U)[] ? Mutable<U>[] : T[P] }

const enabledFlag = Object.freeze({ enabled: true })
const cloneCandidate = () => structuredClone(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE) as Mutable<typeof MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE> & Record<string, unknown>

const expectSafetyLocked = (result: ProviderDryRunGateResult): void => {
  expect(result.allowRealProvider).toBe(false)
  expect(result.allowRealAccountRead).toBe(false)
  expect(result.allowNotificationSend).toBe(false)
  expect(result.allowTrading).toBe(false)
  expect(result.allowAiCall).toBe(false)
  expect(result.requiresHumanApproval).toBe(true)
  expect(result.fallbackMode).toBe('mock-only')
  expect(result.canFallbackToMockOnly).toBe(true)
}

const expectNoUnsafePayload = (result: ProviderDryRunGateResult): void => {
  expect(result).not.toHaveProperty('candidate')
  expect(result).not.toHaveProperty('candidatePayload')
  expect(result).not.toHaveProperty('rawCandidate')
  expect(result).not.toHaveProperty('viewModel')
  expect(result).not.toHaveProperty('DailyReportViewModel')
}

describe('provider dry-run gate', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.resetModules()
    vi.doUnmock('../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer')
    vi.doUnmock('../../../src/mocks/preview/dry-run/realDailyReportDryRunAdapter')
    vi.unstubAllGlobals()
  })

  it('returns disabled for undefined input and default feature flag', () => {
    expect(runProviderDryRunGate()).toMatchObject({ status: 'disabled', featureFlagState: 'disabled', candidateChainExecuted: false })
    expect(runProviderDryRunGate({})).toMatchObject({ status: 'disabled', featureFlagState: 'disabled', candidateChainExecuted: false })
  })

  it('does not call normalizer for disabled feature flag', async () => {
    const normalizerSpy = vi.fn()
    vi.doMock('../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer', () => ({
      normalizeProviderCandidatePayloadToDryRunInput: normalizerSpy,
    }))
    const { runProviderDryRunGate: runGate } = await import('../../../src/mocks/preview/provider/providerDryRunGate')
    const result = runGate({ featureFlag: { enabled: false }, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
    expect(result.status).toBe('disabled')
    expect(result.candidateChainExecuted).toBe(false)
    expect(normalizerSpy).not.toHaveBeenCalled()
  })

  it('blocks feature flag failures without calling normalizer', async () => {
    const normalizerSpy = vi.fn()
    vi.doMock('../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer', () => ({
      normalizeProviderCandidatePayloadToDryRunInput: normalizerSpy,
    }))
    const { runProviderDryRunGate: runGate } = await import('../../../src/mocks/preview/provider/providerDryRunGate')
    const result = runGate({ featureFlag: { enabled: true, allowRealProvider: true }, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
    expect(result).toMatchObject({ status: 'blocked', blockedStage: 'feature-flag', candidateChainExecuted: false })
    expect(normalizerSpy).not.toHaveBeenCalled()
  })

  it('blocks enabled-mock-only input when candidate is missing', () => {
    const result = runProviderDryRunGate({ featureFlag: enabledFlag })
    expect(result).toMatchObject({
      status: 'blocked',
      featureFlagState: 'enabled-mock-only',
      blockedStage: 'gate-input',
      candidateChainExecuted: false,
      errors: ['provider-dry-run-gate.candidate-required'],
    })
    expect(result).not.toHaveProperty('normalizedInput')
  })

  it('completes mock-only with fixture and produces dry-run validator passing normalizedInput', () => {
    const result = runProviderDryRunGate({ featureFlag: enabledFlag, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
    expect(result.status).toBe('completed-mock-only')
    expect(result.featureFlagState).toBe('enabled-mock-only')
    expect(result.candidateChainExecuted).toBe(true)
    expect(result.errors).toEqual([])
    expect(result).toHaveProperty('normalizedInput')
    if (result.status !== 'completed-mock-only') throw new Error('expected completed')
    expect(validateRealDailyReportDryRunInput(result.normalizedInput).status).toBe('passed')
    expectSafetyLocked(result)
  })

  it('maps candidate validator blocked to low-sensitive gate blocked without normalizedInput', () => {
    const candidate = cloneCandidate()
    candidate.candidateId = 'REAL_CANDIDATE_ID_SHOULD_NOT_LEAK'
    candidate.providerType = 'REAL_PROVIDER_TYPE_SHOULD_NOT_LEAK'
    candidate.rawResponse = 'RAW_RESPONSE_SHOULD_NOT_LEAK'
    const result = runProviderDryRunGate({ featureFlag: enabledFlag, candidate })
    expect(result).toMatchObject({ status: 'blocked', blockedStage: 'candidate-chain', candidateChainExecuted: true })
    expect(result.errors).toEqual(['candidate-validation.blocked'])
    expect(result).not.toHaveProperty('normalizedInput')
    const serialized = JSON.stringify(result)
    expect(serialized).not.toContain('REAL_CANDIDATE_ID_SHOULD_NOT_LEAK')
    expect(serialized).not.toContain('REAL_PROVIDER_TYPE_SHOULD_NOT_LEAK')
    expect(serialized).not.toContain('RAW_RESPONSE_SHOULD_NOT_LEAK')
  })

  it('maps dry-run validator blocked to gate blocked without normalizedInput', async () => {
    vi.doMock('../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer', () => ({
      normalizeProviderCandidatePayloadToDryRunInput: vi.fn(() => ({
        status: 'blocked',
        errors: ['normalized-dry-run-validation.blocked'],
        warnings: [],
        fallbackMode: 'mock-only',
        canFallbackToMockOnly: true,
      })),
    }))
    const { runProviderDryRunGate: runGate } = await import('../../../src/mocks/preview/provider/providerDryRunGate')
    const result = runGate({ featureFlag: enabledFlag, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
    expect(result).toMatchObject({ status: 'blocked', blockedStage: 'candidate-chain', candidateChainExecuted: true })
    expect(result.errors).toEqual(['normalized-dry-run-validation.blocked'])
    expect(result).not.toHaveProperty('normalizedInput')
  })

  it('catches normalizer exceptions as low-sensitive unexpected blocked', async () => {
    vi.doMock('../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer', () => ({
      normalizeProviderCandidatePayloadToDryRunInput: () => {
        throw new Error('SECRET_STACK_SHOULD_NOT_LEAK')
      },
    }))
    const { runProviderDryRunGate: runGate } = await import('../../../src/mocks/preview/provider/providerDryRunGate')
    const result = runGate({ featureFlag: enabledFlag, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
    expect(result).toMatchObject({ status: 'blocked', blockedStage: 'unexpected', errors: ['provider-dry-run-gate.failed'] })
    expect(JSON.stringify(result)).not.toContain('SECRET_STACK_SHOULD_NOT_LEAK')
    expect(result).not.toHaveProperty('normalizedInput')
  })

  it('does not read candidate getter when disabled or feature flag blocked', () => {
    const candidateGetter = vi.fn(() => MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    const disabledInput = Object.defineProperty({ featureFlag: { enabled: false } }, 'candidate', { get: candidateGetter })
    expect(runProviderDryRunGate(disabledInput).status).toBe('disabled')
    expect(candidateGetter).not.toHaveBeenCalled()

    const blockedInput = Object.defineProperty({ featureFlag: { allowRealProvider: true } }, 'candidate', { get: candidateGetter })
    expect(runProviderDryRunGate(blockedInput).status).toBe('blocked')
    expect(candidateGetter).not.toHaveBeenCalled()
  })

  it('keeps all disabled and blocked results free of payload properties and sensitive markers', () => {
    const results = [
      runProviderDryRunGate(),
      runProviderDryRunGate('invalid'),
      runProviderDryRunGate({ featureFlag: { allowRealProvider: true }, candidate: cloneCandidate() }),
      runProviderDryRunGate({ featureFlag: enabledFlag }),
      runProviderDryRunGate({ featureFlag: enabledFlag, candidate: { candidateId: 'MOCK_PROVIDER_CANDIDATE_ID', providerType: 'PROVIDER_TYPE_PLACEHOLDER', rawResponse: 'RAW_RESPONSE_SHOULD_NOT_LEAK' } }),
    ]
    for (const result of results) {
      expectSafetyLocked(result)
      expectNoUnsafePayload(result)
      if (result.status !== 'completed-mock-only') expect(result).not.toHaveProperty('normalizedInput')
      const serialized = JSON.stringify(result)
      expect(serialized).not.toContain('MOCK_PROVIDER_CANDIDATE_ID')
      expect(serialized).not.toContain('PROVIDER_TYPE_PLACEHOLDER')
      expect(serialized).not.toContain('RAW_RESPONSE_SHOULD_NOT_LEAK')
    }
  })

  it('does not mutate inputs, accepts frozen fixture, freezes results, and stays deterministic', () => {
    const featureFlag = { enabled: true }
    const candidate = cloneCandidate()
    const before = JSON.stringify({ featureFlag, candidate })
    const first = runProviderDryRunGate({ featureFlag, candidate })
    const second = runProviderDryRunGate({ featureFlag, candidate })
    const frozen = runProviderDryRunGate({ featureFlag: enabledFlag, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })

    expect(JSON.stringify({ featureFlag, candidate })).toBe(before)
    expect(first).toEqual(second)
    expect(frozen.status).toBe('completed-mock-only')
    expect(Object.isFrozen(first)).toBe(true)
    expect(Object.isFrozen(first.errors)).toBe(true)
    expect(Object.isFrozen(first.warnings)).toBe(true)
  })

  it('does not access network, storage, environment, time, random APIs, or adapter', async () => {
    const fetchSpy = vi.fn()
    const localStorageGetItem = vi.fn()
    const envSpy = vi.spyOn(process, 'env', 'get')
    const nowSpy = vi.spyOn(Date, 'now')
    const randomSpy = vi.spyOn(Math, 'random')
    vi.stubGlobal('fetch', fetchSpy)
    vi.stubGlobal('localStorage', { getItem: localStorageGetItem })
    vi.doMock('../../../src/mocks/preview/dry-run/realDailyReportDryRunAdapter', () => ({
      adaptRealDailyReportDryRunInputToViewModel: vi.fn(() => {
        throw new Error('adapter must not be called')
      }),
    }))

    runProviderDryRunGate({ featureFlag: enabledFlag, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })

    expect(fetchSpy).not.toHaveBeenCalled()
    expect(localStorageGetItem).not.toHaveBeenCalled()
    expect(envSpy).not.toHaveBeenCalled()
    expect(nowSpy).not.toHaveBeenCalled()
    expect(randomSpy).not.toHaveBeenCalled()
    const adapter = await import('../../../src/mocks/preview/dry-run/realDailyReportDryRunAdapter')
    expect(adapter.adaptRealDailyReportDryRunInputToViewModel).not.toHaveBeenCalled()
  })
})
