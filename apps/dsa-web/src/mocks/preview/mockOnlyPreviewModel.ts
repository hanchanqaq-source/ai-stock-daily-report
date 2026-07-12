import { createMockApiService } from '../service/mockApiService'
import type {
  MockOnlyDashboardSummaryPreview,
  MockOnlyHistoryReportsPreview,
  MockOnlyPortfolioPreview,
  MockOnlyPreviewMetadata,
  MockOnlyPreviewModel,
  MockOnlyPreviewOptions,
  MockOnlyPreviewSection,
} from './mockOnlyPreviewTypes'

interface FixtureMetadata {
  readonly metadata?: {
    readonly mode?: string
    readonly source?: string
    readonly contains_real_data?: boolean
    readonly contains_secrets?: boolean
    readonly safe_for_windows_preview?: boolean
  }
}

const REQUIRED_OPTIONS: MockOnlyPreviewOptions = {
  mode: 'mock',
  source: 'local_preview_only',
}


const DASHBOARD_SUMMARY_PREVIEW: MockOnlyDashboardSummaryPreview = Object.freeze({
  headline: '科技方向保持震荡，模拟组合以观察为主，暂不进行主动调仓。',
  marketStatus: '震荡观察',
  totalHoldingAmount: '¥59,167.78',
  dailyChange: '+0.68%',
  positionRatio: '32.9%',
  riskLevel: '中等',
  labels: Object.freeze(['模拟数据', 'REDACTED FIXTURE DATA', '非真实账户', '非投资建议', '不会发送通知']),
  holdingStructure: Object.freeze([
    Object.freeze({ name: '硬科技', ratio: '62%' }),
    Object.freeze({ name: '海外科技', ratio: '18%' }),
    Object.freeze({ name: '其他观察仓', ratio: '20%' }),
  ]),
  riskWarnings: Object.freeze([
    '本区域只展示静态脱敏 fixture，不读取用户真实持仓。',
    '本区域不接真实行情、provider、通知或交易能力。',
  ]),
  actionSuggestions: Object.freeze([
    '观察模拟组合波动，不执行自动调仓。',
    '复核风险等级标签，仅作为页面展示示例。',
  ]),
})

const PORTFOLIO_PREVIEW: MockOnlyPortfolioPreview = Object.freeze({
  accountLabel: '本地预览组合',
  totalAmountLabel: '¥59,167.78',
  targetAmountLabel: '¥180,000.00',
  positionRatioLabel: '32.9%',
  labels: Object.freeze(['模拟数据', 'REDACTED FIXTURE DATA', '非真实账户', '非投资建议', '不会发送通知', '不会交易']),
  holdings: Object.freeze([
    Object.freeze({
      name: '硬科技观察仓',
      category: '主题观察',
      amountLabel: '¥14,879.70',
      weightLabel: '25.1%',
      pnlLabel: '+18.33%',
      riskLevel: '中高',
      note: '静态脱敏示例，仅用于持仓行渲染检查。',
    }),
    Object.freeze({
      name: 'AI 硬件观察仓',
      category: '行业观察',
      amountLabel: '¥6,877.54',
      weightLabel: '11.6%',
      pnlLabel: '-0.46%',
      riskLevel: '中',
      note: '静态脱敏示例，不代表真实账户或真实产品。',
    }),
    Object.freeze({
      name: '半导体观察仓',
      category: '行业观察',
      amountLabel: '¥2,115.71',
      weightLabel: '3.6%',
      pnlLabel: '-4.01%',
      riskLevel: '中高',
      note: '静态脱敏示例，风险标签只用于页面展示。',
    }),
    Object.freeze({
      name: '海外科技观察仓',
      category: '跨市场观察',
      amountLabel: '¥2,292.78',
      weightLabel: '3.9%',
      pnlLabel: '-1.61%',
      riskLevel: '中',
      note: '静态脱敏示例，不连接任何真实基金平台。',
    }),
  ]),
  riskNotes: Object.freeze([
    '本区域只展示静态脱敏 fixture，不读取用户真实持仓。',
    '本区域不接真实行情、provider、通知或交易能力。',
    '页面中的金额、比例、盈亏和风险等级仅用于渲染测试。',
  ]),
  actionNotes: Object.freeze([
    '模拟组合保持观察，不执行自动调仓。',
    '风险标签仅用于页面展示，不代表真实投资判断。',
  ]),
})


const HISTORY_REPORTS_PREVIEW: MockOnlyHistoryReportsPreview = Object.freeze({
  summary: Object.freeze([
    Object.freeze({ label: '模拟报告数量', value: '3' }),
    Object.freeze({ label: '最新模拟报告', value: '2026-07-12' }),
    Object.freeze({ label: '模拟发送状态', value: '未发送' }),
    Object.freeze({ label: '模拟数据来源', value: 'REDACTED FIXTURE DATA' }),
  ]),
  reports: Object.freeze([
    Object.freeze({
      reportDateLabel: '2026-07-12',
      title: 'AI股票基金每日信息报告',
      status: '本地预览',
      marketMood: '震荡观察',
      portfolioAction: '不调仓',
      riskLevel: '中等',
      deliveryStatus: '未发送',
      note: '静态脱敏 fixture 示例，不读取真实历史日报文件。',
    }),
    Object.freeze({
      reportDateLabel: '2026-07-11',
      title: 'AI股票基金每日信息报告',
      status: '本地预览',
      marketMood: '分化观察',
      portfolioAction: '仅观察',
      riskLevel: '中等',
      deliveryStatus: '未发送',
      note: '静态脱敏 fixture 示例，不读取数据库或通知记录。',
    }),
    Object.freeze({
      reportDateLabel: '2026-07-10',
      title: 'AI股票基金每日信息报告',
      status: '本地预览',
      marketMood: '偏强观察',
      portfolioAction: '不交易',
      riskLevel: '中高',
      deliveryStatus: '未发送',
      note: '静态脱敏 fixture 示例，不连接任何真实账户。',
    }),
  ]),
  selectedReport: Object.freeze({
    title: 'AI股票基金每日信息报告 mock-only 历史详情',
    generatedAtLabel: '2026-07-12 本地静态预览',
    headline: '科技方向维持震荡，模拟组合以观察为主，不执行主动调仓。',
    sections: Object.freeze([
      Object.freeze({ title: '市场概览', content: '静态脱敏 fixture 示例，不接真实行情。' }),
      Object.freeze({ title: '持仓观察', content: '静态脱敏 fixture 示例，不读取真实账户。' }),
      Object.freeze({ title: '风险提示', content: '页面仅用于渲染检查，不构成投资建议。' }),
      Object.freeze({ title: '动作建议', content: '不发送通知，不执行交易。' }),
    ]),
    tags: Object.freeze(['模拟数据', 'REDACTED FIXTURE DATA', '非真实日报', '非真实账户', '非投资建议', '不会发送通知', '不会交易']),
  }),
  riskNotes: Object.freeze([
    '本区域只展示静态脱敏 fixture，不读取真实历史报告。',
    '本区域不接真实行情、provider、AI、通知或交易能力。',
    '页面中的报告日期、摘要、风险等级和动作建议仅用于渲染测试。',
    '本功能不是正式日报归档功能。',
  ]),
  actionNotes: Object.freeze([
    '历史报告列表仅用于 mock-only 页面演示。',
    '当前不会从本地文件、数据库、云端或通知渠道读取报告。',
  ]),
})

const SAFETY_BANNER = Object.freeze([
  'MOCK ONLY',
  'LOCAL PREVIEW ONLY',
  'REDACTED FIXTURE DATA',
  'NO REAL NETWORK',
  'NO REAL ACCOUNT',
  'NO OUTBOUND DELIVERY',
])

const assertPreviewOptions = (options: MockOnlyPreviewOptions): void => {
  if (options.mode !== REQUIRED_OPTIONS.mode || options.source !== REQUIRED_OPTIONS.source) {
    throw new Error('Mock-only preview requires mode=mock and source=local_preview_only.')
  }
}

const getFixtureMetadata = (fixture: FixtureMetadata): MockOnlyPreviewMetadata => {
  const metadata = fixture.metadata

  if (
    metadata?.mode !== REQUIRED_OPTIONS.mode ||
    metadata.source !== REQUIRED_OPTIONS.source ||
    metadata.contains_real_data !== false ||
    metadata.contains_secrets !== false ||
    metadata.safe_for_windows_preview !== true
  ) {
    throw new Error('Mock-only preview fixture metadata is not safe for local preview.')
  }

  return {
    mode: REQUIRED_OPTIONS.mode,
    source: REQUIRED_OPTIONS.source,
    containsRealData: false,
    containsSecrets: false,
    safeForWindowsPreview: true,
  }
}

export const getMockOnlyPreviewSummary = (options: MockOnlyPreviewOptions): MockOnlyPreviewMetadata => {
  assertPreviewOptions(options)

  const service = createMockApiService(options)
  return getFixtureMetadata(service.getMockModule<FixtureMetadata>('dashboard'))
}

export const getMockOnlyPreviewSections = (
  options: MockOnlyPreviewOptions,
): readonly MockOnlyPreviewSection[] => {
  assertPreviewOptions(options)

  const service = createMockApiService(options)
  const dashboard = service.getMockModule('dashboard')
  const portfolio = service.getMockModule('portfolio')
  const history = service.getMockModule('history')
  const alerts = service.getMockModule('alerts')
  const agent = service.getMockModule('agent')
  const emptyStates = service.getMockModule('emptyStates')

  return Object.freeze([
    {
      id: 'safety-banner',
      title: '安全边界',
      description: '固定展示 mock-only、本地预览、脱敏 fixture 和不对外发送的安全标签。',
      status: '后续建设',
      data: SAFETY_BANNER,
    },
    {
      id: 'dashboard-summary',
      title: '仪表盘摘要',
      description: '展示今日一句话摘要、市场状态、模拟持仓、仓位、风险和动作建议示例。',
      status: '可预览',
      previewAnchor: 'mock-dashboard-summary-preview',
      data: dashboard,
    },
    {
      id: 'portfolio-preview',
      title: '持仓预览',
      description: '展示模拟账户、持仓列表、风险提示和今日观察备注；仅使用静态脱敏 fixture。',
      status: '可预览',
      previewAnchor: 'mock-portfolio-preview',
      data: portfolio,
    },
    {
      id: 'history-reports-preview',
      title: '历史报告预览',
      description: '展示历史报告列表与详情示例；仅使用静态脱敏 fixture，不读取真实日报。',
      status: '可预览',
      previewAnchor: 'mock-history-reports-preview',
      data: history,
    },
    {
      id: 'alerts-preview',
      title: '提醒预览',
      description: '后续展示提醒规则、触发记录与发送形态示例；当前不会发送通知。',
      status: '后续建设',
      data: alerts,
    },
    {
      id: 'agent-chat-preview',
      title: 'Agent 对话预览',
      description: '后续展示 Agent 会话、消息、流式片段和错误示例；当前不接真实 Agent。',
      status: '后续建设',
      data: agent,
    },
    {
      id: 'empty-error-examples',
      title: '空状态与错误示例',
      description: '后续展示空状态和错误形态，用于未来页面渲染检查。',
      status: '后续建设',
      data: emptyStates,
    },
    {
      id: 'local-settings-import-export',
      title: '本地设置与导入导出预览',
      description: 'Web-P20 静态边界预览：不读取文件、配置或密钥。',
      status: '后续建设',
      data: Object.freeze({
        settingsMode: 'mock_only_locked',
        importMode: 'review_only',
        exportMode: 'not_generated',
      }),
    },
  ])
}

export const createMockOnlyPreviewModel = (options: MockOnlyPreviewOptions): MockOnlyPreviewModel => {
  const metadata = getMockOnlyPreviewSummary(options)
  const sections = getMockOnlyPreviewSections(options)

  return Object.freeze({
    metadata,
    safetyBanner: SAFETY_BANNER,
    sections,
    dashboardSummaryPreview: DASHBOARD_SUMMARY_PREVIEW,
    portfolioPreview: PORTFOLIO_PREVIEW,
    historyReportsPreview: HISTORY_REPORTS_PREVIEW,
  })
}
