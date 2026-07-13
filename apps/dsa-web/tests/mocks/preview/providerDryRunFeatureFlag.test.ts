import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG,
  evaluateProviderDryRunFeatureFlag,
  type ProviderDryRunFeatureFlagResult,
} from '../../../src/mocks/preview/provider/providerDryRunFeatureFlag'

const safeConfig = Object.freeze({
  enabled: true,
  mode: 'mock-only',
  allowRealProvider: false,
  allowRealAccountRead: false,
  allowNotificationSend: false,
  allowTrading: false,
  allowAiCall: false,
  requiresHumanApproval: true,
  fallbackMode: 'mock-only',
  canFallbackToMockOnly: true,
})

const expectLockedSafety = (result: ProviderDryRunFeatureFlagResult): void => {
  expect(result.mode).toBe('mock-only')
  expect(result.allowRealProvider).toBe(false)
  expect(result.allowRealAccountRead).toBe(false)
  expect(result.allowNotificationSend).toBe(false)
  expect(result.allowTrading).toBe(false)
  expect(result.allowAiCall).toBe(false)
  expect(result.requiresHumanApproval).toBe(true)
  expect(result.fallbackMode).toBe('mock-only')
  expect(result.canFallbackToMockOnly).toBe(true)
}

const expectBlocked = (input: unknown): ProviderDryRunFeatureFlagResult => {
  const result = evaluateProviderDryRunFeatureFlag(input)
  expect(result.state).toBe('blocked')
  expect(result.enabled).toBe(false)
  expect(result.canRunMockOnlyCandidateChain).toBe(false)
  expect(result.errors.length).toBeGreaterThan(0)
  expectLockedSafety(result)
  return result
}

describe('provider dry-run feature flag', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('exports a frozen default config that is disabled and mock-only', () => {
    expect(DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG.enabled).toBe(false)
    expect(Object.isFrozen(DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG)).toBe(true)
    expect(DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG).toEqual({
      enabled: false,
      mode: 'mock-only',
      allowRealProvider: false,
      allowRealAccountRead: false,
      allowNotificationSend: false,
      allowTrading: false,
      allowAiCall: false,
      requiresHumanApproval: true,
      fallbackMode: 'mock-only',
      canFallbackToMockOnly: true,
    })
  })

  it('returns disabled for undefined, empty object, and explicit enabled=false inputs', () => {
    for (const input of [undefined, {}, { enabled: false }, { ...safeConfig, enabled: false }] as const) {
      const result = evaluateProviderDryRunFeatureFlag(input)
      expect(result.state).toBe('disabled')
      expect(result.enabled).toBe(false)
      expect(result.canRunMockOnlyCandidateChain).toBe(false)
      expect(result.errors).toEqual([])
      expectLockedSafety(result)
    }
  })

  it('returns enabled-mock-only only for safe enabled=true inputs', () => {
    for (const input of [{ enabled: true }, safeConfig] as const) {
      const result = evaluateProviderDryRunFeatureFlag(input)
      expect(result.state).toBe('enabled-mock-only')
      expect(result.enabled).toBe(true)
      expect(result.canRunMockOnlyCandidateChain).toBe(true)
      expect(result.errors).toEqual([])
      expectLockedSafety(result)
    }
  })

  it('blocks non-object and array inputs', () => {
    for (const input of [null, 'MOCK_FLAG_MARKER', 7, ['MOCK_FLAG_MARKER']] as const) {
      expectBlocked(input)
    }
  })

  it('blocks invalid enabled and non-mock-only mode inputs', () => {
    expectBlocked({ enabled: 'MOCK_ENABLED_MARKER' }).errors.forEach((error) => {
      expect(error).toContain('feature-flag.invalid-enabled')
    })
    expectBlocked({ enabled: true, mode: 'MOCK_REAL_MODE_MARKER' }).errors.forEach((error) => {
      expect(error).toContain('feature-flag.mode-must-be-mock-only')
    })
  })

  it('blocks every real capability request and keeps output safety locked', () => {
    const capabilityCases = [
      ['allowRealProvider', 'feature-flag.real-provider-forbidden'],
      ['allowRealAccountRead', 'feature-flag.real-account-read-forbidden'],
      ['allowNotificationSend', 'feature-flag.notification-forbidden'],
      ['allowTrading', 'feature-flag.trading-forbidden'],
      ['allowAiCall', 'feature-flag.ai-call-forbidden'],
    ] as const

    for (const [fieldName, errorCode] of capabilityCases) {
      const result = expectBlocked({ enabled: true, [fieldName]: true })
      expect(result.errors).toContain(`${errorCode}:input.${fieldName}`)
    }
  })

  it('blocks unsafe approval and fallback mutations', () => {
    expectBlocked({ enabled: true, requiresHumanApproval: false }).errors.forEach((error) => {
      expect(error).toContain('feature-flag.human-approval-required')
    })
    expectBlocked({ enabled: true, fallbackMode: 'MOCK_UNSAFE_FALLBACK' }).errors.forEach((error) => {
      expect(error).toContain('feature-flag.fallback-must-be-mock-only')
    })
    expectBlocked({ enabled: true, canFallbackToMockOnly: false }).errors.forEach((error) => {
      expect(error).toContain('feature-flag.fallback-must-be-mock-only')
    })
  })

  it('blocks sensitive unknown fields without echoing their values', () => {
    const sensitiveFields = ['token', 'apiKey', 'credential', 'endpoint', 'providerUrl', 'authorization'] as const
    for (const fieldName of sensitiveFields) {
      const result = expectBlocked({ enabled: true, [fieldName]: 'MOCK_SECRET_VALUE_SHOULD_NOT_LEAK' })
      expect(result.errors).toContain(`feature-flag.unknown-sensitive-field:input.${fieldName}`)
      expect(JSON.stringify(result.errors)).not.toContain('MOCK_SECRET_VALUE_SHOULD_NOT_LEAK')
    }
  })

  it('does not mutate input and returns deterministic results for repeated calls', () => {
    const input = { enabled: true, mode: 'mock-only' }
    const before = JSON.stringify(input)
    const first = evaluateProviderDryRunFeatureFlag(input)
    const second = evaluateProviderDryRunFeatureFlag(input)

    expect(JSON.stringify(input)).toBe(before)
    expect(first).toEqual(second)
    expect(first).not.toBe(input)
  })

  it('does not include candidate, normalizedInput, or ViewModel payloads in any result', () => {
    for (const result of [
      evaluateProviderDryRunFeatureFlag(),
      evaluateProviderDryRunFeatureFlag({ enabled: true }),
      evaluateProviderDryRunFeatureFlag({ allowRealProvider: true }),
    ]) {
      expect(result).not.toHaveProperty('candidate')
      expect(result).not.toHaveProperty('normalizedInput')
      expect(result).not.toHaveProperty('ViewModel')
      expect(JSON.stringify(result)).not.toContain('DailyReportViewModel')
    }
  })

  it('does not call system time or random APIs while evaluating', () => {
    const nowSpy = vi.spyOn(Date, 'now')
    const randomSpy = vi.spyOn(Math, 'random')

    evaluateProviderDryRunFeatureFlag({ enabled: true })
    evaluateProviderDryRunFeatureFlag({ allowRealProvider: true })

    expect(nowSpy).not.toHaveBeenCalled()
    expect(randomSpy).not.toHaveBeenCalled()
  })

  it('does not read process environment or browser storage while evaluating', () => {
    const envSpy = vi.spyOn(process, 'env', 'get')
    const localStorageGetItem = vi.fn()
    const sessionStorageGetItem = vi.fn()
    vi.stubGlobal('localStorage', { getItem: localStorageGetItem })
    vi.stubGlobal('sessionStorage', { getItem: sessionStorageGetItem })

    evaluateProviderDryRunFeatureFlag({ enabled: true })
    evaluateProviderDryRunFeatureFlag({ credential: 'MOCK_CREDENTIAL_MARKER' })

    expect(envSpy).not.toHaveBeenCalled()
    expect(localStorageGetItem).not.toHaveBeenCalled()
    expect(sessionStorageGetItem).not.toHaveBeenCalled()
  })

  it('does not access network primitives while evaluating', () => {
    const fetchSpy = vi.fn(() => {
      throw new Error('network must not be called')
    })
    const xhrSpy = vi.fn(() => {
      throw new Error('network must not be called')
    })
    const webSocketSpy = vi.fn(() => {
      throw new Error('network must not be called')
    })
    const eventSourceSpy = vi.fn(() => {
      throw new Error('network must not be called')
    })

    vi.stubGlobal('fetch', fetchSpy)
    vi.stubGlobal('XMLHttpRequest', xhrSpy)
    vi.stubGlobal('WebSocket', webSocketSpy)
    vi.stubGlobal('EventSource', eventSourceSpy)

    evaluateProviderDryRunFeatureFlag({ enabled: true })
    evaluateProviderDryRunFeatureFlag({ endpoint: 'MOCK_ENDPOINT_MARKER' })

    expect(fetchSpy).not.toHaveBeenCalled()
    expect(xhrSpy).not.toHaveBeenCalled()
    expect(webSocketSpy).not.toHaveBeenCalled()
    expect(eventSourceSpy).not.toHaveBeenCalled()
  })
})
