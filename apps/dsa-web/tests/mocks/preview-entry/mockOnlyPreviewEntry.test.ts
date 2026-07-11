import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { createMockOnlyPreviewModel } from '../../../src/mocks/preview/mockOnlyPreviewModel'

const indexPath = 'mock-only-preview/index.html'
const entryPath = 'src/mocks/preview-entry/mockOnlyPreviewEntry.ts'
const mainPath = 'src/main.tsx'
const appPath = 'src/App.tsx'

const runtimeRoots = ['src/api', 'src/pages', 'src/stores', 'src/components', 'src/contexts', 'src/utils'] as const

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

describe('mock-only preview independent web entry', () => {
  it('keeps the independent index present and visibly marked as mock-only', () => {
    expect(existsSync(indexPath)).toBe(true)
    const source = readSource(indexPath)

    for (const label of [
      'AI股票基金每日信息报告',
      '股票基金质量分析系统 mock-only 本地安全预览',
      '仅供模拟',
      '仅限本地预览',
      '不读取 .env',
      '不连接真实 API',
      '不启动后端',
      '不发送通知',
    ]) {
      expect(source).toContain(label)
    }
  })

  it('keeps the independent index pointed only at the preview entry', () => {
    const source = readSource(indexPath)

    expect(source).toContain('/src/mocks/preview-entry/mockOnlyPreviewEntry.ts')
    expect(source).not.toContain('/src/main.tsx')
    expect(source).not.toContain('App.tsx')

    for (const forbidden of ['cdn', 'http://', 'https://', '/api/v1', 'VITE_API_URL']) {
      expect(source).not.toContain(forbidden)
    }

    for (const forbiddenPattern of [
      /\bfetch\b/,
      /\bXMLHttpRequest\b/,
      /\bWebSocket\b/,
      /\blocalStorage\b/,
      /\bsessionStorage\b/,
      /\binnerHTML\b/,
    ]) {
      expect(source).not.toMatch(forbiddenPattern)
    }
  })

  it('keeps the TypeScript entry present, readable, and limited to the preview model import', () => {
    expect(existsSync(entryPath)).toBe(true)
    const source = readSource(entryPath)
    const importLines = source.split('\n').filter((line) => line.trim().startsWith('import '))

    expect(importLines).toEqual(["import { createMockOnlyPreviewModel } from '../preview/mockOnlyPreviewModel'"])
    for (const requiredText of [
      'AI股票基金每日信息报告',
      '股票基金质量分析系统 mock-only 本地安全预览',
      '仅供模拟',
      '仅限本地预览',
      '不读取 .env',
      '不连接真实 API',
      '不启动后端',
      '不发送通知',
      'createElement',
      'textContent',
      'appendChild',
    ]) {
      expect(source).toContain(requiredText)
    }
    for (const forbiddenImport of ['src/api', '/api/', '/pages', '/stores', '/components', '/contexts', '/utils', 'App', 'main', 'router']) {
      expect(source).not.toContain(forbiddenImport)
    }
  })

  it('keeps the TypeScript entry free of network, environment, storage, and unsafe DOM primitives', () => {
    const source = readSource(entryPath)

    for (const forbiddenPattern of [
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
      /\binnerHTML\b/,
      /\bdangerouslySetInnerHTML\b/,
      /\beval\b/,
      /\bnew Function\b/,
    ]) {
      expect(source).not.toMatch(forbiddenPattern)
    }

    for (const forbiddenTarget of ['http://', 'https://', '/api/v1', 'VITE_API_URL']) {
      expect(source).not.toContain(forbiddenTarget)
    }
  })

  it('keeps real runtime entry files from importing preview-entry', () => {
    for (const sourcePath of [mainPath, appPath]) {
      expect(readSource(sourcePath)).not.toContain('preview-entry')
    }
  })

  it('keeps real runtime directories from importing preview-entry', () => {
    const sourceFiles = runtimeRoots.flatMap((root) => collectTypeScriptFiles(root))

    for (const sourcePath of sourceFiles) {
      expect(readSource(sourcePath), `${sourcePath} must not import preview-entry`).not.toContain('preview-entry')
    }
  })

  it('keeps preview model guarded by mock local preview options', () => {
    expect(() => createMockOnlyPreviewModel({ mode: 'production', source: 'local_preview_only' } as never)).toThrow(
      /mode=mock and source=local_preview_only/i,
    )
    expect(() => createMockOnlyPreviewModel({ mode: 'mock', source: 'remote_preview' } as never)).toThrow(
      /mode=mock and source=local_preview_only/i,
    )

    const model = createMockOnlyPreviewModel({ mode: 'mock', source: 'local_preview_only' })
    expect(model.metadata).toMatchObject({ mode: 'mock', source: 'local_preview_only' })
  })
})
