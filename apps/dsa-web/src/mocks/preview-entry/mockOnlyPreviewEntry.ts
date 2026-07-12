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


  const historyReportsPreview = model.historyReportsPreview
  const historyPanel = document.createElement('section')
  historyPanel.className = 'mock-preview-card mock-preview-dashboard-card'
  historyPanel.id = 'mock-history-reports-preview'
  historyPanel.setAttribute('aria-labelledby', 'mock-history-reports-preview-title')
  appendTextElement(historyPanel, 'h3', '历史报告预览', 'mock-preview-dashboard-title').id =
    'mock-history-reports-preview-title'
  appendTextElement(
    historyPanel,
    'p',
    '本区域仅展示静态脱敏 fixture，用于本地页面渲染检查，不读取真实日报文件、数据库、账户、行情或通知记录。',
  )
  appendList(historyPanel, 'ul', historyReportsPreview.selectedReport.tags, 'mock-preview-dashboard-labels')

  const historyMetrics = document.createElement('div')
  historyMetrics.className = 'mock-preview-dashboard-grid'
  for (const metric of historyReportsPreview.summary) {
    appendMetric(historyMetrics, metric.label, metric.value)
  }
  historyPanel.appendChild(historyMetrics)

  const reportsBlock = document.createElement('div')
  reportsBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(reportsBlock, 'h4', '历史报告列表')
  const reportsList = document.createElement('ul')
  reportsList.className = 'mock-preview-portfolio-list'
  for (const report of historyReportsPreview.reports) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${report.reportDateLabel}｜${report.title}｜状态：${report.status}｜市场：${report.marketMood}｜动作：${report.portfolioAction}｜风险：${report.riskLevel}｜发送：${report.deliveryStatus}`,
    )
    appendTextElement(item, 'span', report.note)
    reportsList.appendChild(item)
  }
  reportsBlock.appendChild(reportsList)
  historyPanel.appendChild(reportsBlock)

  const selectedReportBlock = document.createElement('div')
  selectedReportBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(selectedReportBlock, 'h4', '报告详情示例')
  appendTextElement(selectedReportBlock, 'strong', historyReportsPreview.selectedReport.title)
  appendTextElement(selectedReportBlock, 'p', `生成时间：${historyReportsPreview.selectedReport.generatedAtLabel}`)
  appendTextElement(selectedReportBlock, 'p', `一句话摘要：${historyReportsPreview.selectedReport.headline}`)
  for (const section of historyReportsPreview.selectedReport.sections) {
    appendTextElement(selectedReportBlock, 'p', `${section.title}：${section.content}`)
  }
  historyPanel.appendChild(selectedReportBlock)

  const historyWarningBlock = document.createElement('div')
  historyWarningBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(historyWarningBlock, 'h4', '风险提示')
  appendList(historyWarningBlock, 'ul', historyReportsPreview.riskNotes, 'mock-preview-settings-list')
  historyPanel.appendChild(historyWarningBlock)

  const historyActionBlock = document.createElement('div')
  historyActionBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(historyActionBlock, 'h4', '今日观察备注')
  appendList(historyActionBlock, 'ol', historyReportsPreview.actionNotes, 'mock-preview-settings-list')
  historyPanel.appendChild(historyActionBlock)

  container.appendChild(historyPanel)


  const alertsPreview = model.alertsPreview
  const alertsPanel = document.createElement('section')
  alertsPanel.className = 'mock-preview-card mock-preview-dashboard-card'
  alertsPanel.id = 'mock-alerts-preview'
  alertsPanel.setAttribute('aria-labelledby', 'mock-alerts-preview-title')
  appendTextElement(alertsPanel, 'h3', '提醒预览', 'mock-preview-dashboard-title').id = 'mock-alerts-preview-title'
  appendTextElement(
    alertsPanel,
    'p',
    `本区域仅展示静态脱敏 fixture，用于本地页面渲染检查，不读取真实通知配置，不连接真实 provider，不发送任何通知。`,
  )
  appendList(alertsPanel, 'ul', alertsPreview.labels, 'mock-preview-dashboard-labels')

  const alertsMetrics = document.createElement('div')
  alertsMetrics.className = 'mock-preview-dashboard-grid'
  for (const metric of alertsPreview.summary) {
    appendMetric(alertsMetrics, metric.label, metric.value)
  }
  alertsPanel.appendChild(alertsMetrics)

  const rulesBlock = document.createElement('div')
  rulesBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(rulesBlock, 'h4', '提醒规则列表')
  const rulesList = document.createElement('ul')
  rulesList.className = 'mock-preview-portfolio-list'
  for (const rule of alertsPreview.rules) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${rule.name}｜范围：${rule.scope}｜条件：${rule.condition}｜级别：${rule.severity}｜状态：${rule.status}`,
    )
    appendTextElement(item, 'span', rule.note)
    rulesList.appendChild(item)
  }
  rulesBlock.appendChild(rulesList)
  alertsPanel.appendChild(rulesBlock)

  const triggersBlock = document.createElement('div')
  triggersBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(triggersBlock, 'h4', '触发记录')
  const triggersList = document.createElement('ul')
  triggersList.className = 'mock-preview-portfolio-list'
  for (const trigger of alertsPreview.triggers) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${trigger.triggeredAtLabel}｜${trigger.ruleName}｜状态：${trigger.status}｜结果：${trigger.decision}`,
    )
    appendTextElement(item, 'span', `${trigger.observedValue}｜${trigger.note}`)
    triggersList.appendChild(item)
  }
  triggersBlock.appendChild(triggersList)
  alertsPanel.appendChild(triggersBlock)

  const deliveriesBlock = document.createElement('div')
  deliveriesBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(deliveriesBlock, 'h4', '发送状态')
  const deliveriesList = document.createElement('ul')
  deliveriesList.className = 'mock-preview-portfolio-list'
  for (const delivery of alertsPreview.deliveries) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${delivery.channel}｜状态：${delivery.status}｜目标：${delivery.targetLabel}｜时间：${delivery.sentAtLabel}`,
    )
    appendTextElement(item, 'span', delivery.message)
    deliveriesList.appendChild(item)
  }
  deliveriesBlock.appendChild(deliveriesList)
  alertsPanel.appendChild(deliveriesBlock)

  const alertsWarningBlock = document.createElement('div')
  alertsWarningBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(alertsWarningBlock, 'h4', '风险提示')
  appendList(alertsWarningBlock, 'ul', alertsPreview.riskNotes, 'mock-preview-settings-list')
  alertsPanel.appendChild(alertsWarningBlock)

  const alertsActionBlock = document.createElement('div')
  alertsActionBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(alertsActionBlock, 'h4', '今日观察备注')
  appendList(alertsActionBlock, 'ol', alertsPreview.actionNotes, 'mock-preview-settings-list')
  alertsPanel.appendChild(alertsActionBlock)

  container.appendChild(alertsPanel)

  const agentChatPreview = model.agentChatPreview
  const agentPanel = document.createElement('section')
  agentPanel.className = 'mock-preview-card mock-preview-dashboard-card'
  agentPanel.id = 'mock-agent-chat-preview'
  agentPanel.setAttribute('aria-labelledby', 'mock-agent-chat-preview-title')
  appendTextElement(agentPanel, 'h3', 'Agent 对话预览', 'mock-preview-dashboard-title').id = 'mock-agent-chat-preview-title'
  appendTextElement(
    agentPanel,
    'p',
    '本区域仅展示静态脱敏 fixture，用于本地页面渲染检查，不连接真实 AI、真实 Agent、真实 provider、真实模型或真实账户。',
  )
  appendList(agentPanel, 'ul', agentChatPreview.labels, 'mock-preview-dashboard-labels')

  const agentMetrics = document.createElement('div')
  agentMetrics.className = 'mock-preview-dashboard-grid'
  for (const metric of agentChatPreview.summary) {
    appendMetric(agentMetrics, metric.label, metric.value)
  }
  agentPanel.appendChild(agentMetrics)

  const sessionsBlock = document.createElement('div')
  sessionsBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(sessionsBlock, 'h4', '会话列表')
  const sessionsList = document.createElement('ul')
  sessionsList.className = 'mock-preview-portfolio-list'
  for (const session of agentChatPreview.sessions) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${session.sessionLabel}｜主题：${session.topic}｜状态：${session.status}｜模式：${session.mode}`,
    )
    appendTextElement(item, 'span', `${session.startedAtLabel}｜${session.note}`)
    sessionsList.appendChild(item)
  }
  sessionsBlock.appendChild(sessionsList)
  agentPanel.appendChild(sessionsBlock)

  const messagesBlock = document.createElement('div')
  messagesBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(messagesBlock, 'h4', '消息示例')
  const messagesList = document.createElement('ul')
  messagesList.className = 'mock-preview-portfolio-list'
  for (const message of agentChatPreview.messages) {
    const item = document.createElement('li')
    appendTextElement(item, 'strong', `${message.role}：${message.content}`)
    appendTextElement(item, 'span', `${message.timestampLabel}｜${message.status}｜${message.note}`)
    messagesList.appendChild(item)
  }
  messagesBlock.appendChild(messagesList)
  agentPanel.appendChild(messagesBlock)

  const chunksBlock = document.createElement('div')
  chunksBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(chunksBlock, 'h4', '流式片段示例')
  const chunksList = document.createElement('ol')
  chunksList.className = 'mock-preview-portfolio-list'
  for (const chunk of agentChatPreview.streamChunks) {
    const item = document.createElement('li')
    appendTextElement(item, 'strong', `chunk ${chunk.order}：${chunk.content}`)
    appendTextElement(item, 'span', `${chunk.type}｜${chunk.status}｜${chunk.note}`)
    chunksList.appendChild(item)
  }
  chunksBlock.appendChild(chunksList)
  agentPanel.appendChild(chunksBlock)

  const errorsBlock = document.createElement('div')
  errorsBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(errorsBlock, 'h4', '错误示例')
  const errorsList = document.createElement('ul')
  errorsList.className = 'mock-preview-portfolio-list'
  for (const errorExample of agentChatPreview.errorExamples) {
    const item = document.createElement('li')
    appendTextElement(item, 'strong', `${errorExample.title}：${errorExample.message}`)
    appendTextElement(item, 'span', `${errorExample.status}｜${errorExample.recoveryHint}`)
    errorsList.appendChild(item)
  }
  errorsBlock.appendChild(errorsList)
  agentPanel.appendChild(errorsBlock)

  const agentWarningBlock = document.createElement('div')
  agentWarningBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(agentWarningBlock, 'h4', '风险提示')
  appendList(agentWarningBlock, 'ul', agentChatPreview.riskNotes, 'mock-preview-settings-list')
  agentPanel.appendChild(agentWarningBlock)

  const agentActionBlock = document.createElement('div')
  agentActionBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(agentActionBlock, 'h4', '今日观察备注')
  appendList(agentActionBlock, 'ol', agentChatPreview.actionNotes, 'mock-preview-settings-list')
  agentPanel.appendChild(agentActionBlock)

  container.appendChild(agentPanel)


  const emptyErrorStatesPreview = model.emptyErrorStatesPreview
  const emptyErrorPanel = document.createElement('section')
  emptyErrorPanel.className = 'mock-preview-card mock-preview-dashboard-card'
  emptyErrorPanel.id = 'mock-empty-error-states-preview'
  emptyErrorPanel.setAttribute('aria-labelledby', 'mock-empty-error-states-preview-title')
  appendTextElement(emptyErrorPanel, 'h3', '空状态与错误示例', 'mock-preview-dashboard-title').id = 'mock-empty-error-states-preview-title'
  appendTextElement(
    emptyErrorPanel,
    'p',
    '本区域仅展示静态脱敏 fixture，用于本地页面渲染检查，不读取真实文件、真实配置、真实账户、真实 provider、真实通知或真实 AI。',
  )
  appendList(emptyErrorPanel, 'ul', emptyErrorStatesPreview.labels, 'mock-preview-dashboard-labels')

  const emptyErrorMetrics = document.createElement('div')
  emptyErrorMetrics.className = 'mock-preview-dashboard-grid'
  for (const metric of emptyErrorStatesPreview.summary) {
    appendMetric(emptyErrorMetrics, metric.label, metric.value)
  }
  emptyErrorPanel.appendChild(emptyErrorMetrics)

  const emptyStatesBlock = document.createElement('div')
  emptyStatesBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(emptyStatesBlock, 'h4', '空状态示例')
  const emptyStatesList = document.createElement('ul')
  emptyStatesList.className = 'mock-preview-portfolio-list'
  for (const emptyState of emptyErrorStatesPreview.emptyStates) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${emptyState.title}｜模块：${emptyState.module}｜状态：${emptyState.status}｜说明：${emptyState.message}`,
    )
    appendTextElement(item, 'span', emptyState.recoveryHint)
    emptyStatesList.appendChild(item)
  }
  emptyStatesBlock.appendChild(emptyStatesList)
  emptyErrorPanel.appendChild(emptyStatesBlock)

  const errorStatesBlock = document.createElement('div')
  errorStatesBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(errorStatesBlock, 'h4', '错误示例')
  const errorStatesList = document.createElement('ul')
  errorStatesList.className = 'mock-preview-portfolio-list'
  for (const errorState of emptyErrorStatesPreview.errorStates) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${errorState.title}｜模块：${errorState.module}｜级别：${errorState.severity}｜说明：${errorState.message}`,
    )
    appendTextElement(item, 'span', `${errorState.safeBoundary}｜${errorState.recoveryHint}`)
    errorStatesList.appendChild(item)
  }
  errorStatesBlock.appendChild(errorStatesList)
  emptyErrorPanel.appendChild(errorStatesBlock)

  const degradedStatesBlock = document.createElement('div')
  degradedStatesBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(degradedStatesBlock, 'h4', '降级状态示例')
  const degradedStatesList = document.createElement('ul')
  degradedStatesList.className = 'mock-preview-portfolio-list'
  for (const degradedState of emptyErrorStatesPreview.degradedStates) {
    const item = document.createElement('li')
    appendTextElement(
      item,
      'strong',
      `${degradedState.title}｜模块：${degradedState.module}｜状态：${degradedState.status}｜说明：${degradedState.message}`,
    )
    appendTextElement(item, 'span', degradedState.note)
    degradedStatesList.appendChild(item)
  }
  degradedStatesBlock.appendChild(degradedStatesList)
  emptyErrorPanel.appendChild(degradedStatesBlock)

  const emptyErrorWarningBlock = document.createElement('div')
  emptyErrorWarningBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(emptyErrorWarningBlock, 'h4', '风险提示')
  appendList(emptyErrorWarningBlock, 'ul', emptyErrorStatesPreview.riskNotes, 'mock-preview-settings-list')
  emptyErrorPanel.appendChild(emptyErrorWarningBlock)

  const emptyErrorActionBlock = document.createElement('div')
  emptyErrorActionBlock.className = 'mock-preview-dashboard-block'
  appendTextElement(emptyErrorActionBlock, 'h4', '观察备注')
  appendList(emptyErrorActionBlock, 'ol', emptyErrorStatesPreview.actionNotes, 'mock-preview-settings-list')
  emptyErrorPanel.appendChild(emptyErrorActionBlock)

  container.appendChild(emptyErrorPanel)


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
