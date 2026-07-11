import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import {
  assertMockOnlyMode,
  assertNoRealNetworkTarget,
  inspectMockOnlyRequestTarget,
  isMockOnlyModeEnabled,
} from '../../../src/mocks/safety/mockOnlySafety'

const safetySourcePath = 'src/mocks/safety/mockOnlySafety.ts'
const safetySource = readFileSync(safetySourcePath, 'utf-8')
const appEntrySource = readFileSync('src/main.tsx', 'utf-8')
const appSource = readFileSync('src/App.tsx', 'utf-8')

const runtimeSearchRoots = ['src/api', 'src/pages', 'src/stores', 'src/components', 'src/contexts', 'src/utils']

describe('mock-only safety switch', () => {
  it('keeps mock-only mode disabled by default and for non-mock values', () => {
    for (const mode of [undefined, null, '', false, true, 'false', 'production', 'preview', 'dev', 'local']) {
      expect(isMockOnlyModeEnabled(mode)).toBe(false)
    }
  })

  it('only enables mock-only mode for explicit mock values', () => {
    for (const mode of ['mock', ' mock ', 'mock-only', 'mock_only']) {
      expect(isMockOnlyModeEnabled(mode)).toBe(true)
    }
  })

  it('throws when mock-only access is requested without explicit mock mode', () => {
    expect(() => assertMockOnlyMode(undefined)).toThrow(/explicit mock-only mode/i)
    expect(() => assertMockOnlyMode('production')).toThrow(/explicit mock-only mode/i)
  })

  it('allows mock-only access when explicit mock mode is provided', () => {
    expect(() => assertMockOnlyMode('mock')).not.toThrow()
  })
})

describe('mock-only target inspection', () => {
  it('blocks runtime API paths', () => {
    expect(inspectMockOnlyRequestTarget('/api/v1/example')).toMatchObject({
      allowed: false,
      matchedMarker: '/api/v1',
    })
  })

  it('blocks http and https targets', () => {
    expect(inspectMockOnlyRequestTarget('http://example.invalid')).toMatchObject({ allowed: false, matchedMarker: 'http://' })
    expect(inspectMockOnlyRequestTarget('https://example.invalid')).toMatchObject({ allowed: false, matchedMarker: 'https://' })
  })

  it('blocks loopback and wildcard host markers used only as blocklist test markers', () => {
    expect(inspectMockOnlyRequestTarget('127.0.0.1:8000')).toMatchObject({
      allowed: false,
      matchedMarker: '127.0.0.1',
    })
    expect(inspectMockOnlyRequestTarget('localhost:8000')).toMatchObject({ allowed: false, matchedMarker: 'localhost' })
    expect(inspectMockOnlyRequestTarget('0.0.0.0:8000')).toMatchObject({ allowed: false, matchedMarker: '0.0.0.0' })
  })

  it('blocks provider-like and backend-like targets', () => {
    expect(inspectMockOnlyRequestTarget('quote-provider-a')).toMatchObject({ allowed: false, matchedMarker: 'provider' })
    expect(inspectMockOnlyRequestTarget('real-backend-api')).toMatchObject({ allowed: false, matchedMarker: 'backend' })
  })

  it('allows local fixture names and mock module markers only', () => {
    expect(inspectMockOnlyRequestTarget('dashboard')).toMatchObject({
      allowed: true,
      reason: 'allowed_local_fixture_or_module_name',
    })
    expect(inspectMockOnlyRequestTarget('dashboard.json')).toMatchObject({
      allowed: true,
      reason: 'allowed_local_fixture_or_module_name',
    })
    expect(inspectMockOnlyRequestTarget('mock:dashboard')).toMatchObject({
      allowed: true,
      matchedMarker: 'mock:',
    })
    expect(inspectMockOnlyRequestTarget('local_preview_only')).toMatchObject({
      allowed: true,
      matchedMarker: 'local_preview_only',
    })
    expect(() => assertNoRealNetworkTarget('fixture:dashboard')).not.toThrow()
  })

  it('throws when a real network target is asserted as safe', () => {
    expect(() => assertNoRealNetworkTarget('/api/v1/example')).toThrow(/blocks target/i)
  })
})

describe('mock-only safety scaffold remains non-runtime', () => {
  it('does not contain request, environment, or secret access primitives', () => {
    expect(safetySource).not.toMatch(/\bfetch\b/)
    expect(safetySource).not.toMatch(/\baxios\b/)
    expect(safetySource).not.toContain('XMLHttpRequest')
    expect(safetySource).not.toContain('import.meta.env')
    expect(safetySource).not.toMatch(/from ['"].*src\/api/)
    expect(safetySource).not.toMatch(/from ['"](?:\.\.\/)*api\//)
    expect(safetySource).not.toMatch(/token|api[_-]?key/i)
  })

  it('is not imported by App entry points', () => {
    expect(appEntrySource).not.toContain('src/mocks/safety')
    expect(appEntrySource).not.toContain('./mocks/safety')
    expect(appSource).not.toContain('src/mocks/safety')
    expect(appSource).not.toContain('./mocks/safety')
  })

  it('keeps adapter and safety scaffolds out of runtime api, pages, stores, components, contexts, and utils', async () => {
    const { readdirSync, statSync } = await import('node:fs')
    const { join } = await import('node:path')
    const sourceFiles: string[] = []

    const collectFiles = (directory: string) => {
      for (const entry of readdirSync(directory)) {
        const fullPath = join(directory, entry)
        if (statSync(fullPath).isDirectory()) {
          collectFiles(fullPath)
        } else if (/\.(ts|tsx)$/.test(entry)) {
          sourceFiles.push(fullPath)
        }
      }
    }

    for (const root of runtimeSearchRoots) {
      collectFiles(root)
    }

    for (const filePath of sourceFiles) {
      const source = readFileSync(filePath, 'utf-8')
      expect(source, filePath).not.toContain('src/mocks/adapter')
      expect(source, filePath).not.toContain('../mocks/adapter')
      expect(source, filePath).not.toContain('./mocks/adapter')
      expect(source, filePath).not.toContain('src/mocks/safety')
      expect(source, filePath).not.toContain('../mocks/safety')
      expect(source, filePath).not.toContain('./mocks/safety')
    }
  })
})
