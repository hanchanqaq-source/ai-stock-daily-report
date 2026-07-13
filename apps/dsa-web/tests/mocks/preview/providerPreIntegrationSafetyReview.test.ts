import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { basename, join } from 'node:path'
import { describe, expect, it } from 'vitest'
import type { RealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunTypes'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'
import {
  MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE,
  type ProviderCandidatePayload,
} from '../../../src/mocks/preview/provider/providerCandidatePayloadFixture'
import { normalizeProviderCandidatePayloadToDryRunInput } from '../../../src/mocks/preview/provider/providerCandidatePayloadNormalizer'
import { validateProviderCandidatePayload } from '../../../src/mocks/preview/provider/providerCandidatePayloadValidator'
import {
  DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG,
  evaluateProviderDryRunFeatureFlag,
} from '../../../src/mocks/preview/provider/providerDryRunFeatureFlag'
import { runProviderDryRunGate } from '../../../src/mocks/preview/provider/providerDryRunGate'
import { inspectProviderCredentialBoundary } from '../../../src/mocks/preview/provider/providerCredentialBoundary'
import { createDisabledProviderReadonlyPort } from '../../../src/mocks/preview/provider/providerReadonlyDisabledPort'
import { runProviderReadonlyDryRunPipeline } from '../../../src/mocks/preview/provider/providerReadonlyDryRunPipeline'

type Mutable<T> = { -readonly [P in keyof T]: T[P] extends readonly (infer U)[] ? Mutable<U>[] : T[P] }
type MutableCandidate = Mutable<ProviderCandidatePayload> & Record<string, unknown>
type MutableDryRunInput = Mutable<RealDailyReportDryRunInput> & Record<string, unknown>

const runtimeSearchRoots = [
  'src/main.tsx',
  'src/App.tsx',
  'src/api',
  'src/pages',
  'src/stores',
  'src/components',
  'src/contexts',
  'src/utils',
] as const

const providerSourcePaths = [
  'src/mocks/preview/provider/providerCandidatePayloadFixture.ts',
  'src/mocks/preview/provider/providerCandidatePayloadValidator.ts',
  'src/mocks/preview/provider/providerCandidatePayloadNormalizer.ts',
  'src/mocks/preview/provider/providerDryRunFeatureFlag.ts',
  'src/mocks/preview/provider/providerDryRunGate.ts',
  'src/mocks/preview/provider/providerReadonlyTypes.ts',
  'src/mocks/preview/provider/providerReadonlyPort.ts',
  'src/mocks/preview/provider/providerCredentialBoundary.ts',
  'src/mocks/preview/provider/providerReadonlyDisabledPort.ts',
  'src/mocks/preview/provider/providerReadonlyDryRunPipeline.ts',
] as const

const collectTypeScriptFiles = (path: string): string[] => {
  if (!existsSync(path)) return []
  if (statSync(path).isFile()) return path.endsWith('.ts') || path.endsWith('.tsx') ? [path] : []

  const files: string[] = []
  for (const entry of readdirSync(path)) {
    const fullPath = join(path, entry)
    if (statSync(fullPath).isDirectory()) files.push(...collectTypeScriptFiles(fullPath))
    else if (entry.endsWith('.ts') || entry.endsWith('.tsx')) files.push(fullPath)
  }
  return files
}

const readSource = (sourcePath: string): string => readFileSync(sourcePath, 'utf-8')
const cloneCandidate = (): MutableCandidate => structuredClone(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE) as MutableCandidate

const normalizeFixture = (): RealDailyReportDryRunInput => {
  const candidateValidation = validateProviderCandidatePayload(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
  expect(candidateValidation.status).toBe('passed')
  expect(candidateValidation.normalizationAllowed).toBe(true)

  const normalization = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
  expect(normalization.status).toBe('normalized')
  expect(normalization.normalizedInput).toBeDefined()
  expect(normalization.fallbackMode).toBe('mock-only')
  expect(normalization.canFallbackToMockOnly).toBe(true)

  const dryRunValidation = validateRealDailyReportDryRunInput(normalization.normalizedInput!)
  expect(dryRunValidation.status).toBe('passed')
  expect(dryRunValidation.fallbackMode).toBe('mock-only')
  expect(dryRunValidation.canFallbackToMockOnly).toBe(true)
  return normalization.normalizedInput!
}

const expectNoRawValuesInErrors = (errors: readonly string[], rawValues: readonly string[]) => {
  expect(errors.length).toBeGreaterThan(0)
  const serializedErrors = JSON.stringify(errors)
  for (const rawValue of rawValues) expect(serializedErrors).not.toContain(rawValue)
}

describe('Web-P48 pre-integration provider safety review', () => {
  it('keeps the existing candidate validator to normalizer to dry-run validator chain mock-only', () => {
    const normalizedInput = normalizeFixture()
    expect(normalizedInput.source.sourceType).toBe('mock-only')
    expect(normalizedInput.rollback.fallbackMode).toBe('mock-only')
    expect(normalizedInput.rollback.canFallbackToMockOnly).toBe(true)
  })

  it('keeps every real capability disabled in normalizedInput', () => {
    const normalizedInput = normalizeFixture()
    expect(normalizedInput).toMatchObject({
      source: {
        sourceType: 'mock-only',
        providerName: 'REDACTED_PROVIDER_LABEL',
        isMock: true,
        isRealReadOnly: false,
        isRedacted: true,
      },
      safety: {
        allowRealProvider: false,
        allowRealAccountRead: false,
        allowNotificationSend: false,
        allowTrading: false,
        allowAiCall: false,
        requiresHumanApproval: true,
      },
      redaction: {
        containsRealAccountData: false,
        containsSecrets: false,
        containsWebhook: false,
        containsToken: false,
        containsApiKey: false,
        containsPersonalContact: false,
      },
      rollback: { fallbackMode: 'mock-only', canFallbackToMockOnly: true },
    })
  })

  it('keeps provider candidate modules out of runtime, preview entry, and preview model import paths', () => {
    const guardedPaths = [
      'src/mocks/preview-entry/mockOnlyPreviewEntry.ts',
      'src/mocks/preview/mockOnlyPreviewModel.ts',
      ...runtimeSearchRoots.flatMap((root) => collectTypeScriptFiles(root)),
    ]
    const forbiddenImports = [
      'providerCandidatePayloadFixture',
      'providerCandidatePayloadValidator',
      'providerCandidatePayloadNormalizer',
      'MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE',
      'validateProviderCandidatePayload',
      'normalizeProviderCandidatePayloadToDryRunInput',
      'providerDryRunFeatureFlag',
      'evaluateProviderDryRunFeatureFlag',
      'providerDryRunGate',
      'runProviderDryRunGate',
      'providerReadonlyDryRunPipeline',
      'runProviderReadonlyDryRunPipeline',
    ] as const

    for (const sourcePath of guardedPaths) {
      const source = readSource(sourcePath)
      for (const forbiddenImport of forbiddenImports) {
        expect(source, `${sourcePath} must not import ${forbiddenImport}`).not.toContain(forbiddenImport)
      }
    }
  })

  it('does not add real provider implementation files to the mock-only provider directory', () => {
    const providerDir = 'src/mocks/preview/provider'
    const allowedFiles = new Set(providerSourcePaths.map((sourcePath) => basename(sourcePath)))
    const forbiddenRealProviderFiles = new Set([
      'providerClient.ts',
      'realProviderClient.ts',
      'providerApi.ts',
      'providerService.ts',
      'providerHttpClient.ts',
      'accountClient.ts',
      'marketDataClient.ts',
      'credentialLoader.ts',
      'authProvider.ts',
    ])

    const actualFiles = readdirSync(providerDir).filter((entry) => entry.endsWith('.ts'))
    expect(actualFiles.sort()).toEqual([...allowedFiles].sort())
    for (const fileName of actualFiles) expect(forbiddenRealProviderFiles.has(fileName)).toBe(false)
  })

  it('keeps provider fixture, validator, and normalizer free of external capabilities', () => {
    const forbiddenPatterns = [
      /\bfetch\b/,
      /\baxios\b/,
      /\bXMLHttpRequest\b/,
      /\bWebSocket\b/,
      /\bEventSource\b/,
      /\blocalStorage\b/,
      /\bsessionStorage\b/,
      /\bindexedDB\b/,
      /\bNotification\b/,
      /\bServiceWorker\b/,
      /\bsendBeacon\b/,
      /\bFileReader\b/,
      /\bprocess\.env\b/,
      /\bimport\.meta\.env\b/,
      /\bDate\.now\b/,
      /\bnew Date\b/,
      /\bMath\.random\b/,
      /\bsetTimeout\b/,
      /\bsetInterval\b/,
      /\bOpenAI\b/,
      /\bDeepSeek\b/,
      /智谱/,
      /\bLangChain\b/,
      /https?:\/\//,
      /\blocalhost\b/,
      /\b127\.0\.0\.1\b/,
      /\b0\.0\.0\.0\b/,
    ] as const

    for (const sourcePath of providerSourcePaths) {
      const source = readSource(sourcePath)
      for (const forbiddenPattern of forbiddenPatterns) {
        expect(source, `${sourcePath} must not contain ${forbiddenPattern}`).not.toMatch(forbiddenPattern)
      }
    }
  })

  it('has no runtime feature flag or config entry that can enable a real provider', () => {
    const runtimeFiles = runtimeSearchRoots.flatMap((root) => collectTypeScriptFiles(root))
    const forbiddenEnabledFlags = [
      /enableRealProvider\s*:\s*true/,
      /allowRealProvider\s*:\s*true/,
      /providerEnabled\s*:\s*true/,
      /realProviderEnabled\s*:\s*true/,
      /useRealProvider\s*:\s*true/,
    ] as const

    for (const sourcePath of runtimeFiles) {
      const source = readSource(sourcePath)
      for (const forbiddenFlag of forbiddenEnabledFlags) {
        expect(source, `${sourcePath} must not enable real provider`).not.toMatch(forbiddenFlag)
      }
    }
  })

  it('keeps Web-P49 provider dry-run feature flag default-closed and mock-only', () => {
    expect(DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG.enabled).toBe(false)
    expect(Object.isFrozen(DEFAULT_PROVIDER_DRY_RUN_FEATURE_FLAG)).toBe(true)

    const defaultResult = evaluateProviderDryRunFeatureFlag()
    expect(defaultResult.state).toBe('disabled')
    expect(defaultResult.enabled).toBe(false)
    expect(defaultResult.canRunMockOnlyCandidateChain).toBe(false)

    const enabledResult = evaluateProviderDryRunFeatureFlag({ enabled: true })
    expect(enabledResult.state).toBe('enabled-mock-only')
    expect(enabledResult.canRunMockOnlyCandidateChain).toBe(true)
    expect(enabledResult.allowRealProvider).toBe(false)
    expect(enabledResult.allowRealAccountRead).toBe(false)
    expect(enabledResult.allowNotificationSend).toBe(false)
    expect(enabledResult.allowTrading).toBe(false)
    expect(enabledResult.allowAiCall).toBe(false)
    expect(enabledResult.requiresHumanApproval).toBe(true)
    expect(enabledResult.fallbackMode).toBe('mock-only')
    expect(enabledResult.canFallbackToMockOnly).toBe(true)

    const blockedResult = evaluateProviderDryRunFeatureFlag({ enabled: true, allowRealProvider: true })
    expect(blockedResult.state).toBe('blocked')
    expect(blockedResult.enabled).toBe(false)
    expect(blockedResult.canRunMockOnlyCandidateChain).toBe(false)
    expect(blockedResult.errors.length).toBeGreaterThan(0)
  })

  it('keeps Web-P49 feature flag disconnected from candidate chain and runtime', () => {
    const featureFlagSource = readSource('src/mocks/preview/provider/providerDryRunFeatureFlag.ts')
    for (const forbidden of [
      'validateProviderCandidatePayload',
      'normalizeProviderCandidatePayloadToDryRunInput',
      'validateRealDailyReportDryRunInput',
      'realDailyReportDryRunAdapter',
      'adaptRealDailyReportDryRunInputToViewModel',
      'DailyReportViewModel',
    ]) {
      expect(featureFlagSource).not.toContain(forbidden)
    }

    const guardedPaths = [
      'src/mocks/preview-entry/mockOnlyPreviewEntry.ts',
      'src/mocks/preview/mockOnlyPreviewModel.ts',
      ...runtimeSearchRoots.flatMap((root) => collectTypeScriptFiles(root)),
    ]
    for (const sourcePath of guardedPaths) {
      const source = readSource(sourcePath)
      expect(source).not.toContain('providerDryRunFeatureFlag')
      expect(source).not.toContain('evaluateProviderDryRunFeatureFlag')
    }
  })


  it('keeps Web-M1B provider dry-run gate default-closed, mock-only, and disconnected from runtime', () => {
    const disabled = runProviderDryRunGate()
    expect(disabled.status).toBe('disabled')
    expect(disabled.candidateChainExecuted).toBe(false)
    expect(disabled).not.toHaveProperty('normalizedInput')

    const completed = runProviderDryRunGate({ featureFlag: { enabled: true }, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
    expect(completed.status).toBe('completed-mock-only')
    expect(completed.candidateChainExecuted).toBe(true)
    expect(completed.allowRealProvider).toBe(false)
    expect(completed.fallbackMode).toBe('mock-only')
    if (completed.status === 'completed-mock-only') expect(completed.normalizedInput.source.sourceType).toBe('mock-only')

    const gateSource = readSource('src/mocks/preview/provider/providerDryRunGate.ts')
    for (const forbidden of [
      'realDailyReportDryRunAdapter',
      'adaptRealDailyReportDryRunInputToViewModel',
      'DailyReportViewModel',
      'src/pages',
      'src/components',
    ]) {
      expect(gateSource).not.toContain(forbidden)
    }
  })


  it('propagates blocked candidate validation without normalizedInput or raw error leakage', () => {
    const candidate = cloneCandidate()
    candidate.providerType = 'REAL_PROVIDER_TYPE_DRIFT'
    candidate.sourceLabel = 'REAL_SOURCE_LABEL_DRIFT'
    candidate.candidateId = 'REAL_CANDIDATE_ID_DRIFT'
    candidate.rawResponse = 'RAW_RESPONSE_SHOULD_NOT_LEAK'
    candidate.apiKey = 'API_KEY_SHOULD_NOT_LEAK'
    candidate.sections[0].summary = 'external marker hxxps://example.invalid should be blocked'.replace('hxxps', 'https')
    candidate.metrics[0].valueLabel = '12345.6789'
    candidate.riskSignals[0].valueLabel = '立即执行交易'
    candidate.safetyLabels = []
    candidate.redactionLabels = []

    const candidateValidation = validateProviderCandidatePayload(candidate as ProviderCandidatePayload)
    expect(candidateValidation.status).toBe('blocked')
    expect(candidateValidation.normalizationAllowed).toBe(false)
    expect(candidateValidation.errors.length).toBeGreaterThan(0)

    const normalization = normalizeProviderCandidatePayloadToDryRunInput(candidate as ProviderCandidatePayload)
    expect(normalization.status).toBe('blocked')
    expect(normalization.errors).toEqual(['candidate-validation.blocked'])
    expect(normalization.normalizedInput).toBeUndefined()
    expect(normalization.fallbackMode).toBe('mock-only')
    expect(normalization.canFallbackToMockOnly).toBe(true)
    expectNoRawValuesInErrors(normalization.errors, [
      'REAL_PROVIDER_TYPE_DRIFT',
      'REAL_SOURCE_LABEL_DRIFT',
      'REAL_CANDIDATE_ID_DRIFT',
      'RAW_RESPONSE_SHOULD_NOT_LEAK',
      'API_KEY_SHOULD_NOT_LEAK',
      'example.invalid',
      '12345.6789',
      '立即执行交易',
    ])
  })

  it('blocks unsafe mutations after normalization in the dry-run validator', () => {
    const normalizedInput = normalizeFixture()
    const unsafeInput = structuredClone(normalizedInput) as MutableDryRunInput
    unsafeInput.safety.allowRealProvider = true
    unsafeInput.safety.allowRealAccountRead = true
    unsafeInput.safety.allowNotificationSend = true
    unsafeInput.safety.allowTrading = true
    unsafeInput.safety.allowAiCall = true
    unsafeInput.safety.requiresHumanApproval = false
    unsafeInput.rollback.fallbackMode = 'real-provider'
    unsafeInput.rollback.canFallbackToMockOnly = false
    unsafeInput.source.sourceType = 'real-readonly'
    unsafeInput.source.isRealReadOnly = true

    expect(normalizedInput.source.sourceType).toBe('mock-only')
    expect(normalizedInput.source.isRealReadOnly).toBe(false)
    const result = validateRealDailyReportDryRunInput(unsafeInput as RealDailyReportDryRunInput)
    expect(result.status).toBe('blocked')
    expect(result.errors).toEqual(
      expect.arrayContaining([
        'safety.allowRealProvider.must-be-false',
        'safety.allowRealAccountRead.must-be-false',
        'safety.allowNotificationSend.must-be-false',
        'safety.allowTrading.must-be-false',
        'safety.allowAiCall.must-be-false',
        'safety.requiresHumanApproval.must-be-true',
        'rollback.fallbackMode.must-be-mock-only',
        'rollback.canFallbackToMockOnly.must-be-true',
      ]),
    )
    expect(result.fallbackMode).toBe('mock-only')
    expect(result.canFallbackToMockOnly).toBe(true)
  })


  it('keeps Core-M2 disabled provider, credential boundary, and pipeline mock-only NO-GO', async () => {
    const credential = inspectProviderCredentialBoundary()
    expect(credential).toMatchObject({ status: 'not-configured', hasCredential: false, secretMaterialAccessible: false, environmentReadAllowed: false, storageReadAllowed: false })

    const provider = createDisabledProviderReadonlyPort()
    expect(provider).toMatchObject({ networkEnabled: false, credentialReadEnabled: false, accountReadEnabled: false, providerLabel: 'REDACTED_PROVIDER_LABEL' })
    const providerResult = await provider.readCandidate({} as never)
    expect(providerResult).toMatchObject({ status: 'unavailable', fallbackMode: 'mock-only', canFallbackToMockOnly: true })
    expect(providerResult).not.toHaveProperty('candidate')

    const pipelineDisabled = await runProviderReadonlyDryRunPipeline()
    expect(pipelineDisabled).toMatchObject({ status: 'disabled', providerAttempted: false, providerOutcome: 'not-attempted', fallbackMode: 'mock-only', allowRealProvider: false })
    expect(pipelineDisabled).not.toHaveProperty('normalizedInput')

    const pipelineFallback = await runProviderReadonlyDryRunPipeline({ featureFlag: { enabled: true } })
    expect(pipelineFallback).toMatchObject({ status: 'completed-mock-only', providerOutcome: 'unavailable', fallbackUsed: true, allowRealProvider: false, allowRealAccountRead: false, allowNotificationSend: false, allowTrading: false, allowAiCall: false })
    if (pipelineFallback.status !== 'completed-mock-only') throw new Error('expected completed mock-only')
    expect(pipelineFallback.normalizedInput.source.sourceType).toBe('mock-only')
    expect(pipelineFallback.normalizedInput.source.isRealReadOnly).toBe(false)
  })

  it('keeps normalizer isolated from adapter, ViewModel, page components, and raw provider output fields', () => {
    const normalizerSource = readSource('src/mocks/preview/provider/providerCandidatePayloadNormalizer.ts')
    for (const forbidden of [
      'realDailyReportDryRunAdapter',
      'adaptRealDailyReportDryRunInputToViewModel',
      'DailyReportViewModel',
      'src/pages',
      'src/components',
    ]) {
      expect(normalizerSource).not.toContain(forbidden)
    }

    const normalization = normalizeProviderCandidatePayloadToDryRunInput(MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE)
    const serialized = JSON.stringify(normalization.normalizedInput)
    for (const forbidden of [
      'viewModel',
      'DailyReportViewModel',
      'candidatePayload',
      'rawCandidate',
      'rawResponse',
      'providerResponse',
      'accountId',
      'transaction',
      'endpoint',
      'requestUrl',
      'credential',
      'token',
      'webhook',
      'apiKey',
    ]) {
      expect(serialized).not.toContain(forbidden)
    }
  })
})
