import { describe, expect, it, vi } from 'vitest'
import { MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE } from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { sanitizeProviderReadonlyPortResult } from '../../../src/mocks/preview/provider/providerReadonlyResultSanitizer'

const base = {
  providerLabel: 'REDACTED_PROVIDER_LABEL',
  readOnly: true,
  redacted: true,
} as const
const failure = (status: string, extra: Record<string, unknown> = {}) => ({
  status,
  ...base,
  errors: ['token=SECRET_TOKEN_MARKER', 'accountId=SECRET_ACCOUNT_MARKER'],
  warnings: ['requestUrl=SECRET_URL_MARKER'],
  fallbackMode: 'mock-only',
  canFallbackToMockOnly: true,
  ...extra,
})
const candidate = (extra: Record<string, unknown> = {}) => ({
  status: 'candidate',
  ...base,
  candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE,
  errors: [],
  warnings: [],
  ...extra,
})
const expectInvalid = (input: unknown) => {
  expect(sanitizeProviderReadonlyPortResult(input)).toEqual({
    status: 'invalid-provider-result',
    providerLabel: 'REDACTED_PROVIDER_LABEL',
    readOnly: true,
    redacted: true,
    errors: ['provider-readonly.invalid-provider-result'],
    warnings: [],
    fallbackMode: 'mock-only',
    canFallbackToMockOnly: true,
  })
}

describe('provider readonly result sanitizer', () => {
  it('passes valid candidate outer contract and freezes safe output', () => {
    const result = sanitizeProviderReadonlyPortResult(candidate())
    expect(result).toMatchObject({
      status: 'candidate',
      candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE,
      errors: [],
      warnings: [],
    })
    expect(Object.isFrozen(result)).toBe(true)
    expect(Object.isFrozen(result.errors)).toBe(true)
    expect(Object.isFrozen(result.warnings)).toBe(true)
  })

  it.each(['unavailable', 'timeout', 'credential-unavailable', 'invalid-response', 'blocked'] as const)(
    'maps %s to fixed low-sensitive errors',
    (status) => {
      const result = sanitizeProviderReadonlyPortResult(failure(status))
      expect(result).toMatchObject({
        status,
        errors: [`provider-readonly.${status}`],
        warnings: [],
      })
      const serialized = JSON.stringify(result)
      expect(serialized).not.toContain('SECRET_TOKEN_MARKER')
      expect(serialized).not.toContain('SECRET_URL_MARKER')
      expect(serialized).not.toContain('SECRET_ACCOUNT_MARKER')
    },
  )

  it.each([
    { status: 'success' },
    {},
    null,
    'bad',
    1,
    [],
    () => undefined,
    failure('Unavailable'),
    failure('real-provider'),
    failure('enabled'),
    failure('error'),
    failure(null as never),
    failure(1 as never),
    failure({} as never),
  ])('returns fixed invalid-provider-result for invalid input %#', (input) => {
    expectInvalid(input)
  })

  it.each([
    failure('unavailable', { providerLabel: 'REAL_PROVIDER' }),
    failure('unavailable', { readOnly: false }),
    failure('unavailable', { redacted: false }),
    failure('unavailable', { fallbackMode: 'real-provider' }),
    failure('unavailable', { canFallbackToMockOnly: false }),
    candidate({ candidate: undefined }),
    candidate({ candidate: null }),
    candidate({ errors: ['SECRET_TOKEN_MARKER'] }),
    candidate({ warnings: ['SECRET_URL_MARKER'] }),
    candidate({ rawResponse: 'SECRET_RESPONSE' }),
    candidate({ extra: 'ordinary-drift' }),
  ])('blocks contract drift %#', (input) => {
    expectInvalid(input)
  })

  it('does not mutate input or return raw errors/warnings', () => {
    const input = failure('invalid-response')
    const before = structuredClone(input)
    const result = sanitizeProviderReadonlyPortResult(input)
    expect(input).toEqual(before)
    expect(result.errors).not.toBe(input.errors)
    expect(result.warnings).not.toBe(input.warnings)
  })

  it('is deterministic and avoids network, storage, environment, time, and random APIs', () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    vi.stubGlobal('localStorage', { getItem: vi.fn() })
    const envSpy = vi.spyOn(process, 'env', 'get')
    const nowSpy = vi.spyOn(Date, 'now')
    const randomSpy = vi.spyOn(Math, 'random')
    const first = sanitizeProviderReadonlyPortResult(failure('blocked'))
    const second = sanitizeProviderReadonlyPortResult(failure('blocked'))
    expect(first).toEqual(second)
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(localStorage.getItem).not.toHaveBeenCalled()
    expect(envSpy).not.toHaveBeenCalled()
    expect(nowSpy).not.toHaveBeenCalled()
    expect(randomSpy).not.toHaveBeenCalled()
  })
})
