import type { RealDailyReportDryRunInput } from '../dry-run/realDailyReportDryRunTypes'
import { MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE } from './providerCandidatePayloadFixture'
import { evaluateProviderDryRunFeatureFlag } from './providerDryRunFeatureFlag'
import { runProviderDryRunGate } from './providerDryRunGate'
import { inspectProviderCredentialBoundary } from './providerCredentialBoundary'
import { sanitizeProviderReadonlyPortResult } from './providerReadonlyResultSanitizer'
import type { ProviderReadonlyPort } from './providerReadonlyPort'
import { createDisabledProviderReadonlyPort } from './providerReadonlyDisabledPort'
import {
  DEFAULT_PROVIDER_READONLY_REQUEST,
  type ProviderReadonlyDryRunPipelineResult,
  type ProviderReadonlyPipelineOutcome,
  type ProviderReadonlyRequest,
} from './providerReadonlyTypes'

type UnknownRecord = Record<string, unknown>

interface ProviderReadonlyDryRunPipelineInput {
  readonly featureFlag?: unknown
  readonly request?: unknown
  readonly provider?: ProviderReadonlyPort
}

const allowedInputFields = new Set(['featureFlag', 'request', 'provider'] as const)
const sensitiveInputFields = new Set([
  'token',
  'apiKey',
  'api_key',
  'secret',
  'password',
  'credential',
  'credentials',
  'endpoint',
  'requestUrl',
  'headers',
  'cookies',
  'rawResponse',
  'responseBody',
  'accountId',
  'accountNumber',
])
const allowedRequestFields = new Set(Object.keys(DEFAULT_PROVIDER_READONLY_REQUEST))
const sensitiveRequestFields = new Set([
  'accountNumber',
  'accountId',
  'fundCode',
  'stockCode',
  'endpoint',
  'url',
  'requestUrl',
  'token',
  'apiKey',
  'cookie',
  'email',
  'phone',
])

const isRecord = (value: unknown): value is UnknownRecord => typeof value === 'object' && value !== null && !Array.isArray(value)

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

const buildResult = (
  status: ProviderReadonlyDryRunPipelineResult['status'],
  providerAttempted: boolean,
  providerOutcome: ProviderReadonlyPipelineOutcome,
  fallbackUsed: boolean,
  candidateChainExecuted: boolean,
  errors: readonly string[],
  warnings: readonly string[] = [],
  normalizedInput?: RealDailyReportDryRunInput,
): ProviderReadonlyDryRunPipelineResult => {
  const result = {
    status,
    ...baseSafety,
    providerAttempted,
    providerOutcome,
    fallbackUsed,
    candidateChainExecuted,
    errors: freezeStringArray(errors),
    warnings: freezeStringArray(warnings),
  } as Record<string, unknown>
  if (status === 'completed-mock-only') result.normalizedInput = normalizedInput
  return Object.freeze(result) as unknown as ProviderReadonlyDryRunPipelineResult
}

const validateProviderReadonlyRequest = (request: unknown): { request?: ProviderReadonlyRequest; errors: readonly string[] } => {
  if (request === undefined) return { request: DEFAULT_PROVIDER_READONLY_REQUEST, errors: [] }
  if (!isRecord(request)) return { errors: ['provider-readonly-request.invalid-input:request'] }
  const errors: string[] = []
  for (const fieldName of Object.keys(request)) {
    if (allowedRequestFields.has(fieldName)) continue
    errors.push(
      sensitiveRequestFields.has(fieldName)
        ? `provider-readonly-request.sensitive-field:request.${fieldName}`
        : `provider-readonly-request.unknown-field:request.${fieldName}`,
    )
  }
  const expected = DEFAULT_PROVIDER_READONLY_REQUEST as unknown as UnknownRecord
  for (const fieldName of allowedRequestFields) {
    if (request[fieldName] !== expected[fieldName]) errors.push(`provider-readonly-request.invalid-field:request.${fieldName}`)
  }
  return errors.length > 0 ? { errors } : { request: request as unknown as ProviderReadonlyRequest, errors: [] }
}

export const runProviderReadonlyDryRunPipeline = async (input?: unknown): Promise<ProviderReadonlyDryRunPipelineResult> => {
  let providerAttempted = false
  if (input !== undefined && !isRecord(input)) {
    return buildResult('blocked', false, 'blocked', false, false, ['provider-readonly-pipeline.invalid-input:input'])
  }

  const record = (input ?? {}) as ProviderReadonlyDryRunPipelineInput & UnknownRecord
  const unknownInputFields = Object.keys(record).filter((fieldName) => !allowedInputFields.has(fieldName as never))
  if (unknownInputFields.length > 0) {
    return buildResult(
      'blocked',
      false,
      'blocked',
      false,
      false,
      unknownInputFields.map((fieldName) =>
        sensitiveInputFields.has(fieldName)
          ? `provider-readonly-pipeline.sensitive-field:input.${fieldName}`
          : `provider-readonly-pipeline.unknown-field:input.${fieldName}`,
      ),
    )
  }

  const featureFlag = evaluateProviderDryRunFeatureFlag(input === undefined ? undefined : record.featureFlag)
  if (featureFlag.state === 'disabled') return buildResult('disabled', false, 'not-attempted', false, false, [], featureFlag.warnings)
  if (featureFlag.state === 'blocked')
    return buildResult('blocked', false, 'blocked', false, false, featureFlag.errors, featureFlag.warnings)

  const requestValidation = validateProviderReadonlyRequest(record.request)
  if (!requestValidation.request) return buildResult('blocked', false, 'blocked', false, false, requestValidation.errors)

  const credentialBoundary = inspectProviderCredentialBoundary()
  if (credentialBoundary.status === 'blocked') {
    return buildResult('blocked', false, 'blocked', false, false, ['provider-credential-boundary.blocked'])
  }

  const provider = record.provider ?? createDisabledProviderReadonlyPort()
  try {
    providerAttempted = true
    const rawProviderResult = await provider.readCandidate(requestValidation.request)
    const providerResult = sanitizeProviderReadonlyPortResult(rawProviderResult)
    if (providerResult.status === 'candidate') {
      const gate = runProviderDryRunGate({
        featureFlag: { enabled: true },
        candidate: providerResult.candidate,
      })
      if (gate.status === 'completed-mock-only') {
        return buildResult('completed-mock-only', true, 'candidate', false, true, [], gate.warnings, gate.normalizedInput)
      }
      return buildResult('blocked', true, 'candidate', false, gate.candidateChainExecuted, gate.errors, gate.warnings)
    }

    if (['unavailable', 'timeout', 'credential-unavailable'].includes(providerResult.status)) {
      const gate = runProviderDryRunGate({
        featureFlag: { enabled: true },
        candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE,
      })
      const warning = `provider-readonly.fallback-after-${providerResult.status}`
      if (gate.status === 'completed-mock-only') {
        return buildResult(
          'completed-mock-only',
          true,
          providerResult.status,
          true,
          true,
          [],
          [warning, ...gate.warnings],
          gate.normalizedInput,
        )
      }
      return buildResult('blocked', true, providerResult.status, true, gate.candidateChainExecuted, gate.errors, [
        warning,
        ...gate.warnings,
      ])
    }

    return buildResult('blocked', true, providerResult.status, false, false, providerResult.errors, providerResult.warnings)
  } catch {
    return buildResult('blocked', providerAttempted, 'unexpected', false, false, ['provider-readonly-pipeline.failed'])
  }
}
