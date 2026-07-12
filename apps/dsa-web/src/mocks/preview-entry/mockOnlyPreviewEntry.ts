import { createMockOnlyPreviewModel } from '../preview/mockOnlyPreviewModel'

const ROOT_ID = 'mock-only-preview-root'
const PREVIEW_OPTIONS = {
  mode: 'mock',
  source: 'local_preview_only',
} as const

const SAFETY_NOTES = Object.freeze([
  '仅供模拟',
  '仅限本地预览',
  '不读取 .env',
  '不连接真实 API',
  '不启动后端',
  '不发送通知',
])

const SETTINGS_IMPORT_EXPORT_NOTES = Object.freeze([
  '设置状态：mock-only 固定，不保存本地配置',
  '导入状态：仅展示人工复核流程，不读取文件或剪贴板',
  '导出状态：不生成备份，不导出 .env、Token、API Key 或 Webhook',
])

export interface MockOnlyPreviewEntryRenderResult {
  readonly safetyBannerCount: number
  readonly safetyNoteCount: number
  readonly sectionCount: number
}

const appendTextElement = (parent: HTMLElement, tagName: string, text: string, className?: string): HTMLElement => {
  const element = document.createElement(tagName)
  element.textContent = text
  if (className) element.className = className
  parent.appendChild(element)
  return element
}

const appendList = (parent: HTMLElement, tagName: 'ul' | 'ol', items: readonly string[], className: string): HTMLElement => {
  const list = document.createElement(tagName)
  list.className = className
  for (const item of items) {
    appendTextElement(list, 'li', item)
  }
  parent.appendChild(list)
  return list
}

export const renderMockOnlyPreviewEntry = (root: HTMLElement): MockOnlyPreviewEntryRenderResult => {
  const model = createMockOnlyPreviewModel(PREVIEW_OPTIONS)

  const container = document.createElement('section')
  container.className = 'mock-preview-shell'
  container.setAttribute('aria-labelledby', 'mock-only-preview-entry-title')

  const hero = document.createElement('div')
  hero.className = 'mock-preview-hero'
  appendTextElement(hero, 'p', 'Windows localhost-only safe preview', 'mock-preview-eyebrow')
  appendTextElement(hero, 'h2', 'AI股票基金每日信息报告', 'mock-preview-title').id = 'mock-only-preview-entry-title'
  appendTextElement(hero, 'p', '股票基金质量分析系统 mock-only 本地安全预览', 'mock-preview-subtitle')
  container.appendChild(hero)

  const safetyPanel = document.createElement('section')
  safetyPanel.className = 'mock-preview-card mock-preview-safety-card'
  appendTextElement(safetyPanel, 'h3', '安全边界确认')
  appendTextElement(safetyPanel, 'p', '此页面只渲染脱敏 fixture 与静态 mock 模型，用于本机安全预览体验检查。')
  appendList(safetyPanel, 'ul', SAFETY_NOTES, 'mock-preview-badge-list')
  appendList(safetyPanel, 'ul', model.safetyBanner, 'mock-preview-safety-list')
  container.appendChild(safetyPanel)

  const metadataPanel = document.createElement('section')
  metadataPanel.className = 'mock-preview-card'
  appendTextElement(metadataPanel, 'h3', '预览元数据')
  appendList(
    metadataPanel,
    'ul',
    [
      `mode: ${model.metadata.mode}`,
      `source: ${model.metadata.source}`,
      `containsRealData: ${String(model.metadata.containsRealData)}`,
      `containsSecrets: ${String(model.metadata.containsSecrets)}`,
      `safeForWindowsPreview: ${String(model.metadata.safeForWindowsPreview)}`,
    ],
    'mock-preview-metadata-list',
  )
  container.appendChild(metadataPanel)

  const settingsPanel = document.createElement('section')
  settingsPanel.className = 'mock-preview-card mock-preview-settings-card'
  appendTextElement(settingsPanel, 'h3', 'Web-P20 设置与导入导出（模拟）')
  appendTextElement(settingsPanel, 'p', '本区只说明本地操作边界，不执行配置读取、文件导入、备份导出或任何写入。')
  appendList(settingsPanel, 'ul', SETTINGS_IMPORT_EXPORT_NOTES, 'mock-preview-settings-list')
  container.appendChild(settingsPanel)

  const sectionsPanel = document.createElement('section')
  sectionsPanel.className = 'mock-preview-card'
  appendTextElement(sectionsPanel, 'h3', 'Mock 模块预览范围')
  const sectionList = document.createElement('ol')
  sectionList.className = 'mock-preview-section-list'
  for (const section of model.sections) {
    const item = document.createElement('li')
    appendTextElement(item, 'strong', section.title)
    appendTextElement(item, 'span', section.description)
    sectionList.appendChild(item)
  }
  sectionsPanel.appendChild(sectionList)
  container.appendChild(sectionsPanel)

  root.appendChild(container)

  return {
    safetyBannerCount: model.safetyBanner.length,
    safetyNoteCount: SAFETY_NOTES.length,
    sectionCount: model.sections.length,
  }
}

const root = document.getElementById(ROOT_ID)

if (!root) {
  throw new Error(`Mock-only preview root element #${ROOT_ID} was not found.`)
}

renderMockOnlyPreviewEntry(root)
