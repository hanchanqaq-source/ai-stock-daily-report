import type { RealDailyReportDryRunInput } from '../dry-run/realDailyReportDryRunTypes'
import type { ProviderCandidatePayload } from './providerCandidatePayloadFixture'

export type ProviderReadonlyOutcome =
  | 'candidate'
  | 'unavailable'
  | 'timeout'
  | 'credential-unavailable'
  | 'invalid-response'
  | 'blocked'

export interface ProviderReadonlyRequest {
  readonly requestId: 'LOCAL_DRY_RUN_REQUEST'
  readonly mode: 'dry-run'
  readonly readOnly: true
  readonly projectName: '股票基金质量分析系统'
  readonly reportDisplayName: 'AI股票基金每日信息报告'
  readonly requestedAtLabel: 'MOCK_FRESHNESS_LABEL'
  readonly allowAccountWrite: false
  readonly allowTrading: false
  readonly allowNotificationSend: false
  readonly allowAiCall: false
  readonly requiresHumanApproval: true
}

export interface ProviderReadonlyCandidateResult {
  readonly status: 'candidate'
  readonly providerLabel: 'REDACTED_PROVIDER_LABEL'
  readonly readOnly: true
  readonly redacted: true
  readonly candidate: ProviderCandidatePayload
  readonly errors: readonly []
  readonly warnings: readonly string[]
}

export interface ProviderReadonlyFailureResult {
  readonly status: Exclude<ProviderReadonlyOutcome, 'candidate'>
  readonly providerLabel: 'REDACTED_PROVIDER_LABEL'
  readonly readOnly: true
  readonly redacted: true
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
}

export type ProviderReadonlyPortResult = ProviderReadonlyCandidateResult | ProviderReadonlyFailureResult

export type ProviderReadonlyPipelineOutcome = ProviderReadonlyOutcome | 'not-attempted' | 'unexpected'

interface ProviderReadonlyDryRunPipelineBaseResult {
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
  readonly allowRealProvider: false
  readonly allowRealAccountRead: false
  readonly allowNotificationSend: false
  readonly allowTrading: false
  readonly allowAiCall: false
  readonly requiresHumanApproval: true
  readonly providerAttempted: boolean
  readonly providerOutcome: ProviderReadonlyPipelineOutcome
  readonly fallbackUsed: boolean
  readonly candidateChainExecuted: boolean
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
}

export interface ProviderReadonlyDryRunPipelineDisabledResult extends ProviderReadonlyDryRunPipelineBaseResult {
  readonly status: 'disabled'
  readonly providerAttempted: false
  readonly providerOutcome: 'not-attempted'
  readonly fallbackUsed: false
  readonly candidateChainExecuted: false
}

export interface ProviderReadonlyDryRunPipelineBlockedResult extends ProviderReadonlyDryRunPipelineBaseResult {
  readonly status: 'blocked'
}

export interface ProviderReadonlyDryRunPipelineCompletedResult extends ProviderReadonlyDryRunPipelineBaseResult {
  readonly status: 'completed-mock-only'
  readonly normalizedInput: RealDailyReportDryRunInput
}

export type ProviderReadonlyDryRunPipelineResult =
  | ProviderReadonlyDryRunPipelineDisabledResult
  | ProviderReadonlyDryRunPipelineBlockedResult
  | ProviderReadonlyDryRunPipelineCompletedResult

export const DEFAULT_PROVIDER_READONLY_REQUEST: ProviderReadonlyRequest = Object.freeze({
  requestId: 'LOCAL_DRY_RUN_REQUEST',
  mode: 'dry-run',
  readOnly: true,
  projectName: '股票基金质量分析系统',
  reportDisplayName: 'AI股票基金每日信息报告',
  requestedAtLabel: 'MOCK_FRESHNESS_LABEL',
  allowAccountWrite: false,
  allowTrading: false,
  allowNotificationSend: false,
  allowAiCall: false,
  requiresHumanApproval: true,
})
