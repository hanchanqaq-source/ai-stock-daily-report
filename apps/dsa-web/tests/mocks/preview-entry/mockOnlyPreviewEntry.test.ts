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
      '不读取环境配置文件',
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
      '不读取环境配置文件',
      '不连接真实 API',
      '不启动后端',
      '不发送通知',
      'Web-P20 设置与导入导出（模拟）',
      '不执行配置读取、文件导入、备份导出或任何写入。',
      '不读取文件或剪贴板',
      '不生成备份，不导出环境配置或密钥类配置',
      '模拟模块预览范围',
      '仪表盘摘要预览',
      '持仓预览',
      '历史报告预览',
      '提醒预览',
      'Agent 对话预览',
      '空状态与错误示例',
      'AI股票基金每日信息报告',
      '模拟账户',
      '模拟持仓总额',
      '模拟目标仓位',
      '模拟仓位比例',
      '进入预览',
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

  it('exposes history reports preview labels through the static preview model', () => {
    const model = createMockOnlyPreviewModel({ mode: 'mock', source: 'local_preview_only' })
    const visibleText = [
      ...model.sections.map((section) => `${section.title}:${section.status}`),
      ...model.historyReportsPreview.summary.map((item) => `${item.label}:${item.value}`),
      ...model.historyReportsPreview.reports.map((item) => `${item.reportDateLabel}:${item.title}:${item.status}`),
      model.historyReportsPreview.selectedReport.title,
      model.historyReportsPreview.selectedReport.headline,
      ...model.alertsPreview.summary.map((item) => `${item.label}:${item.value}`),
      ...model.alertsPreview.labels,
      ...model.agentChatPreview.summary.map((item) => `${item.label}:${item.value}`),
      ...model.agentChatPreview.labels,
      ...model.emptyErrorStatesPreview.summary.map((item) => `${item.label}:${item.value}`),
      ...model.emptyErrorStatesPreview.labels,
      ...model.historyReportsPreview.selectedReport.tags,
    ].join('\n')

    for (const requiredText of [
      '历史报告预览',
      '提醒预览',
      '模拟报告数量',
      '最新模拟报告',
      'AI股票基金每日信息报告',
      'REDACTED FIXTURE DATA',
      '非真实日报',
      '非真实账户',
      '非投资建议',
      '不会发送通知',
      '不会交易',
      '提醒预览',
      '模拟提醒规则数量',
      '模拟触发记录',
      '模拟发送状态',
      '非真实通知',
      '不读取 webhook',
      '不读取 token',
      'Agent 对话预览',
      '模拟会话数量',
      '模拟消息数量',
      '模拟流式片段',
      '非真实 Agent',
      '非真实 AI',
      '不会调用模型',
      '不读取 API key',
      '不读取 .env',
      '空状态与错误示例',
      '非真实错误',
    ]) {
      expect(visibleText).toContain(requiredText)
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
      /\bFileReader\b/,
      /\bnavigator\.clipboard\b/,
      /\blocalStorage\b/,
      /\bsessionStorage\b/,
      /\bindexedDB\b/,
      /\bNotification\s*\(/,
      /\bserviceWorker\b/,
      /\bsendBeacon\b/,
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


  it('renders Web-P28 page overview and module completion status from the preview model', () => {
    const source = readSource(entryPath)
    const model = createMockOnlyPreviewModel({ mode: 'mock', source: 'local_preview_only' })
    const businessSectionIds = new Set([
      'dashboard-summary',
      'portfolio-preview',
      'history-reports-preview',
      'alerts-preview',
      'agent-chat-preview',
      'empty-error-examples',
    ])
    const businessSections = model.sections.filter((section) => businessSectionIds.has(section.id))
    const previewableSections = businessSections.filter((section) => section.status === '可预览')
    const pendingSections = businessSections.filter((section) => section.status === '后续建设')

    for (const requiredText of [
      '页面总览',
      'mock-only 模块完成度',
      '当前模式',
      '项目名称',
      '页面显示名称',
      '可预览模块数量',
      '后续建设模块数量',
      '总模块数量',
      '完成度',
      '数据来源',
      '网络状态',
      '通知状态',
      '交易状态',
      'Agent 状态',
      '安全边界',
      'AI股票基金每日信息报告',
    ]) {
      expect(source).toContain(requiredText)
    }

    const overviewVisibleText = [
      model.overview.modeLabel,
      model.overview.projectName,
      model.overview.pageDisplayName,
      model.overview.dataSource,
      model.overview.networkStatus,
      model.overview.notificationStatus,
      model.overview.tradingStatus,
      model.overview.agentStatus,
      model.overview.safetyBoundary,
      ...model.overview.safetyStatus.map((item) => `${item.label}:${item.value}`),
    ].join('\n')

    for (const requiredText of [
      '运行范围',
      '真实网络',
      '真实账户',
      '真实通知',
      '真实交易',
      '模型调用',
      'mock-only 本地预览',
      '股票基金质量分析系统',
      'REDACTED FIXTURE DATA',
      '未连接真实服务',
      '不会发送通知',
      '不会交易',
      '不会调用模型',
      '127.0.0.1 only',
    ]) {
      expect(overviewVisibleText).toContain(requiredText)
    }

    expect(model.overview.safetyBoundary).toBe('127.0.0.1 only')
    expect(model.overview.usageDescription).toContain('本页面仅用于 Windows 本地 mock-only 渲染检查')
    expect(model.overview.previewableModuleCount).toBe(previewableSections.length)
    expect(model.overview.pendingModuleCount).toBe(pendingSections.length)
    expect(model.overview.totalModuleCount).toBe(businessSections.length)
  })

  it('keeps preview entry fixture text redacted from precise holding values and real account detail labels', () => {
    const source = `${readSource(entryPath)}
${JSON.stringify(createMockOnlyPreviewModel({ mode: 'mock', source: 'local_preview_only' }))}`

    for (const forbiddenExactValue of [
      ['¥59', '167.78'].join(','),
      ['¥180', '000.00'].join(','),
      ['32', '9%'].join('.'),
      ['¥14', '879.70'].join(','),
      ['+18', '33%'].join('.'),
      ['¥6', '877.54'].join(','),
      ['-0', '46%'].join('.'),
      ['¥2', '115.71'].join(','),
      ['-4', '01%'].join('.'),
      ['¥2', '292.78'].join(','),
      ['-1', '61%'].join('.'),
    ]) {
      expect(source).not.toContain(forbiddenExactValue)
    }

    expect(source).toContain('REDACTED FIXTURE DATA')
    expect(source).toContain('模拟数据')
    for (const forbiddenAccountDetail of ['真实基金代码', '真实账户明细', '真实交易记录']) {
      expect(source).not.toContain(forbiddenAccountDetail)
    }
  })


  it('renders Web-P27 quick navigation anchors and section return links without external targets', () => {
    const source = readSource(entryPath)

    for (const requiredText of [
      '页面快速导航',
      '本地预览导航',
      '返回顶部',
      '返回模块列表',
      '安全边界确认',
      '设置与导入导出',
      '仪表盘摘要',
      '持仓预览',
      '历史报告预览',
      '提醒预览',
      'Agent 对话预览',
      '空状态与错误示例',
      '本页仅为 mock-only 本地预览',
      '所有跳转均为同页锚点',
      '不会打开外部链接',
      '不会连接真实服务',
    ]) {
      expect(source).toContain(requiredText)
    }

    for (const requiredAnchor of [
      'mock-preview-top',
      'mock-preview-modules',
      'mock-safety-boundary',
      'mock-settings-import-export',
      'mock-dashboard-summary-preview',
      'mock-portfolio-preview',
      'mock-history-reports-preview',
      'mock-alerts-preview',
      'mock-agent-chat-preview',
      'mock-empty-error-states-preview',
    ]) {
      expect(source).toContain(requiredAnchor)
    }

    expect(source).toContain('link.href = href')
    for (const samePageHref of [
      '#mock-preview-top',
      '#mock-preview-modules',
      '`#${item.anchor}`',
      '`#${section.previewAnchor}`',
    ]) {
      expect(source).toContain(samePageHref)
    }
    expect(source).not.toContain('target="_blank"')
    expect(source).not.toMatch(/https?:\/\//)
  })

  it('adds return links to every major mock-only preview section', () => {
    const source = readSource(entryPath)
    for (const panelName of [
      'safetyPanel',
      'settingsPanel',
      'dashboardPanel',
      'portfolioPanel',
      'historyPanel',
      'alertsPanel',
      'agentPanel',
      'emptyErrorPanel',
    ]) {
      expect(source).toContain(`appendSectionReturnLinks(${panelName})`)
    }
  })

  it('renders the dashboard entry in the module range before the dashboard content', () => {
    const source = readSource(entryPath)
    const moduleRangeIndex = source.indexOf('模拟模块预览范围')
    const dashboardEntryIndex = source.indexOf('进入预览')
    const dashboardContentIndex = source.indexOf('仪表盘摘要预览')

    expect(moduleRangeIndex).toBeGreaterThanOrEqual(0)
    expect(dashboardEntryIndex).toBeGreaterThan(moduleRangeIndex)
    expect(dashboardContentIndex).toBeGreaterThan(dashboardEntryIndex)
    expect(source).toContain("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
  })

  it('renders the portfolio entry in the module range before the portfolio content', () => {
    const source = readSource(entryPath)
    const moduleRangeIndex = source.indexOf('模拟模块预览范围')
    const portfolioEntryIndex = source.indexOf("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
    const portfolioContentIndex = source.indexOf("portfolioPanel.id = 'mock-portfolio-preview'")

    expect(moduleRangeIndex).toBeGreaterThanOrEqual(0)
    expect(portfolioEntryIndex).toBeGreaterThan(moduleRangeIndex)
    expect(portfolioContentIndex).toBeGreaterThan(portfolioEntryIndex)
    expect(source).toContain("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
  })

  it('renders the history reports entry in the module range before the history reports content', () => {
    const source = readSource(entryPath)
    const moduleRangeIndex = source.indexOf('模拟模块预览范围')
    const historyEntryIndex = source.indexOf("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
    const historyContentIndex = source.indexOf("historyPanel.id = 'mock-history-reports-preview'")

    expect(moduleRangeIndex).toBeGreaterThanOrEqual(0)
    expect(historyEntryIndex).toBeGreaterThan(moduleRangeIndex)
    expect(historyContentIndex).toBeGreaterThan(historyEntryIndex)
    expect(source).toContain("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
  })


  it('renders the alerts entry in the module range before the alerts content', () => {
    const source = readSource(entryPath)
    const moduleRangeIndex = source.indexOf('模拟模块预览范围')
    const alertsEntryIndex = source.indexOf("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
    const alertsContentIndex = source.indexOf("alertsPanel.id = 'mock-alerts-preview'")

    expect(moduleRangeIndex).toBeGreaterThanOrEqual(0)
    expect(alertsEntryIndex).toBeGreaterThan(moduleRangeIndex)
    expect(alertsContentIndex).toBeGreaterThan(alertsEntryIndex)
    expect(source).toContain("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
  })

  it('renders the agent chat entry in the module range before the agent chat content', () => {
    const source = readSource(entryPath)
    const moduleRangeIndex = source.indexOf('模拟模块预览范围')
    const agentEntryIndex = source.indexOf("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
    const agentContentIndex = source.indexOf("agentPanel.id = 'mock-agent-chat-preview'")

    expect(moduleRangeIndex).toBeGreaterThanOrEqual(0)
    expect(agentEntryIndex).toBeGreaterThan(moduleRangeIndex)
    expect(agentContentIndex).toBeGreaterThan(agentEntryIndex)
    expect(source).toContain("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
  })


  it('renders the empty and error states entry in the module range before the empty and error states content', () => {
    const source = readSource(entryPath)
    const moduleRangeIndex = source.indexOf('模拟模块预览范围')
    const emptyErrorEntryIndex = source.indexOf("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
    const emptyErrorContentIndex = source.indexOf("emptyErrorPanel.id = 'mock-empty-error-states-preview'")

    expect(moduleRangeIndex).toBeGreaterThanOrEqual(0)
    expect(emptyErrorEntryIndex).toBeGreaterThan(moduleRangeIndex)
    expect(emptyErrorContentIndex).toBeGreaterThan(emptyErrorEntryIndex)
    expect(source).toContain("appendAnchorLink(item, '进入预览', `#${section.previewAnchor}`)")
  })

  it('marks dashboard summary, portfolio preview, history reports preview, alerts preview, agent chat preview, and empty/error states preview as previewable and keeps unfinished modules pending', () => {
    const model = createMockOnlyPreviewModel({ mode: 'mock', source: 'local_preview_only' })
    const dashboard = model.sections.find((section) => section.id === 'dashboard-summary')
    const portfolio = model.sections.find((section) => section.id === 'portfolio-preview')
    const history = model.sections.find((section) => section.id === 'history-reports-preview')
    const alerts = model.sections.find((section) => section.id === 'alerts-preview')
    const agent = model.sections.find((section) => section.id === 'agent-chat-preview')
    const emptyErrors = model.sections.find((section) => section.id === 'empty-error-examples')
    const unfinishedSections = model.sections.filter(
      (section) =>
        section.id !== 'dashboard-summary' &&
        section.id !== 'portfolio-preview' &&
        section.id !== 'history-reports-preview' &&
        section.id !== 'alerts-preview' &&
        section.id !== 'agent-chat-preview' &&
        section.id !== 'empty-error-examples',
    )

    expect(dashboard).toMatchObject({ title: '仪表盘摘要', status: '可预览', previewAnchor: 'mock-dashboard-summary-preview' })
    expect(portfolio).toMatchObject({ title: '持仓预览', status: '可预览', previewAnchor: 'mock-portfolio-preview' })
    expect(history).toMatchObject({ title: '历史报告预览', status: '可预览', previewAnchor: 'mock-history-reports-preview' })
    expect(alerts).toMatchObject({ title: '提醒预览', status: '可预览', previewAnchor: 'mock-alerts-preview' })
    expect(agent).toMatchObject({ title: 'Agent 对话预览', status: '可预览', previewAnchor: 'mock-agent-chat-preview' })
    expect(emptyErrors).toMatchObject({ title: '空状态与错误示例', status: '可预览', previewAnchor: 'mock-empty-error-states-preview' })
    expect(unfinishedSections.length).toBeGreaterThan(0)
    for (const section of unfinishedSections) {
      expect(section.status).toBe('后续建设')
      expect(section.status).not.toBe('可预览')
    }
  })

  it('keeps Web-P29 responsive CSS for tablet and mobile mock-only preview layouts', () => {
    const source = readSource(indexPath)

    for (const requiredText of [
      'AI股票基金每日信息报告',
      '股票基金质量分析系统',
      '页面总览',
      'mock-only 模块完成度',
      '页面快速导航',
      '返回顶部',
      '返回模块列表',
      '安全边界确认',
      '设置与导入导出',
      '仪表盘摘要',
      '持仓预览',
      '历史报告预览',
      '提醒预览',
      'Agent 对话预览',
      '空状态与错误示例',
    ]) {
      expect(`${source}\n${readSource(entryPath)}`).toContain(requiredText)
    }

    for (const requiredCss of [
      '@media (max-width: 900px)',
      '@media (max-width: 640px)',
      '@media (max-width: 420px)',
      'grid-template-columns: 1fr',
      'flex-wrap: wrap',
      'overflow-wrap: anywhere',
      'word-break: break-word',
      'min-width: 0',
      'min-height: 44px',
    ]) {
      expect(source).toContain(requiredCss)
    }
  })

  it('keeps the rendered preview page source free of forbidden runtime endpoints and network primitives', () => {
    const source = `${readSource(indexPath)}\n${readSource(entryPath)}`

    for (const forbidden of [
      '0.0.0.0',
      'target="_blank"',
      'fetch(',
      'axios',
      'XMLHttpRequest',
      'WebSocket',
      'EventSource',
      'localStorage',
      'sessionStorage',
      'indexedDB',
      'Notification(',
      'serviceWorker',
      'sendBeacon',
      'FileReader',
      'input type="file"',
      'openai',
      'deepseek',
      'zhipu',
      'LangChain',
      '/api/v1',
      'VITE_API_URL',
    ]) {
      expect(source).not.toContain(forbidden)
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
    expect(model.sections).toEqual(
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
})
