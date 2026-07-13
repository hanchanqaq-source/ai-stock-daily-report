import type { ProviderCandidatePayload } from './providerCandidatePayloadFixture'
import type { ProviderReadonlyFailureResult } from './providerReadonlyTypes'

type UnknownRecord = Record<string, unknown>
type ProviderFailureStatus = ProviderReadonlyFailureResult['status']

export interface SanitizedProviderCandidateResult {
  readonly status: 'candidate'
  readonly providerLabel: 'REDACTED_PROVIDER_LABEL'
  readonly readOnly: true
  readonly redacted: true
  readonly candidate: ProviderCandidatePayload
  readonly errors: readonly []
  readonly warnings: readonly []
}

export interface SanitizedProviderFailureResult {
  readonly status: ProviderFailureStatus
  readonly providerLabel: 'REDACTED_PROVIDER_LABEL'
  readonly readOnly: true
  readonly redacted: true
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
}

export interface SanitizedProviderInvalidResult {
  readonly status: 'invalid-provider-result'
  readonly providerLabel: 'REDACTED_PROVIDER_LABEL'
  readonly readOnly: true
  readonly redacted: true
  readonly errors: readonly ['provider-readonly.invalid-provider-result']
  readonly warnings: readonly []
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
}

export type SanitizedProviderReadonlyPortResult =
  | SanitizedProviderCandidateResult
  | SanitizedProviderFailureResult
  | SanitizedProviderInvalidResult

const providerLabel = 'REDACTED_PROVIDER_LABEL' as const
const empty = Object.freeze([]) as readonly []
const invalidErrors = Object.freeze(['provider-readonly.invalid-provider-result'] as const)
const failureStatuses = new Set(['unavailable', 'timeout', 'credential-unavailable', 'invalid-response', 'blocked'])
const candidateFields = new Set(['status', 'providerLabel', 'readOnly', 'redacted', 'candidate', 'errors', 'warnings'])
const failureFields = new Set([
  'status',
  'providerLabel',
  'readOnly',
  'redacted',
  'errors',
  'warnings',
  'fallbackMode',
  'canFallbackToMockOnly',
])

const isPlainRecord = (value: unknown): value is UnknownRecord => {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false
  const prototype = Object.getPrototypeOf(value)
  return prototype === Object.prototype || prototype === null
}

const isEmptyArray = (value: unknown): value is readonly [] => Array.isArray(value) && value.length === 0

const invalidResult = (): SanitizedProviderInvalidResult =>
  Object.freeze({
    status: 'invalid-provider-result',
    providerLabel,
    readOnly: true,
    redacted: true,
    errors: invalidErrors,
    warnings: empty,
    fallbackMode: 'mock-only',
    canFallbackToMockOnly: true,
  })

const failureResult = (status: ProviderFailureStatus): SanitizedProviderFailureResult =>
  Object.freeze({
    status,
    providerLabel,
    readOnly: true,
    redacted: true,
    errors: Object.freeze([`provider-readonly.${status}`]),
    warnings: empty,
    fallbackMode: 'mock-only',
    canFallbackToMockOnly: true,
  })

const hasOnlyFields = (record: UnknownRecord, allowed: ReadonlySet<string>): boolean =>
  Object.keys(record).every((fieldName) => allowed.has(fieldName))

export const sanitizeProviderReadonlyPortResult = (input: unknown): SanitizedProviderReadonlyPortResult => {
  if (!isPlainRecord(input)) return invalidResult()
  if (input.providerLabel !== providerLabel || input.readOnly !== true || input.redacted !== true) return invalidResult()

  if (input.status === 'candidate') {
    if (!hasOnlyFields(input, candidateFields)) return invalidResult()
    if (!('candidate' in input) || input.candidate === undefined || input.candidate === null) return invalidResult()
    if (!isEmptyArray(input.errors) || !isEmptyArray(input.warnings)) return invalidResult()
    return Object.freeze({
      status: 'candidate',
      providerLabel,
      readOnly: true,
      redacted: true,
      candidate: input.candidate as ProviderCandidatePayload,
      errors: empty,
      warnings: empty,
    })
  }

  if (typeof input.status !== 'string' || !failureStatuses.has(input.status)) return invalidResult()
  if (!hasOnlyFields(input, failureFields)) return invalidResult()
  if (input.fallbackMode !== 'mock-only' || input.canFallbackToMockOnly !== true) return invalidResult()
  return failureResult(input.status as ProviderFailureStatus)
}
