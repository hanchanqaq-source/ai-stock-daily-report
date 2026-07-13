import type { ProviderReadonlyPort } from './providerReadonlyPort'
import type { ProviderReadonlyFailureResult } from './providerReadonlyTypes'

const unavailableResult = (): ProviderReadonlyFailureResult =>
  Object.freeze({
    status: 'unavailable',
    providerLabel: 'REDACTED_PROVIDER_LABEL',
    readOnly: true,
    redacted: true,
    errors: Object.freeze(['provider-readonly.unavailable']),
    warnings: Object.freeze([]),
    fallbackMode: 'mock-only',
    canFallbackToMockOnly: true,
  })

export const createDisabledProviderReadonlyPort = (): ProviderReadonlyPort =>
  Object.freeze({
    mode: 'local-dry-run',
    providerLabel: 'REDACTED_PROVIDER_LABEL',
    networkEnabled: false,
    credentialReadEnabled: false,
    accountReadEnabled: false,
    readCandidate: async () => unavailableResult(),
  })
