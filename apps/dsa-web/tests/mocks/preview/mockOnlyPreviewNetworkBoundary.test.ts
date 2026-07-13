import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMockOnlyPreviewModel } from '../../../src/mocks/preview/mockOnlyPreviewModel'

const mockOptions = { mode: 'mock', source: 'local_preview_only' } as const

const boundarySourcePaths = [
  'src/mocks/preview/mockOnlyPreviewModel.ts',
  'src/mocks/preview/mockOnlyPreviewTypes.ts',
  'src/mocks/preview/dry-run/realDailyReportDryRunTypes.ts',
  'src/mocks/preview/dry-run/realDailyReportDryRunValidator.ts',
  'src/mocks/preview/dry-run/realDailyReportDryRunAdapter.ts',
  'src/mocks/preview/adapters/dailyReportAdapter.ts',
  'src/mocks/preview/adapters/index.ts',
  'src/mocks/preview/fixtures/dailyReportFixture.ts',
  'src/mocks/preview/fixtures/index.ts',
  'src/mocks/preview/guards/dailyReportViewModelGuard.ts',
  'src/mocks/preview/guards/index.ts',
  'src/mocks/service/mockApiClient.ts',
  'src/mocks/service/mockApiService.ts',
  'src/mocks/service/mockApiServiceTypes.ts',
  'src/mocks/adapter/mockApiAdapter.ts',
  'src/mocks/adapter/mockApiTypes.ts',
  'src/mocks/safety/mockOnlySafety.ts',
  'src/mocks/safety/mockOnlySafetyTypes.ts',
] as const

const previewServiceAdapterPaths = boundarySourcePaths.filter((sourcePath) => !sourcePath.includes('/safety/'))
const previewServicePaths = boundarySourcePaths.filter(
  (sourcePath) => sourcePath.includes('/preview/') || sourcePath.includes('/service/'),
)
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

const forbiddenNetworkPrimitives = [
  /\bfetch\b/,
  /\baxios\b/,
  /\bXMLHttpRequest\b/,
  /\bEventSource\b/,
  /\bWebSocket\b/,
  /\bimport\.meta\.env\b/,
  /\bwindow\.location\b/,
  /\blocalStorage\b/,
  /\bsessionStorage\b/,
  /\bindexedDB\b/,
  /\bNotification\s*\(/,
  /\bserviceWorker\b/,
  /\bsendBeacon\b/,
  /\bFileReader\b/,
  /\bOpenAI\b/,
  /\bDeepSeek\b/,
  /\bLangChain\b/,
] as const

const forbiddenRequestTargets = [
  'http://',
  'https://',
  '/api/v1',
  '127.0.0.1',
  'localhost',
  '0.0.0.0',
] as const

const forbiddenRuntimeImports = [
  /from ['"].*src\/api(?:\/|['"])/,
  /from ['"](?:\.\.\/)*api\//,
  /from ['"].*\/pages(?:\/|['"])/,
  /from ['"](?:\.\.\/)*pages\//,
  /from ['"].*\/stores(?:\/|['"])/,
  /from ['"](?:\.\.\/)*stores\//,
  /from ['"].*\/components(?:\/|['"])/,
  /from ['"](?:\.\.\/)*components\//,
  /from ['"].*\/contexts(?:\/|['"])/,
  /from ['"](?:\.\.\/)*contexts\//,
  /from ['"].*\/utils(?:\/|['"])/,
  /from ['"](?:\.\.\/)*utils\//,
] as const

const forbiddenRuntimeMockImports = [
  'src/mocks/preview',
  'src/mocks/service',
  '../mocks/preview',
  '../mocks/service',
  './mocks/preview',
  './mocks/service',
] as const

const readSource = (sourcePath: string): string => readFileSync(sourcePath, 'utf-8')

const collectTypeScriptFiles = (path: string): string[] => {
  if (!existsSync(path)) return []
  if (statSync(path).isFile()) return path.endsWith('.ts') || path.endsWith('.tsx') ? [path] : []

  const sourceFiles: string[] = []
  for (const entry of readdirSync(path)) {
    const fullPath = join(path, entry)
    if (statSync(fullPath).isDirectory()) sourceFiles.push(...collectTypeScriptFiles(fullPath))
    else if (entry.endsWith('.ts') || entry.endsWith('.tsx')) sourceFiles.push(fullPath)
  }
  return sourceFiles
}

describe('mock-only preview network boundary', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('keeps preview, service, adapter, and safety sources free of network primitives and browser storage', () => {
    for (const sourcePath of boundarySourcePaths) {
      const source = readSource(sourcePath)
      for (const forbiddenPattern of forbiddenNetworkPrimitives) {
        expect(source, `${sourcePath} must not contain ${forbiddenPattern}`).not.toMatch(forbiddenPattern)
      }
    }
  })

  it('keeps preview, service, and adapter sources free of requestable URLs and API paths', () => {
    for (const sourcePath of previewServiceAdapterPaths) {
      const source = readSource(sourcePath)
      for (const forbiddenTarget of forbiddenRequestTargets) {
        expect(source, `${sourcePath} must not contain ${forbiddenTarget}`).not.toContain(forbiddenTarget)
      }
    }
  })

  it('allows safety blocklist markers only inside the safety implementation', () => {
    const safetySource = readSource('src/mocks/safety/mockOnlySafety.ts')
    for (const blockedMarker of forbiddenRequestTargets) {
      expect(safetySource, `safety blocklist should document ${blockedMarker}`).toContain(blockedMarker)
    }
    for (const sourcePath of previewServiceAdapterPaths) {
      const source = readSource(sourcePath)
      for (const blockedMarker of forbiddenRequestTargets) {
        expect(source, `${sourcePath} must not reuse safety marker ${blockedMarker} as a target`).not.toContain(
          blockedMarker,
        )
      }
    }
  })

  it('keeps preview, service, and adapter isolated from real runtime modules', () => {
    for (const sourcePath of previewServiceAdapterPaths) {
      const source = readSource(sourcePath)
      for (const forbiddenImport of forbiddenRuntimeImports) {
        expect(source, `${sourcePath} must not import ${forbiddenImport}`).not.toMatch(forbiddenImport)
      }
    }
  })

  it('keeps preview model dependent on mock service and the daily report adapter only', () => {
    const previewSource = readSource('src/mocks/preview/mockOnlyPreviewModel.ts')
    expect(previewSource).toContain('../service/mockApiService')
    expect(previewSource).toContain('./adapters')
    expect(previewSource).not.toContain('../safety/')
  })

  it('keeps real runtime entries and directories from importing mock preview or service modules', () => {
    const runtimeFiles = runtimeSearchRoots.flatMap((root) => collectTypeScriptFiles(root))
    for (const sourcePath of runtimeFiles) {
      const source = readSource(sourcePath)
      for (const forbiddenImport of forbiddenRuntimeMockImports) {
        expect(source, `${sourcePath} must not import ${forbiddenImport}`).not.toContain(forbiddenImport)
      }
    }
  })

  it('creates the preview model without touching global network functions or constructors', () => {
    const fetchSpy = vi.fn(() => {
      throw new Error('fetch must not be called by mock-only preview')
    })
    const xhrSpy = vi.fn(() => {
      throw new Error('XMLHttpRequest must not be constructed by mock-only preview')
    })
    const webSocketSpy = vi.fn(() => {
      throw new Error('WebSocket must not be constructed by mock-only preview')
    })
    const eventSourceSpy = vi.fn(() => {
      throw new Error('EventSource must not be constructed by mock-only preview')
    })

    vi.stubGlobal('fetch', fetchSpy)
    vi.stubGlobal('XMLHttpRequest', xhrSpy)
    vi.stubGlobal('WebSocket', webSocketSpy)
    vi.stubGlobal('EventSource', eventSourceSpy)

    const model = createMockOnlyPreviewModel(mockOptions)
    expect(model.metadata).toEqual({
      mode: 'mock',
      source: 'local_preview_only',
      containsRealData: false,
      containsSecrets: false,
      safeForWindowsPreview: true,
    })
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(xhrSpy).not.toHaveBeenCalled()
    expect(webSocketSpy).not.toHaveBeenCalled()
    expect(eventSourceSpy).not.toHaveBeenCalled()
  })

  it('rejects non-mock modes before exposing fixture-backed preview data', () => {
    expect(() => createMockOnlyPreviewModel({ mode: 'production', source: 'local_preview_only' } as never)).toThrow(
      /mode=mock/i,
    )
    expect(() => createMockOnlyPreviewModel({ mode: 'preview', source: 'local_preview_only' } as never)).toThrow(
      /mode=mock/i,
    )
    expect(() => createMockOnlyPreviewModel({ source: 'local_preview_only' } as never)).toThrow(/mode=mock/i)
  })

  it('derives preview metadata from safe mock fixture metadata', () => {
    const model = createMockOnlyPreviewModel(mockOptions)
    expect(model.metadata.mode).toBe('mock')
    expect(model.metadata.source).toBe('local_preview_only')
    expect(model.metadata.containsRealData).toBe(false)
    expect(model.metadata.containsSecrets).toBe(false)
    expect(model.metadata.safeForWindowsPreview).toBe(true)
  })


  it('keeps the dry-run adapter free of provider names and secret marker text', () => {
    const source = readSource('src/mocks/preview/dry-run/realDailyReportDryRunAdapter.ts')
    const adapterForbiddenFragments = ['智谱', 'webhook', 'token', 'API key', '0.0.0.0', 'http://', 'https://'] as const

    for (const forbiddenFragment of adapterForbiddenFragments) {
      expect(source, `dry-run adapter must not contain ${forbiddenFragment}`).not.toContain(forbiddenFragment)
    }
  })

  it('keeps the dry-run schema type draft locked to safe literal switches', () => {
    const source = readSource('src/mocks/preview/dry-run/realDailyReportDryRunTypes.ts')
    const requiredFragments = [
      'RealDailyReportDryRunInput',
      "mode: 'dry-run'",
      'dryRun: true',
      "projectName: '股票基金质量分析系统'",
      "reportDisplayName: 'AI股票基金每日信息报告'",
      'allowNotificationSend: false',
      'allowTrading: false',
      'allowAiCall: false',
      'requiresHumanApproval: true',
      'canFallbackToMockOnly: true',
    ] as const

    for (const requiredFragment of requiredFragments) {
      expect(source).toContain(requiredFragment)
    }
  })

  it('documents the complete static boundary scan set', () => {
    expect(previewServicePaths).toEqual([
      'src/mocks/preview/mockOnlyPreviewModel.ts',
      'src/mocks/preview/mockOnlyPreviewTypes.ts',
      'src/mocks/preview/dry-run/realDailyReportDryRunTypes.ts',
      'src/mocks/preview/dry-run/realDailyReportDryRunValidator.ts',
      'src/mocks/preview/dry-run/realDailyReportDryRunAdapter.ts',
      'src/mocks/preview/adapters/dailyReportAdapter.ts',
      'src/mocks/preview/adapters/index.ts',
      'src/mocks/preview/fixtures/dailyReportFixture.ts',
      'src/mocks/preview/fixtures/index.ts',
      'src/mocks/preview/guards/dailyReportViewModelGuard.ts',
      'src/mocks/preview/guards/index.ts',
      'src/mocks/service/mockApiClient.ts',
      'src/mocks/service/mockApiService.ts',
      'src/mocks/service/mockApiServiceTypes.ts',
    ])
    for (const sourcePath of boundarySourcePaths) {
      expect(existsSync(sourcePath), `${sourcePath} must exist`).toBe(true)
    }
  })
})
