import { describe, expect, it, vi } from 'vitest'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'
import { MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE } from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { runProviderReadonlyDryRunPipeline } from '../../../src/mocks/preview/provider/providerReadonlyDryRunPipeline'
import type { ProviderReadonlyPort } from '../../../src/mocks/preview/provider/providerReadonlyPort'
import { DEFAULT_PROVIDER_READONLY_REQUEST, type ProviderReadonlyPortResult } from '../../../src/mocks/preview/provider/providerReadonlyTypes'

const enabled = { enabled: true } as const
const failure = (status: Exclude<ProviderReadonlyPortResult['status'], 'candidate'>): ProviderReadonlyPortResult => Object.freeze({ status, providerLabel: 'REDACTED_PROVIDER_LABEL', readOnly: true, redacted: true, errors: Object.freeze([`provider.${status}`]), warnings: Object.freeze([]), fallbackMode: 'mock-only', canFallbackToMockOnly: true })
const candidateResult = (candidate = MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE): ProviderReadonlyPortResult => Object.freeze({ status: 'candidate', providerLabel: 'REDACTED_PROVIDER_LABEL', readOnly: true, redacted: true, candidate, errors: Object.freeze([]) as readonly [], warnings: Object.freeze([]) })
const port = (result: ProviderReadonlyPortResult, spy = vi.fn()): ProviderReadonlyPort => Object.freeze({ mode: 'local-dry-run', providerLabel: 'REDACTED_PROVIDER_LABEL', networkEnabled: false, credentialReadEnabled: false, accountReadEnabled: false, readCandidate: spy.mockResolvedValue(result) })

const expectSafe = (result: Awaited<ReturnType<typeof runProviderReadonlyDryRunPipeline>>) => {
  expect(result).toMatchObject({ fallbackMode: 'mock-only', canFallbackToMockOnly: true, allowRealProvider: false, allowRealAccountRead: false, allowNotificationSend: false, allowTrading: false, allowAiCall: false, requiresHumanApproval: true })
}

describe('readonly provider dry-run pipeline', () => {
  it('defaults to disabled and does not read request or provider getters while disabled', async () => {
    await expect(runProviderReadonlyDryRunPipeline()).resolves.toMatchObject({ status: 'disabled', providerAttempted: false, providerOutcome: 'not-attempted', fallbackUsed: false, candidateChainExecuted: false })
    const requestGetter = vi.fn()
    const providerGetter = vi.fn()
    const input = Object.defineProperties({}, { featureFlag: { value: { enabled: false } }, request: { get: requestGetter }, provider: { get: providerGetter } })
    const result = await runProviderReadonlyDryRunPipeline(input)
    expect(result.status).toBe('disabled')
    expect(requestGetter).not.toHaveBeenCalled()
    expect(providerGetter).not.toHaveBeenCalled()
  })

  it('blocks flag failures and request violations before provider call', async () => {
    const spy = vi.fn()
    await expect(runProviderReadonlyDryRunPipeline({ featureFlag: { enabled: true, allowRealProvider: true }, provider: port(failure('unavailable'), spy) })).resolves.toMatchObject({ status: 'blocked', providerAttempted: false })
    expect(spy).not.toHaveBeenCalled()
    await expect(runProviderReadonlyDryRunPipeline({ featureFlag: enabled, request: 'bad' })).resolves.toMatchObject({ status: 'blocked' })
    await expect(runProviderReadonlyDryRunPipeline({ featureFlag: enabled, request: { ...DEFAULT_PROVIDER_READONLY_REQUEST, allowTrading: true } })).resolves.toMatchObject({ status: 'blocked' })
    await expect(runProviderReadonlyDryRunPipeline({ featureFlag: enabled, request: { ...DEFAULT_PROVIDER_READONLY_REQUEST, extra: true } })).resolves.toMatchObject({ status: 'blocked' })
  })

  it.each(['unavailable', 'timeout', 'credential-unavailable'] as const)('falls back to mock fixture after %s', async (status) => {
    const spy = vi.fn()
    const result = await runProviderReadonlyDryRunPipeline({ featureFlag: enabled, provider: port(failure(status), spy) })
    expect(spy).toHaveBeenCalledWith(DEFAULT_PROVIDER_READONLY_REQUEST)
    expect(result).toMatchObject({ status: 'completed-mock-only', providerAttempted: true, providerOutcome: status, fallbackUsed: true, candidateChainExecuted: true })
    expect(result.warnings).toContain(`provider-readonly.fallback-after-${status}`)
    if (result.status !== 'completed-mock-only') throw new Error('expected completed')
    expect(validateRealDailyReportDryRunInput(result.normalizedInput).status).toBe('passed')
    expectSafe(result)
  })

  it('accepts valid candidate results and blocks invalid candidates', async () => {
    const completed = await runProviderReadonlyDryRunPipeline({ featureFlag: enabled, provider: port(candidateResult()) })
    expect(completed).toMatchObject({ status: 'completed-mock-only', providerOutcome: 'candidate', fallbackUsed: false, candidateChainExecuted: true })
    const invalid = { ...MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE, candidateId: 'REAL_ID' }
    const blocked = await runProviderReadonlyDryRunPipeline({ featureFlag: enabled, provider: port(candidateResult(invalid)) })
    expect(blocked).toMatchObject({ status: 'blocked', providerOutcome: 'candidate', fallbackUsed: false })
    expect(blocked).not.toHaveProperty('normalizedInput')
  })

  it.each(['invalid-response', 'blocked'] as const)('blocks provider %s without normalizedInput', async (status) => {
    const result = await runProviderReadonlyDryRunPipeline({ featureFlag: enabled, provider: port(failure(status)) })
    expect(result).toMatchObject({ status: 'blocked', providerAttempted: true, providerOutcome: status, fallbackUsed: false, candidateChainExecuted: false })
    expect(result).not.toHaveProperty('normalizedInput')
  })

  it('handles provider exceptions with low-sensitive blocked result', async () => {
    const provider = { ...port(failure('unavailable')), readCandidate: vi.fn().mockRejectedValue(new Error('SECRET_PROVIDER_ERROR')) }
    const result = await runProviderReadonlyDryRunPipeline({ featureFlag: enabled, provider })
    expect(result).toMatchObject({ status: 'blocked', providerOutcome: 'unexpected', errors: ['provider-readonly-pipeline.failed'] })
    expect(JSON.stringify(result)).not.toContain('SECRET_PROVIDER_ERROR')
  })

  it('keeps deterministic frozen outputs and avoids network, storage, environment, time, random, adapter, and ViewModel', async () => {
    const fetchSpy = vi.fn(); vi.stubGlobal('fetch', fetchSpy); vi.stubGlobal('localStorage', { getItem: vi.fn() })
    const envSpy = vi.spyOn(process, 'env', 'get'); const nowSpy = vi.spyOn(Date, 'now'); const randomSpy = vi.spyOn(Math, 'random')
    const input = { featureFlag: enabled, provider: port(failure('unavailable')) }
    const before = JSON.stringify(input)
    const first = await runProviderReadonlyDryRunPipeline(input)
    const second = await runProviderReadonlyDryRunPipeline(input)
    expect(JSON.stringify(input)).toBe(before)
    expect(first).toEqual(second)
    expect(Object.isFrozen(first)).toBe(true)
    expect(Object.isFrozen(first.errors)).toBe(true)
    expect(fetchSpy).not.toHaveBeenCalled(); expect(localStorage.getItem).not.toHaveBeenCalled(); expect(envSpy).not.toHaveBeenCalled(); expect(nowSpy).not.toHaveBeenCalled(); expect(randomSpy).not.toHaveBeenCalled()
    expect(JSON.stringify(first)).not.toContain('DailyReportViewModel')
  })
})
