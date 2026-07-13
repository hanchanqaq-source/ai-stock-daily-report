import type { RealDailyReportDryRunInput } from '../dry-run/realDailyReportDryRunTypes'
import type { ProviderCandidatePayload } from './providerCandidatePayloadFixture'
import { normalizeProviderCandidatePayloadToDryRunInput } from './providerCandidatePayloadNormalizer'
import { evaluateProviderDryRunFeatureFlag } from './providerDryRunFeatureFlag'

export interface ProviderDryRunGateInput {
  readonly featureFlag?: unknown
  readonly candidate?: unknown
}

export interface ProviderDryRunGateDisabledResult {
  readonly status: 'disabled'
  readonly featureFlagState: 'disabled'
  readonly candidateChainExecuted: false
  readonly errors: readonly []
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

export interface ProviderDryRunGateBlockedResult {
  readonly status: 'blocked'
  readonly featureFlagState: 'blocked' | 'enabled-mock-only'
  readonly blockedStage: 'gate-input' | 'feature-flag' | 'candidate-chain' | 'unexpected'
  readonly candidateChainExecuted: boolean
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

export interface ProviderDryRunGateCompletedResult {
  readonly status: 'completed-mock-only'
  readonly featureFlagState: 'enabled-mock-only'
  readonly candidateChainExecuted: true
  readonly errors: readonly []
  readonly warnings: readonly string[]
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
  readonly allowRealProvider: false
  readonly allowRealAccountRead: false
  readonly allowNotificationSend: false
  readonly allowTrading: false
  readonly allowAiCall: false
  readonly requiresHumanApproval: true
  readonly normalizedInput: RealDailyReportDryRunInput
}

export type ProviderDryRunGateResult =
  | ProviderDryRunGateDisabledResult
  | ProviderDryRunGateBlockedResult
  | ProviderDryRunGateCompletedResult

type UnknownRecord = Record<string, unknown>

const ALLOWED_GATE_INPUT_FIELDS = new Set(['featureFlag', 'candidate'] as const)
const ALLOWED_CANDIDATE_CHAIN_ERRORS = new Set([
  'candidate-validation.blocked',
  'normalized-dry-run-validation.blocked',
  'normalization.failed',
] as const)

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const freezeStringArray = (items: readonly string[]): readonly string[] => Object.freeze([...items])

const baseSafety = {
  fallbackMode: 'mock-only',
  canFallbackToMockOnly: true,
  allowRealProvider: false,
  allowRealAccountRead: false,
  allowNotificationSend: false,
  allowTrading: false,
  allowAiCall: false,
  requiresHumanApproval: true,
} as const

const disabledResult = (warnings: readonly string[] = []): ProviderDryRunGateDisabledResult =>
  Object.freeze({
    status: 'disabled',
    featureFlagState: 'disabled',
    candidateChainExecuted: false,
    errors: Object.freeze([]) as readonly [],
    warnings: freezeStringArray(warnings),
    ...baseSafety,
  })

const blockedResult = (
  featureFlagState: ProviderDryRunGateBlockedResult['featureFlagState'],
  blockedStage: ProviderDryRunGateBlockedResult['blockedStage'],
  candidateChainExecuted: boolean,
  errors: readonly string[],
  warnings: readonly string[] = [],
): ProviderDryRunGateBlockedResult =>
  Object.freeze({
    status: 'blocked',
    featureFlagState,
    blockedStage,
    candidateChainExecuted,
    errors: freezeStringArray(errors),
    warnings: freezeStringArray(warnings),
    ...baseSafety,
  })

const completedResult = (
  normalizedInput: RealDailyReportDryRunInput,
  warnings: readonly string[],
): ProviderDryRunGateCompletedResult =>
  Object.freeze({
    status: 'completed-mock-only',
    featureFlagState: 'enabled-mock-only',
    candidateChainExecuted: true,
    errors: Object.freeze([]) as readonly [],
    warnings: freezeStringArray(warnings),
    ...baseSafety,
    normalizedInput,
  })

const sanitizeCandidateChainErrors = (errors: readonly string[]): readonly string[] => {
  const safeErrors = errors.filter((error) => ALLOWED_CANDIDATE_CHAIN_ERRORS.has(error as never))
  return safeErrors.length > 0 ? safeErrors : ['provider-dry-run-gate.candidate-chain-blocked']
}

export const runProviderDryRunGate = (input?: unknown): ProviderDryRunGateResult => {
  try {
    if (input === undefined) {
      const featureFlag = evaluateProviderDryRunFeatureFlag(undefined)
      if (featureFlag.state === 'disabled') return disabledResult(featureFlag.warnings)
      if (featureFlag.state === 'blocked') {
        return blockedResult('blocked', 'feature-flag', false, featureFlag.errors, featureFlag.warnings)
      }
    }

    if (!isRecord(input)) {
      return blockedResult('blocked', 'gate-input', false, ['provider-dry-run-gate.invalid-input'])
    }

    const unknownInputFields = Object.keys(input)
      .filter((fieldName) => !ALLOWED_GATE_INPUT_FIELDS.has(fieldName as never))
      .map((fieldName) => `provider-dry-run-gate.unknown-field:input.${fieldName}`)
    if (unknownInputFields.length > 0) {
      return blockedResult('blocked', 'gate-input', false, unknownInputFields)
    }

    const featureFlag = evaluateProviderDryRunFeatureFlag(input.featureFlag)
    if (featureFlag.state === 'disabled') return disabledResult(featureFlag.warnings)
    if (featureFlag.state === 'blocked') {
      return blockedResult('blocked', 'feature-flag', false, featureFlag.errors, featureFlag.warnings)
    }

    if (!('candidate' in input)) {
      return blockedResult('enabled-mock-only', 'gate-input', false, ['provider-dry-run-gate.candidate-required'])
    }

    const normalization = normalizeProviderCandidatePayloadToDryRunInput(input.candidate as ProviderCandidatePayload)
    if (normalization.status === 'normalized' && normalization.normalizedInput) {
      return completedResult(normalization.normalizedInput, normalization.warnings)
    }

    return blockedResult(
      'enabled-mock-only',
      'candidate-chain',
      true,
      sanitizeCandidateChainErrors(normalization.errors),
      normalization.warnings,
    )
  } catch {
    return blockedResult('blocked', 'unexpected', false, ['provider-dry-run-gate.failed'])
  }
}
