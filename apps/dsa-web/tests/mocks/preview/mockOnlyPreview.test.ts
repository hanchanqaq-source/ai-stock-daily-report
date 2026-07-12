import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  createMockOnlyPreviewModel,
  getMockOnlyPreviewSections,
  getMockOnlyPreviewSummary,
} from '../../../src/mocks/preview/mockOnlyPreviewModel'
import type { MockOnlyPreviewOptions } from '../../../src/mocks/preview/mockOnlyPreviewTypes'

const previewSourcePaths = [
  'src/mocks/preview/mockOnlyPreviewTypes.ts',
  'src/mocks/preview/mockOnlyPreviewModel.ts',
]
const previewSource = previewSourcePaths.map((sourcePath) => readFileSync(sourcePath, 'utf-8')).join('\n')
const mockOptions: MockOnlyPreviewOptions = { mode: 'mock', source: 'local_preview_only' }
const runtimeSearchRoots = ['src/api', 'src/pages', 'src/stores', 'src/components', 'src/contexts', 'src/utils']

const collectTypeScriptFiles = (directory: string): string[] => {
  const sourceFiles: string[] = []

  for (const entry of readdirSync(directory)) {
    const fullPath = join(directory, entry)
    if (statSync(fullPath).isDirectory()) {
      sourceFiles.push(...collectTypeScriptFiles(fullPath))
    } else if (entry.endsWith('.ts') || entry.endsWith('.tsx')) {
      sourceFiles.push(fullPath)
    }
  }

  return sourceFiles
}

const forbiddenSecretPattern = new RegExp(['tok', 'en|web', 'hook|api[_-]?key'].join(''), 'i')

describe('mock-only preview model', () => {
  it('does not allow preview model creation outside mock mode', () => {
    expect(() => createMockOnlyPreviewModel({ mode: 'production', source: 'local_preview_only' } as never)).toThrow(
      /mode=mock/i,
    )
    expect(() => getMockOnlyPreviewSummary({ mode: 'preview', source: 'local_preview_only' } as never)).toThrow(
      /mode=mock/i,
    )
  })

  it('creates the preview model when mode is mock and source is local preview only', () => {
    expect(createMockOnlyPreviewModel(mockOptions)).toMatchObject({
      metadata: {
        mode: 'mock',
        source: 'local_preview_only',
        containsRealData: false,
        containsSecrets: false,
        safeForWindowsPreview: true,
      },
    })
  })

  it('returns a visible safety banner', () => {
    expect(createMockOnlyPreviewModel(mockOptions).safetyBanner).toEqual([
      'MOCK ONLY',
      'LOCAL PREVIEW ONLY',
      'REDACTED FIXTURE DATA',
      'NO REAL NETWORK',
      'NO REAL ACCOUNT',
      'NO OUTBOUND DELIVERY',
    ])
  })

  it('returns all mock-only preview sections including Web-P20 settings import/export', () => {
    expect(getMockOnlyPreviewSections(mockOptions).map((section) => section.id)).toEqual([
      'safety-banner',
      'dashboard-summary',
      'portfolio-preview',
      'history-reports-preview',
      'alerts-preview',
      'agent-chat-preview',
      'empty-error-examples',
      'local-settings-import-export',
    ])
  })

  it('keeps the Web-P20 settings import/export section static and non-executing', () => {
    expect(getMockOnlyPreviewSections(mockOptions)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: 'local-settings-import-export',
          data: expect.objectContaining({
            settingsMode: 'mock_only_locked',
            importMode: 'review_only',
            exportMode: 'not_generated',
          }),
        }),
      ]),
    )
  })

  it('derives preview metadata from mock fixture metadata', () => {
    expect(getMockOnlyPreviewSummary(mockOptions)).toEqual({
      mode: 'mock',
      source: 'local_preview_only',
      containsRealData: false,
      containsSecrets: false,
      safeForWindowsPreview: true,
    })
  })
})

describe('mock-only preview safety boundary', () => {
  it('does not contain request, environment, endpoint, or credential primitives', () => {
    expect(previewSource).not.toMatch(/\bfetch\b/)
    expect(previewSource).not.toMatch(/\baxios\b/)
    expect(previewSource).not.toContain('XMLHttpRequest')
    expect(previewSource).not.toMatch(/https?:\/\//)
    expect(previewSource).not.toContain(['127', '0', '0', '1'].join('.'))
    expect(previewSource).not.toContain(['local', 'host'].join(''))
    expect(previewSource).not.toContain(['0', '0', '0', '0'].join('.'))
    expect(previewSource).not.toContain('import.meta.env')
    expect(previewSource).not.toMatch(/from ['"].*src\/api/)
    expect(previewSource).not.toMatch(/from ['"](?:\.\.\/)*api\//)
    expect(previewSource).not.toMatch(forbiddenSecretPattern)
  })

  it('uses only the mock service and preview-local type imports', () => {
    expect(previewSource).toContain('../service/mockApiService')
    expect(previewSource).not.toContain('../adapter/')
    expect(previewSource).not.toContain('../safety/')
  })

  it('does not keep a TSX page draft in the preview source scaffold', () => {
    expect(previewSourcePaths).not.toContain(['src/mocks/preview/', 'MockOnly', 'Preview', 'Page.tsx'].join(''))
  })

  it('is not imported by App entry points, runtime directories, or routes', () => {
    const appEntrySource = readFileSync('src/main.tsx', 'utf-8')
    const appSource = readFileSync('src/App.tsx', 'utf-8')

    expect(appEntrySource).not.toContain('src/mocks/preview')
    expect(appEntrySource).not.toContain('./mocks/preview')
    expect(appSource).not.toContain('src/mocks/preview')
    expect(appSource).not.toContain('./mocks/preview')

    const sourceFiles = runtimeSearchRoots.flatMap((root) => collectTypeScriptFiles(root))
    for (const filePath of sourceFiles) {
      const source = readFileSync(filePath, 'utf-8')
      expect(source, filePath).not.toContain('src/mocks/preview')
      expect(source, filePath).not.toContain('../mocks/preview')
      expect(source, filePath).not.toContain('./mocks/preview')
    }
  })
})
