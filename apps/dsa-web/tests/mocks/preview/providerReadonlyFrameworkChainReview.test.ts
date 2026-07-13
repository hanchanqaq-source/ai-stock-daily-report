import { describe, expect, it, vi } from 'vitest'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'
import { MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE } from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { runProviderReadonlyDryRunPipeline } from '../../../src/mocks/preview/provider/providerReadonlyDryRunPipeline'
import type { ProviderReadonlyPort } from '../../../src/mocks/preview/provider/providerReadonlyPort'
import type { ProviderReadonlyPortResult } from '../../../src/mocks/preview/provider/providerReadonlyTypes'

const failure = (status: Exclude<ProviderReadonlyPortResult['status'], 'candidate'>): ProviderReadonlyPortResult => ({
  status,
  providerLabel: 'REDACTED_PROVIDER_LABEL',
  readOnly: true,
  redacted: true,
  errors: [`provider.${status}`],
  warnings: [],
  fallbackMode: 'mock-only',
  canFallbackToMockOnly: true,
})
const candidate = (payload = MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE): ProviderReadonlyPortResult => ({
  status: 'candidate',
  providerLabel: 'REDACTED_PROVIDER_LABEL',
  readOnly: true,
  redacted: true,
  candidate: payload,
  errors: [],
  warnings: [],
})
const port = (result: unknown, spy = vi.fn()): ProviderReadonlyPort => ({
  mode: 'local-dry-run',
  providerLabel: 'REDACTED_PROVIDER_LABEL',
  networkEnabled: false,
  credentialReadEnabled: false,
  accountReadEnabled: false,
  readCandidate: spy.mockResolvedValue(result),
})

describe('Core-M2 readonly provider framework chain review', () => {
  it('matches the flag/provider outcome matrix', async () => {
    const rows = [
      [{ enabled: false }, undefined, 'disabled', false, false],
      [{ enabled: true, allowRealProvider: true }, undefined, 'blocked', false, false],
      [{ enabled: true }, failure('unavailable'), 'completed-mock-only', true, true],
      [{ enabled: true }, failure('timeout'), 'completed-mock-only', true, true],
      [{ enabled: true }, failure('credential-unavailable'), 'completed-mock-only', true, true],
      [{ enabled: true }, failure('invalid-response'), 'blocked', false, false],
      [{ enabled: true }, failure('blocked'), 'blocked', false, false],
      [{ enabled: true }, candidate(), 'completed-mock-only', false, true],
      [
        { enabled: true },
        candidate({
          ...MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE,
          candidateId: 'REAL_ID',
        }),
        'blocked',
        false,
        false,
      ],
    ] as const
    for (const [featureFlag, providerResult, status, fallbackUsed, hasNormalized] of rows) {
      const result = await runProviderReadonlyDryRunPipeline({
        featureFlag,
        provider: providerResult ? port(providerResult) : undefined,
      })
      expect(result.status).toBe(status)
      expect(result.fallbackUsed).toBe(fallbackUsed)
      expect('normalizedInput' in result).toBe(hasNormalized)
    }
    const exception = await runProviderReadonlyDryRunPipeline({
      featureFlag: { enabled: true },
      provider: {
        ...port(failure('unavailable')),
        readCandidate: vi.fn().mockRejectedValue(new Error('SECRET')),
      },
    })
    expect(exception).toMatchObject({ status: 'blocked', fallbackUsed: false })
    expect(exception).not.toHaveProperty('normalizedInput')
  })

  it('sanitizes the Core-M2.1 provider result matrix before pipeline decisions', async () => {
    const rows = [
      [failure('unavailable'), 'unavailable', 'completed-mock-only', true],
      [{ ...failure('timeout'), warnings: ['SECRET_URL_MARKER'] }, 'timeout', 'completed-mock-only', true],
      [
        {
          ...failure('credential-unavailable'),
          errors: ['SECRET_ACCOUNT_MARKER'],
        },
        'credential-unavailable',
        'completed-mock-only',
        true,
      ],
      [{ ...failure('invalid-response'), errors: ['TOKEN_MARKER'] }, 'invalid-response', 'blocked', false],
      [{ ...failure('blocked'), errors: ['ACCOUNT_MARKER'] }, 'blocked', 'blocked', false],
      [{ ...failure('success' as never) }, 'invalid-provider-result', 'blocked', false],
      ['not-an-object', 'invalid-provider-result', 'blocked', false],
      [{ ...candidate(), rawResponse: 'SECRET_rawResponse' }, 'invalid-provider-result', 'blocked', false],
      [candidate(), 'candidate', 'completed-mock-only', false],
    ] as const

    for (const [providerResult, providerOutcome, status, fallbackUsed] of rows) {
      const result = await runProviderReadonlyDryRunPipeline({
        featureFlag: { enabled: true },
        provider: port(providerResult),
      })
      expect(result.status).toBe(status)
      expect(result.providerOutcome).toBe(providerOutcome)
      expect(result.fallbackUsed).toBe(fallbackUsed)
      const serialized = JSON.stringify(result)
      for (const forbidden of [
        'SECRET',
        'TOKEN_MARKER',
        'URL_MARKER',
        'ACCOUNT_MARKER',
        'rawResponse',
        'responseBody',
        'requestUrl',
        'endpoint',
        'credentials',
      ]) {
        expect(serialized).not.toContain(forbidden)
      }
    }
  })

  it('keeps successful Provider Port to RealDailyReportDryRunInput chain mock-only and locked', async () => {
    const result = await runProviderReadonlyDryRunPipeline({
      featureFlag: { enabled: true },
      provider: port(candidate()),
    })
    expect(result.status).toBe('completed-mock-only')
    if (result.status !== 'completed-mock-only') throw new Error('expected completed')
    expect(validateRealDailyReportDryRunInput(result.normalizedInput).status).toBe('passed')
    expect(result.normalizedInput.source).toMatchObject({
      sourceType: 'mock-only',
      providerName: 'REDACTED_PROVIDER_LABEL',
      isRealReadOnly: false,
    })
    expect(result).toMatchObject({
      allowRealProvider: false,
      allowRealAccountRead: false,
      allowNotificationSend: false,
      allowTrading: false,
      allowAiCall: false,
      requiresHumanApproval: true,
      fallbackMode: 'mock-only',
    })
  })
})
