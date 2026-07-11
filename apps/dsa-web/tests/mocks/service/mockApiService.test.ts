import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { createMockApiClient } from '../../../src/mocks/service/mockApiClient'
import {
  assertMockServiceReady,
  createMockApiService,
  getMockModule,
  getMockScenario,
  listMockModules,
} from '../../../src/mocks/service/mockApiService'
import type { MockApiServiceOptions } from '../../../src/mocks/service/mockApiServiceTypes'

const serviceSourcePaths = [
  'src/mocks/service/mockApiClient.ts',
  'src/mocks/service/mockApiService.ts',
  'src/mocks/service/mockApiServiceTypes.ts',
]
const serviceSource = serviceSourcePaths.map((sourcePath) => readFileSync(sourcePath, 'utf-8')).join('\n')
const mockOptions: MockApiServiceOptions = { mode: 'mock', source: 'local_preview_only' }
const runtimeSearchRoots = ['src/api', 'src/pages', 'src/stores', 'src/components', 'src/contexts', 'src/utils']

const collectTypeScriptFiles = (directory: string): string[] => {
  const sourceFiles: string[] = []

  for (const entry of readdirSync(directory)) {
    const fullPath = join(directory, entry)
    if (statSync(fullPath).isDirectory()) {
      sourceFiles.push(...collectTypeScriptFiles(fullPath))
    } else if (/\.(ts|tsx)$/.test(entry)) {
      sourceFiles.push(fullPath)
    }
  }

  return sourceFiles
}

describe('mockApiService non-runtime scaffold', () => {
  it('blocks mock reads without an explicit mock mode', () => {
    expect(() => assertMockServiceReady({ mode: undefined, source: 'local_preview_only' })).toThrow(/explicit mock-only mode/i)
    expect(() => listMockModules({ mode: 'production', source: 'local_preview_only' })).toThrow(/explicit mock-only mode/i)
    expect(() => createMockApiService({ mode: 'preview', source: 'local_preview_only' })).toThrow(/explicit mock-only mode/i)
  })

  it('reads mock modules only when mode is mock', () => {
    const service = createMockApiService(mockOptions)
    const client = createMockApiClient(mockOptions)

    expect(service.assertReady()).toEqual({ ready: true, source: 'local_preview_only' })
    expect(client.assertReady()).toEqual({ ready: true, source: 'local_preview_only' })
    expect(service.getMockModule('dashboard')).toEqual(client.getMockModule('dashboard'))
  })

  it('lists all fixture modules from the adapter catalog', () => {
    expect(listMockModules(mockOptions)).toEqual([
      'auth',
      'dashboard',
      'analysis',
      'history',
      'portfolio',
      'alerts',
      'systemConfig',
      'agent',
      'alphasift',
      'usage',
      'backtest',
      'decisionSignals',
      'stocksImport',
      'errors',
      'emptyStates',
    ])
  })

  it('returns dashboard fixture data', () => {
    expect(getMockModule(mockOptions, 'dashboard')).toMatchObject({
      metadata: { mode: 'mock', source: 'local_preview_only' },
    })
  })

  it('returns a scenario response wrapper with module, scenario, and fixture', () => {
    const response = getMockScenario(mockOptions, 'dashboard', 'default')

    expect(response).toMatchObject({
      moduleName: 'dashboard',
      scenarioName: 'default',
      fixture: { metadata: { mode: 'mock', source: 'local_preview_only' } },
    })
  })

  it('rejects unknown modules without falling through to a real request path', () => {
    expect(() => getMockModule(mockOptions, 'unknownModule' as never)).toThrow(/unknown mock module/i)
    expect(() => getMockScenario(mockOptions, 'unknownModule' as never, 'default')).toThrow(/unknown mock module/i)
  })
})

describe('mockApiService safety boundary', () => {
  it('does not contain request, environment, endpoint, or secret primitives', () => {
    expect(serviceSource).not.toMatch(/\bfetch\b/)
    expect(serviceSource).not.toMatch(/\baxios\b/)
    expect(serviceSource).not.toContain('XMLHttpRequest')
    expect(serviceSource).not.toMatch(/https?:\/\//)
    expect(serviceSource).not.toContain('127.0.0.1')
    expect(serviceSource).not.toContain('0.0.0.0')
    expect(serviceSource).not.toContain('localhost')
    expect(serviceSource).not.toContain('import.meta.env')
    expect(serviceSource).not.toMatch(/from ['"].*src\/api/)
    expect(serviceSource).not.toMatch(/from ['"](?:\.\.\/)*api\//)
    expect(serviceSource).not.toMatch(/token|webhook|api[_-]?key/i)
  })

  it('is not imported by App entry points or runtime source directories', () => {
    const appEntrySource = readFileSync('src/main.tsx', 'utf-8')
    const appSource = readFileSync('src/App.tsx', 'utf-8')

    expect(appEntrySource).not.toContain('src/mocks/service')
    expect(appEntrySource).not.toContain('./mocks/service')
    expect(appSource).not.toContain('src/mocks/service')
    expect(appSource).not.toContain('./mocks/service')

    const sourceFiles = runtimeSearchRoots.flatMap((root) => collectTypeScriptFiles(root))
    for (const filePath of sourceFiles) {
      const source = readFileSync(filePath, 'utf-8')
      expect(source, filePath).not.toContain('src/mocks/service')
      expect(source, filePath).not.toContain('../mocks/service')
      expect(source, filePath).not.toContain('./mocks/service')
    }
  })
})
