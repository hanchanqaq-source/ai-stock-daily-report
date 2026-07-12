import { createMockOnlyPreviewModel } from '../preview/mockOnlyPreviewModel'

const ROOT_ID = 'mock-only-preview-root'
const PREVIEW_OPTIONS = {
  mode: 'mock',
  source: 'local_preview_only',
} as const

const SAFETY_NOTES = Object.freeze([
  '仅供模拟',
  '仅限本地预览',
  '不读取环境配置文件',
  '不连接真实 API',
  '不启动后端',
  '不发送通知',
])

const SETTINGS_IMPORT_EXPORT_NOTES = Object.freeze([
  '设置状态：mock-only 固定，不保存本地配置',
  '导入状态：仅展示人工复核流程，不读取文件或剪贴板',
  '导出状态：不生成备份，不导出环境配置或密钥类配置',
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

const appendMetric = (parent: HTMLElement, label: string, value: string): void => {
  const metric = document.createElement('div')
  metric.className = 'mock-preview-dashboard-metric'
  appendTextElement(metric, 'span', label)
  appendTextElement(metric, 'strong', value)
  parent.appendChild(metric)
}

const ratioToWidth = (ratio: string): string => {
  const parsedRatio = Number.parseFloat(ratio)
  if (!Number.isFinite(parsedRatio)) return '0%'
  return `${Math.max(0, Math.min(100, parsedRatio))}%`
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
  appendTextElement(sectionsPanel, 'h3', '模拟模块预览范围')
  const sectionList = document.createElement('ol')
  sectionList.className = 'mock-preview-section-list'
  for (const section of model.sections) {
    const item = document.createElement('li')
    appendTextElement(item, 'strong', section.title)
    appendTextElement(
      item,
      'span',
      section.status,
      section.status === '可预览' ? 'mock-preview-section-status' : 'mock-preview-section-status is-pending',
    )
    appendTextElement(item, 'span', section.description)
    if (section.previewAnchor) {
      const previewLink = document.createElement('a')
      previewLink.className = 'mock-preview-link'
      previewLink.href = `#${section.previewAnchor}`
      previewLink.textContent = '进入预览'
      item.appendChild(previewLink)
    }
    sectionList.appendChild(item)
  }
  sectionsPanel.appendChild(sectionList)
  container.appendChild(sectionsPanel)

  const dashboardPreview = model.dashboardSummaryPreview
  const dashboardPanel = document.createElement('section')
  dashboardPanel.className = 'mock-preview-card mock-preview-dashboard-card'
  dashboardPanel.id = 'mock-dashboard-summary-preview'
  dashboardPanel.setAttribute('aria-labelledby', 'mock-dashboard-summary-preview-title')
  appendTextElement(dashboardPanel, 'h3', '仪表盘摘要预览', 'mock-preview-dashboard-title').id =
    'mock-dashboard-summary-preview-title'
  appendTextElement(dashboardPanel, 'p', `今日一句话摘要：${dashboardPreview.headline}`)
  appendList(dashboardPanel, 'ul', dashboardPreview.labels, 'mock-preview-dashboard-labels')

  const metricsGrid = document.createElement('div')
  metricsGrid.className = 'mock-preview-dashboard-grid'
  appendMetric(metricsGrid, '市场状态', dashboardPreview.marketStatus)
  appendMetric(metricsGrid, '模拟持仓总额', dashboardPreview.totalHoldingAmount)
  appendMetric(metricsGrid, '模拟当日涨跌', dashboardPreview.dailyChange)
  appendMetric(metricsGrid, '模拟仓位比例', dashboardPreview.positionRatio)
  appendMetric(metricsGrid, '风险等级', dashboardPreview.riskLevel)
  dashboardPanel.appendChild(metricsGrid)

  const structureBlock = document.createElement('div')
  structureBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(structureBlock, 'h4', '持仓结构')
  for (const holding of dashboardPreview.holdingStructure) {
    appendTextElement(structureBlock, 'p', `${holding.name}：${holding.ratio}`)
    const progress = document.createElement('div')
    progress.className = 'mock-preview-dashboard-progress'
    const bar = document.createElement('span')
    bar.style.width = ratioToWidth(holding.ratio)
    progress.appendChild(bar)
    structureBlock.appendChild(progress)
  }
  dashboardPanel.appendChild(structureBlock)

  const warningBlock = document.createElement('div')
  warningBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(warningBlock, 'h4', '风险提示')
  appendList(warningBlock, 'ul', dashboardPreview.riskWarnings, 'mock-preview-settings-list')
  dashboardPanel.appendChild(warningBlock)

  const actionBlock = document.createElement('div')
  actionBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(actionBlock, 'h4', '今日动作建议示例')
  appendList(actionBlock, 'ol', dashboardPreview.actionSuggestions, 'mock-preview-settings-list')
  dashboardPanel.appendChild(actionBlock)

  container.appendChild(dashboardPanel)

  const portfolioPreview = model.portfolioPreview
  const portfolioPanel = document.createElement('section')
  portfolioPanel.className = 'mock-preview-card mock-preview-dashboard-card'
  portfolioPanel.id = 'mock-portfolio-preview'
  portfolioPanel.setAttribute('aria-labelledby', 'mock-portfolio-preview-title')
  appendTextElement(portfolioPanel, 'h3', '持仓预览', 'mock-preview-dashboard-title').id =
    'mock-portfolio-preview-title'
  appendTextElement(
    portfolioPanel,
    'p',
    '本区域仅展示静态脱敏 fixture，用于本地页面渲染检查，不读取真实账户、真实基金、真实行情或真实交易记录。',
  )
  appendList(portfolioPanel, 'ul', portfolioPreview.labels, 'mock-preview-dashboard-labels')

  const portfolioMetrics = document.createElement('div')
  portfolioMetrics.className = 'mock-preview-dashboard-grid'
  appendMetric(portfolioMetrics, '模拟账户', portfolioPreview.accountLabel)
  appendMetric(portfolioMetrics, '模拟持仓总额', portfolioPreview.totalAmountLabel)
  appendMetric(portfolioMetrics, '模拟目标仓位', portfolioPreview.targetAmountLabel)
  appendMetric(portfolioMetrics, '模拟仓位比例', portfolioPreview.positionRatioLabel)
  portfolioPanel.appendChild(portfolioMetrics)

  const holdingsBlock = document.createElement('div')
  holdingsBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(holdingsBlock, 'h4', '持仓列表')
  const holdingList = document.createElement('ul')
  holdingList.className = 'mock-preview-portfolio-list'
  for (const holding of portfolioPreview.holdings) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${holding.name}：${holding.amountLabel}，占比 ${holding.weightLabel}，模拟浮动 ${holding.pnlLabel}，风险 ${holding.riskLevel}`,
    )
    appendTextElement(item, 'span', `${holding.category}｜${holding.note}`)
    holdingList.appendChild(item)
  }
  holdingsBlock.appendChild(holdingList)
  portfolioPanel.appendChild(holdingsBlock)

  const portfolioWarningBlock = document.createElement('div')
  portfolioWarningBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(portfolioWarningBlock, 'h4', '风险提示')
  appendList(portfolioWarningBlock, 'ul', portfolioPreview.riskNotes, 'mock-preview-settings-list')
  portfolioPanel.appendChild(portfolioWarningBlock)

  const portfolioActionBlock = document.createElement('div')
  portfolioActionBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(portfolioActionBlock, 'h4', '今日观察备注')
  appendList(portfolioActionBlock, 'ol', portfolioPreview.actionNotes, 'mock-preview-settings-list')
  portfolioPanel.appendChild(portfolioActionBlock)

  container.appendChild(portfolioPanel)

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
