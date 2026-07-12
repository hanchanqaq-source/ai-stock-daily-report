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


  it('uses Chinese module titles with explicit preview statuses', () => {
    expect(getMockOnlyPreviewSections(mockOptions)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'safety-banner', title: '安全边界', status: '后续建设' }),
        expect.objectContaining({ id: 'dashboard-summary', title: '仪表盘摘要', status: '可预览' }),
        expect.objectContaining({ id: 'portfolio-preview', title: '持仓预览', status: '可预览' }),
        expect.objectContaining({ id: 'history-reports-preview', title: '历史报告预览', status: '可预览' }),
        expect.objectContaining({ id: 'alerts-preview', title: '提醒预览', status: '可预览' }),
        expect.objectContaining({ id: 'agent-chat-preview', title: 'Agent 对话预览', status: '可预览' }),
        expect.objectContaining({ id: 'empty-error-examples', title: '空状态与错误示例', status: '可预览' }),
      ]),
    )
  })


  it('derives mock-only overview completion counts from current section statuses', () => {
    const model = createMockOnlyPreviewModel(mockOptions)
    const previewableSections = model.sections.filter((section) => section.status === '可预览')
    const pendingSections = model.sections.filter((section) => section.status === '后续建设')

    expect(model.overview).toMatchObject({
      modeLabel: 'mock-only 本地预览',
      projectName: '股票基金质量分析系统',
      pageDisplayName: 'AI股票基金每日信息报告',
      dataSource: 'REDACTED FIXTURE DATA',
      networkStatus: '未连接真实服务',
      notificationStatus: '不会发送通知',
      tradingStatus: '不会交易',
      agentStatus: '不会调用模型',
      safetyBoundary: '127.0.0.1 only',
    })
    expect(model.overview.previewableModuleCount).toBe(previewableSections.length)
    expect(model.overview.pendingModuleCount).toBe(pendingSections.length)
    expect(model.overview.totalModuleCount).toBe(previewableSections.length + pendingSections.length)
    expect(model.overview.completionPercent).toBe(
      Math.round((previewableSections.length / model.overview.totalModuleCount) * 100),
    )
    expect(model.overview.safetyStatus).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: '运行范围', value: '127.0.0.1 only' }),
        expect.objectContaining({ label: '数据来源', value: '静态脱敏 fixture' }),
        expect.objectContaining({ label: '真实网络', value: '未连接' }),
        expect.objectContaining({ label: '真实账户', value: '未读取' }),
        expect.objectContaining({ label: '真实通知', value: '未发送' }),
        expect.objectContaining({ label: '真实交易', value: '禁用' }),
        expect.objectContaining({ label: '模型调用', value: '未调用' }),
      ]),
    )
  })

  it('exposes static redacted dashboard summary preview fixture data', () => {
    expect(createMockOnlyPreviewModel(mockOptions).dashboardSummaryPreview).toMatchObject({
      headline: '科技方向保持震荡，模拟组合以观察为主，暂不进行主动调仓。',
      marketStatus: '震荡观察',
      totalHoldingAmount: '¥59,167.78',
      dailyChange: '+0.68%',
      positionRatio: '32.9%',
      riskLevel: '中等',
      labels: expect.arrayContaining(['模拟数据', 'REDACTED FIXTURE DATA', '非真实账户', '非投资建议', '不会发送通知']),
    })
  })

  it('exposes static redacted portfolio preview fixture data', () => {
    expect(createMockOnlyPreviewModel(mockOptions).portfolioPreview).toMatchObject({
      accountLabel: '本地预览组合',
      totalAmountLabel: '¥59,167.78',
      targetAmountLabel: '¥180,000.00',
      positionRatioLabel: '32.9%',
      labels: expect.arrayContaining([
        '模拟数据',
        'REDACTED FIXTURE DATA',
        '非真实账户',
        '非投资建议',
        '不会发送通知',
        '不会交易',
      ]),
      holdings: expect.arrayContaining([
        expect.objectContaining({
          name: '硬科技观察仓',
          amountLabel: '¥14,879.70',
          weightLabel: '25.1%',
          pnlLabel: '+18.33%',
          riskLevel: '中高',
        }),
      ]),
      riskNotes: expect.arrayContaining(['本区域只展示静态脱敏 fixture，不读取用户真实持仓。']),
      actionNotes: expect.arrayContaining(['模拟组合保持观察，不执行自动调仓。']),
    })
  })

  it('exposes static redacted history reports preview fixture data', () => {
    expect(createMockOnlyPreviewModel(mockOptions).historyReportsPreview).toMatchObject({
      summary: expect.arrayContaining([
        expect.objectContaining({ label: '模拟报告数量', value: '3' }),
        expect.objectContaining({ label: '最新模拟报告', value: '2026-07-12' }),
        expect.objectContaining({ label: '模拟数据来源', value: 'REDACTED FIXTURE DATA' }),
      ]),
      reports: expect.arrayContaining([
        expect.objectContaining({
          reportDateLabel: '2026-07-12',
          title: 'AI股票基金每日信息报告',
          status: '本地预览',
          marketMood: '震荡观察',
          portfolioAction: '不调仓',
          riskLevel: '中等',
          deliveryStatus: '未发送',
        }),
      ]),
      selectedReport: expect.objectContaining({
        title: 'AI股票基金每日信息报告 mock-only 历史详情',
        headline: '科技方向维持震荡，模拟组合以观察为主，不执行主动调仓。',
        tags: expect.arrayContaining(['模拟数据', 'REDACTED FIXTURE DATA', '非真实日报', '非真实账户', '非投资建议', '不会发送通知', '不会交易']),
      }),
      riskNotes: expect.arrayContaining(['本区域只展示静态脱敏 fixture，不读取真实历史报告。']),
      actionNotes: expect.arrayContaining(['历史报告列表仅用于 mock-only 页面演示。']),
    })
  })


  it('exposes static redacted alerts preview fixture data', () => {
    const model = createMockOnlyPreviewModel(mockOptions)
    const visibleText = [
      ...model.alertsPreview.summary.map((item) => `${item.label}:${item.value}`),
      ...model.alertsPreview.labels,
      ...model.alertsPreview.rules.map((rule) => `${rule.name}:${rule.scope}:${rule.condition}:${rule.severity}:${rule.status}`),
      ...model.alertsPreview.triggers.map((trigger) => `${trigger.triggeredAtLabel}:${trigger.ruleName}:${trigger.status}:${trigger.decision}`),
      ...model.alertsPreview.deliveries.map((delivery) => `${delivery.channel}:${delivery.status}:${delivery.targetLabel}:${delivery.message}`),
      ...model.alertsPreview.riskNotes,
      ...model.alertsPreview.actionNotes,
    ].join('\n')

    for (const requiredText of [
      '模拟提醒规则数量',
      '模拟触发记录',
      '模拟发送状态',
      'REDACTED FIXTURE DATA',
      '非真实通知',
      '非真实账户',
      '非投资建议',
      '不会发送通知',
      '不会交易',
      '不读取 webhook',
      '不读取 token',
      '科技仓位风险观察',
      'mock-only 本地预览通道',
    ]) {
      expect(visibleText).toContain(requiredText)
    }
  })

  it('exposes static redacted agent chat preview fixture data', () => {
    const model = createMockOnlyPreviewModel(mockOptions)
    const visibleText = [
      ...model.agentChatPreview.summary.map((item) => `${item.label}:${item.value}`),
      ...model.agentChatPreview.labels,
      ...model.agentChatPreview.sessions.map((session) => `${session.sessionLabel}:${session.topic}:${session.status}:${session.mode}`),
      ...model.agentChatPreview.messages.map((message) => `${message.role}:${message.content}:${message.status}`),
      ...model.agentChatPreview.streamChunks.map((chunk) => `${chunk.order}:${chunk.content}:${chunk.status}`),
      ...model.agentChatPreview.errorExamples.map((errorExample) => `${errorExample.title}:${errorExample.message}:${errorExample.recoveryHint}`),
      ...model.agentChatPreview.riskNotes,
      ...model.agentChatPreview.actionNotes,
    ].join('\n')

    for (const requiredText of [
      'Agent 对话预览',
      '模拟会话数量',
      '模拟消息数量',
      '模拟流式片段',
      'REDACTED FIXTURE DATA',
      '非真实 Agent',
      '非真实 AI',
      '非真实账户',
      '非投资建议',
      '不会调用模型',
      '不会发送通知',
      '不会交易',
      '不读取 API key',
      '不读取 token',
      '不读取 .env',
      '本地预览会话 A',
      '日报摘要检查',
      '正在生成 mock-only 回复',
      '模拟 provider 未连接',
    ]) {
      expect(visibleText).toContain(requiredText)
    }
  })


  it('exposes static redacted empty and error states preview fixture data', () => {
    const model = createMockOnlyPreviewModel(mockOptions)
    const visibleText = [
      ...model.sections.map((section) => `${section.title}:${section.status}:${section.previewAnchor ?? ''}`),
      ...model.emptyErrorStatesPreview.summary.map((item) => `${item.label}:${item.value}`),
      ...model.emptyErrorStatesPreview.labels,
      ...model.emptyErrorStatesPreview.emptyStates.map((item) => `${item.title}:${item.module}:${item.status}:${item.message}:${item.recoveryHint}`),
      ...model.emptyErrorStatesPreview.errorStates.map((item) => `${item.title}:${item.module}:${item.severity}:${item.message}:${item.safeBoundary}`),
      ...model.emptyErrorStatesPreview.degradedStates.map((item) => `${item.title}:${item.module}:${item.status}:${item.message}:${item.note}`),
      ...model.emptyErrorStatesPreview.riskNotes,
      ...model.emptyErrorStatesPreview.actionNotes,
    ].join('\n')

    for (const requiredText of [
      '空状态与错误示例',
      '可预览',
      'mock-empty-error-states-preview',
      '模拟空状态数量',
      '模拟错误示例数量',
      '模拟降级状态数量',
      'REDACTED FIXTURE DATA',
      '非真实错误',
      '非真实账户',
      '非投资建议',
      '不读取真实文件',
      '不读取数据库',
      '不读取 webhook',
      '不读取 token',
      '不读取 API key',
      '不会调用模型',
      '不会发送通知',
      '不会交易',
      '暂无持仓数据',
      '暂无历史报告',
      '暂无提醒规则',
      '暂无 Agent 会话',
      'mock-only provider 未连接',
      '导入文件格式无效',
      '通知目标未配置',
      '报告生成失败',
      '行情 provider 未启用',
      '通知通道禁用',
      'Agent 流式输出不可用',
      '本功能不是正式错误监控系统。',
      '当前不会上传任何诊断信息。',
    ]) {
      expect(visibleText).toContain(requiredText)
    }
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
