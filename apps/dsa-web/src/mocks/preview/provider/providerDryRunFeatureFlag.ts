export type ProviderDryRunFeatureFlagState = 'disabled' | 'enabled-mock-only' | 'blocked'

export interface ProviderDryRunFeatureFlagConfig {
  readonly enabled: boolean
  readonly mode: 'mock-only'
  readonly allowRealProvider: false
  readonly allowRealAccountRead: false
  readonly allowNotificationSend: false
  readonly allowTrading: false
  readonly allowAiCall: false
  readonly requiresHumanApproval: true
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
}

export interface ProviderDryRunFeatureFlagResult {
  readonly state: ProviderDryRunFeatureFlagState
  readonly enabled: boolean
  readonly mode: 'mock-only'
  readonly canRunMockOnlyCandidateChain: boolean
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
  readonly allowRealProvider: false
  readonly allowRealAccountRead: false
  readonly allowNotificationSend: false
  readonly allowTrading: false
  readonly allowAiCall: false
  readonly requiresHumanApproval: true
}

type UnknownRecord = Record<string, unknown>

type CapabilityField =
  | 'allowRealProvider'
  | 'allowRealAccountRead'
  | 'allowNotificationSend'
  | 'allowTrading'
  | 'allowAiCall'

export const DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG: ProviderDryRunFeatureFlagConfig = Object.freeze({
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

const SENSITIVE_UNKNOWN_FIELDS = new Set<string>([
  'providerClient',
  'providerUrl',
  'endpoint',
  'requestUrl',
  'accountId',
  'credential',
  'authorization',
  'token',
  'webhook',
  'apiKey',
  'api_key',
  'secret',
  'password',
  'headers',
  'cookies',
  'rawResponse',
  'providerResponse',
  'realProviderEnabled',
  'useRealProvider',
  'providerEnabled',
] as const)

const CAPABILITY_ERROR_CODES: Record<CapabilityField, string> = {
  allowRealProvider: 'feature-flag.real-provider-forbidden',
  allowRealAccountRead: 'feature-flag.real-account-read-forbidden',
  allowNotificationSend: 'feature-flag.notification-forbidden',
  allowTrading: 'feature-flag.trading-forbidden',
  allowAiCall: 'feature-flag.ai-call-forbidden',
}

const capabilityFields = Object.keys(CAPABILITY_ERROR_CODES) as CapabilityField[]

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const appendError = (errors: string[], code: string, path: string): void => {
  errors.push(`${code}:${path}`)
}

const buildResult = (
  state: ProviderDryRunFeatureFlagState,
  enabled: boolean,
  errors: readonly string[],
): ProviderDryRunFeatureFlagResult =>
  Object.freeze({
    state,
    enabled: state === 'blocked' ? false : enabled,
    mode: 'mock-only',
    canRunMockOnlyCandidateChain: state === 'enabled-mock-only',
    errors: Object.freeze([...errors]),
    warnings: Object.freeze([]),
    fallbackMode: 'mock-only',
    canFallbackToMockOnly: true,
    allowRealProvider: false,
    allowRealAccountRead: false,
    allowNotificationSend: false,
    allowTrading: false,
    allowAiCall: false,
    requiresHumanApproval: true,
  })

export const evaluateProviderDryRunFeatureFlag = (input?: unknown): ProviderDryRunFeatureFlagResult => {
  if (input === undefined) return buildResult('disabled', DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG.enabled, [])

  if (!isRecord(input)) return buildResult('blocked', false, ['feature-flag.invalid-input:input'])

  const errors: string[] = []

  for (const fieldName of Object.keys(input)) {
    if (SENSITIVE_UNKNOWN_FIELDS.has(fieldName)) {
      appendError(errors, 'feature-flag.unknown-sensitive-field', `input.${fieldName}`)
    }
  }

  if ('enabled' in input && typeof input.enabled !== 'boolean') {
    appendError(errors, 'feature-flag.invalid-enabled', 'input.enabled')
  }

  if ('mode' in input && input.mode !== 'mock-only') {
    appendError(errors, 'feature-flag.mode-must-be-mock-only', 'input.mode')
  }

  for (const fieldName of capabilityFields) {
    if (input[fieldName] === true) appendError(errors, CAPABILITY_ERROR_CODES[fieldName], `input.${fieldName}`)
  }

  if ('requiresHumanApproval' in input && input.requiresHumanApproval !== true) {
    appendError(errors, 'feature-flag.human-approval-required', 'input.requiresHumanApproval')
  }

  if ('fallbackMode' in input && input.fallbackMode !== 'mock-only') {
    appendError(errors, 'feature-flag.fallback-must-be-mock-only', 'input.fallbackMode')
  }

  if ('canFallbackToMockOnly' in input && input.canFallbackToMockOnly !== true) {
    appendError(errors, 'feature-flag.fallback-must-be-mock-only', 'input.canFallbackToMockOnly')
  }

  if (errors.length > 0) return buildResult('blocked', false, errors)

  const enabled = typeof input.enabled === 'boolean' ? input.enabled : DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG.enabled
  return buildResult(enabled ? 'enabled-mock-only' : 'disabled', enabled, [])
}
