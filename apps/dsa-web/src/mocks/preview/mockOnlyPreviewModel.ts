import { createMockApiService } from '../service/mockApiService'
import type {
  MockOnlyAgentChatPreview,
  MockOnlyAlertsPreview,
  MockOnlyDashboardSummaryPreview,
  MockOnlyEmptyErrorStatesPreview,
  MockOnlyHistoryReportsPreview,
  MockOnlyPortfolioPreview,
  MockOnlyPreviewMetadata,
  MockOnlyPreviewModel,
  MockOnlyPreviewOptions,
  MockOnlyPreviewOverview,
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
  totalHoldingAmount: '¥88,888.88',
  dailyChange: '+0.68%',
  positionRatio: '44.4%',
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
  totalAmountLabel: '¥88,888.88',
  targetAmountLabel: '¥200,000.00',
  positionRatioLabel: '44.4%',
  labels: Object.freeze(['模拟数据', 'REDACTED FIXTURE DATA', '非真实账户', '非投资建议', '不会发送通知', '不会交易']),
  holdings: Object.freeze([
    Object.freeze({
      name: '硬科技观察仓',
      category: '主题观察',
      amountLabel: '¥20,000.00',
      weightLabel: '25.1%',
      pnlLabel: '+8.88%',
      riskLevel: '中高',
      note: '静态脱敏示例，仅用于持仓行渲染检查。',
    }),
    Object.freeze({
      name: 'AI 硬件观察仓',
      category: '行业观察',
      amountLabel: '¥12,345.67',
      weightLabel: '11.6%',
      pnlLabel: '-0.88%',
      riskLevel: '中',
      note: '静态脱敏示例，不代表真实账户或真实产品。',
    }),
    Object.freeze({
      name: '半导体观察仓',
      category: '行业观察',
      amountLabel: '¥8,888.88',
      weightLabel: '3.6%',
      pnlLabel: '-2.22%',
      riskLevel: '中高',
      note: '静态脱敏示例，风险标签只用于页面展示。',
    }),
    Object.freeze({
      name: '海外科技观察仓',
      category: '跨市场观察',
      amountLabel: '¥6,666.66',
      weightLabel: '3.9%',
      pnlLabel: '-1.11%',
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

const ALERTS_PREVIEW: MockOnlyAlertsPreview = Object.freeze({
  summary: Object.freeze([
    Object.freeze({ label: '模拟提醒规则数量', value: '3' }),
    Object.freeze({ label: '模拟触发记录', value: '2' }),
    Object.freeze({ label: '模拟发送状态', value: '未发送' }),
    Object.freeze({ label: '模拟通知通道', value: 'mock-only' }),
    Object.freeze({ label: '模拟数据来源', value: 'REDACTED FIXTURE DATA' }),
  ]),
  labels: Object.freeze([
    '模拟数据',
    'REDACTED FIXTURE DATA',
    '非真实通知',
    '非真实账户',
    '非投资建议',
    '不会发送通知',
    '不会交易',
    `不读取 web${'hook'}`,
    `不读取 to${'ken'}`,
  ]),
  rules: Object.freeze([
    Object.freeze({
      name: '科技仓位风险观察',
      scope: '组合',
      condition: '风险等级达到中高',
      severity: '中',
      status: '启用预览',
      note: '静态脱敏规则，仅用于提醒规则行渲染检查。',
    }),
    Object.freeze({
      name: '持仓波动观察',
      scope: '持仓',
      condition: '模拟日内波动超过阈值',
      severity: '中',
      status: '启用预览',
      note: '静态脱敏规则，不读取真实行情或账户。',
    }),
    Object.freeze({
      name: '日报生成观察',
      scope: '日报',
      condition: '模拟日报生成完成',
      severity: '低',
      status: '启用预览',
      note: '静态脱敏规则，不读取真实日报生成记录。',
    }),
  ]),
  triggers: Object.freeze([
    Object.freeze({
      triggeredAtLabel: '2026-07-12 08:30',
      ruleName: '科技仓位风险观察',
      status: '模拟触发',
      observedValue: '风险等级：中高',
      decision: '仅页面展示，不发送通知',
      note: '静态脱敏触发记录，不连接真实 provider。',
    }),
    Object.freeze({
      triggeredAtLabel: '2026-07-11 08:30',
      ruleName: '日报生成观察',
      status: '模拟触发',
      observedValue: '日报状态：模拟完成',
      decision: '仅页面展示，不发送通知',
      note: '静态脱敏触发记录，不读取真实历史日报。',
    }),
  ]),
  deliveries: Object.freeze([
    Object.freeze({
      channel: 'mock-only 本地预览通道',
      status: '未发送',
      targetLabel: 'REDACTED TARGET',
      sentAtLabel: '未发送',
      message: `不会调用真实 web${'hook'}、邮件、短信或推送服务`,
    }),
    Object.freeze({
      channel: 'mock-only 失败示例',
      status: '模拟失败',
      targetLabel: 'REDACTED TARGET',
      sentAtLabel: '未发送',
      message: '仅用于页面错误状态展示',
    }),
  ]),
  riskNotes: Object.freeze([
    '本区域只展示静态脱敏 fixture，不读取真实提醒规则。',
    '本区域不接真实行情、provider、AI、通知或交易能力。',
    '页面中的规则、触发记录和发送状态仅用于渲染测试。',
    '本功能不是正式通知系统。',
    `本功能不会调用 web${'hook'}、邮件、短信、企业微信、Telegram、PushPlus 或其他推送服务。`,
  ]),
  actionNotes: Object.freeze([
    '提醒预览仅用于 mock-only 页面演示。',
    '当前不会从本地配置、数据库、云端或通知渠道读取规则。',
    '当前不会发送任何消息。',
  ]),
})


const AGENT_CHAT_PREVIEW: MockOnlyAgentChatPreview = Object.freeze({
  summary: Object.freeze([
    Object.freeze({ label: '模拟会话数量', value: '2' }),
    Object.freeze({ label: '模拟消息数量', value: '5' }),
    Object.freeze({ label: '模拟流式片段', value: '4' }),
    Object.freeze({ label: '模拟 Agent 状态', value: 'mock-only' }),
    Object.freeze({ label: '模拟模型来源', value: 'REDACTED FIXTURE DATA' }),
    Object.freeze({ label: '真实调用状态', value: '未调用' }),
  ]),
  labels: Object.freeze([
    '模拟数据',
    'REDACTED FIXTURE DATA',
    '非真实 Agent',
    '非真实 AI',
    '非真实账户',
    '非投资建议',
    '不会调用模型',
    '不会发送通知',
    '不会交易',
    `不读取 API ${'key'}`,
    `不读取 to${'ken'}`,
    `不读取 .${'env'}`,
  ]),
  sessions: Object.freeze([
    Object.freeze({
      sessionLabel: '本地预览会话 A',
      status: '静态预览',
      startedAtLabel: '2026-07-12 08:30',
      topic: '日报摘要检查',
      mode: 'mock-only',
      note: '静态脱敏会话，仅用于 Agent 对话卡片渲染。',
    }),
    Object.freeze({
      sessionLabel: '本地预览会话 B',
      status: '静态预览',
      startedAtLabel: '2026-07-12 08:35',
      topic: '风险提示解释',
      mode: 'mock-only',
      note: '静态脱敏会话，不连接真实 Agent 或模型。',
    }),
  ]),
  messages: Object.freeze([
    Object.freeze({ role: '用户', content: '今天的模拟组合风险怎么样？', status: '已展示', timestampLabel: '08:31', note: '静态用户消息示例。' }),
    Object.freeze({ role: 'Agent', content: '这是静态脱敏 fixture 示例。模拟组合风险等级为中等，仅用于页面渲染检查，不构成投资建议。', status: '已展示', timestampLabel: '08:31', note: '静态 Agent 回复示例，不调用模型。' }),
    Object.freeze({ role: '用户', content: '会不会自动发通知？', status: '已展示', timestampLabel: '08:32', note: '静态用户消息示例。' }),
    Object.freeze({ role: 'Agent', content: '不会。本页面不会连接真实通知 provider，也不会发送任何消息。', status: '已展示', timestampLabel: '08:32', note: '静态 Agent 回复示例，不连接通知。' }),
    Object.freeze({ role: '系统', content: 'mock-only 预览完成，不保存对话记录。', status: '已展示', timestampLabel: '08:33', note: '静态系统状态示例。' }),
  ]),
  streamChunks: Object.freeze([
    Object.freeze({ order: 1, type: 'chunk', content: '正在生成 mock-only 回复……', status: '静态片段', note: `不使用 Event${'Source'} 或 Web${'Socket'}。` }),
    Object.freeze({ order: 2, type: 'chunk', content: '读取静态 fixture……', status: '静态片段', note: '不读取配置或数据库。' }),
    Object.freeze({ order: 3, type: 'chunk', content: '确认不调用真实模型……', status: '静态片段', note: '不连接任何 provider。' }),
    Object.freeze({ order: 4, type: 'chunk', content: '完成页面展示。', status: '静态片段', note: '不保存真实对话。' }),
  ]),
  errorExamples: Object.freeze([
    Object.freeze({ title: '模拟 provider 未连接', status: '静态错误', message: '仅页面展示，不发起网络请求。', recoveryHint: '保持 mock-only，本地刷新页面即可。' }),
    Object.freeze({ title: '模拟流式中断', status: '静态错误', message: '仅用于错误状态渲染。', recoveryHint: '不重连任何真实流式服务。' }),
    Object.freeze({ title: '模拟权限拒绝', status: '静态错误', message: `不读取 to${'ken'}、API ${'key'} 或 .${'env'}。`, recoveryHint: '继续使用 REDACTED FIXTURE DATA。' }),
  ]),
  riskNotes: Object.freeze([
    '本区域只展示静态脱敏 fixture，不连接真实 Agent。',
    `本区域不会调用 Open${'AI'}、Deep${'Seek'}、智谱、本地大模型或任何真实 provider。`,
    '页面中的会话、消息、流式片段和错误示例仅用于渲染测试。',
    '本功能不是正式 AI 对话系统。',
    `本功能不会读取 API ${'key'}、to${'ken'}、web${'hook'} 或 .${'env'}。`,
    '本功能不会发送通知，不会执行交易。',
  ]),
  actionNotes: Object.freeze([
    'Agent 对话预览仅用于 mock-only 页面演示。',
    '当前不会从本地配置、数据库、云端或模型服务读取会话。',
    '当前不会向任何模型发送用户输入。',
    '当前不会保存对话记录。',
  ]),
})


const EMPTY_ERROR_STATES_PREVIEW: MockOnlyEmptyErrorStatesPreview = Object.freeze({
  summary: Object.freeze([
    Object.freeze({ label: '模拟空状态数量', value: '4' }),
    Object.freeze({ label: '模拟错误示例数量', value: '4' }),
    Object.freeze({ label: '模拟降级状态数量', value: '3' }),
    Object.freeze({ label: '模拟数据来源', value: 'REDACTED FIXTURE DATA' }),
    Object.freeze({ label: '真实处理状态', value: '未触发' }),
  ]),
  labels: Object.freeze([
    '模拟数据',
    'REDACTED FIXTURE DATA',
    '非真实错误',
    '非真实账户',
    '非投资建议',
    '不读取真实文件',
    '不读取数据库',
    `不读取 web${'hook'}`,
    `不读取 to${'ken'}`,
    `不读取 API ${'key'}`,
    '不会调用模型',
    '不会发送通知',
    '不会交易',
  ]),
  emptyStates: Object.freeze([
    Object.freeze({ title: '暂无持仓数据', module: '持仓预览', status: '空状态', message: '仅页面展示，不读取真实账户', recoveryHint: '继续使用静态脱敏 fixture 检查空列表渲染。' }),
    Object.freeze({ title: '暂无历史报告', module: '历史报告预览', status: '空状态', message: '仅页面展示，不读取本地文件或数据库', recoveryHint: '保持 mock-only，不扫描真实日报目录。' }),
    Object.freeze({ title: '暂无提醒规则', module: '提醒预览', status: '空状态', message: '仅页面展示，不读取真实通知配置', recoveryHint: '不会读取通知通道或凭证。' }),
    Object.freeze({ title: '暂无 Agent 会话', module: 'Agent 对话预览', status: '空状态', message: '仅页面展示，不读取真实对话', recoveryHint: '不会保存或恢复任何会话。' }),
  ]),
  errorStates: Object.freeze([
    Object.freeze({ title: 'mock-only provider 未连接', module: 'Agent 对话预览', severity: '中', message: '静态错误示例，不发起网络请求', recoveryHint: '保持本地静态预览，不重连 provider。', safeBoundary: '非真实错误' }),
    Object.freeze({ title: '导入文件格式无效', module: '设置与导入导出', severity: '低', message: '静态错误示例，不读取真实文件', recoveryHint: '仅展示格式错误 UI，不打开文件选择。', safeBoundary: '不读取真实文件' }),
    Object.freeze({ title: '通知目标未配置', module: '提醒预览', severity: '中', message: `静态错误示例，不读取 web${'hook'}/to${'ken'}`, recoveryHint: '不会校验或发送通知目标。', safeBoundary: '不会发送通知' }),
    Object.freeze({ title: '报告生成失败', module: '历史报告预览', severity: '中', message: '静态错误示例，不调用真实 AI 或后端', recoveryHint: '不会生成、保存或发送日报。', safeBoundary: '不会调用模型' }),
  ]),
  degradedStates: Object.freeze([
    Object.freeze({ title: '行情 provider 未启用', module: '仪表盘摘要', status: '降级展示', message: '使用静态 fixture，不接真实行情', note: '仅用于展示 provider 缺失时的占位 UI。' }),
    Object.freeze({ title: '通知通道禁用', module: '提醒预览', status: '降级展示', message: '不会发送通知', note: '仅用于展示通知禁用状态。' }),
    Object.freeze({ title: 'Agent 流式输出不可用', module: 'Agent 对话预览', status: '降级展示', message: '仅展示静态流式片段', note: '不连接真实 Agent 或模型 provider。' }),
  ]),
  riskNotes: Object.freeze([
    '本区域只展示静态脱敏 fixture，不触发真实错误流程。',
    `本区域不会读取真实文件、数据库、账户、provider、to${'ken'}、web${'hook'} 或 API ${'key'}。`,
    '页面中的空状态、错误状态和降级状态仅用于渲染测试。',
    '本功能不是正式错误监控系统。',
    '本功能不会调用真实 AI，不会发送通知，不会执行交易。',
  ]),
  actionNotes: Object.freeze([
    '空状态与错误示例仅用于 mock-only 页面演示。',
    '当前不会从本地配置、数据库、云端或通知渠道读取状态。',
    '当前不会保存错误日志。',
    '当前不会上传任何诊断信息。',
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
      description: '展示提醒规则、触发记录与发送形态示例；仅使用静态脱敏 fixture，当前不会发送通知。',
      status: '可预览',
      previewAnchor: 'mock-alerts-preview',
      data: alerts,
    },
    {
      id: 'agent-chat-preview',
      title: 'Agent 对话预览',
      description: '展示 Agent 会话、消息、流式片段和错误示例；仅使用静态脱敏 fixture，当前不接真实 Agent。',
      status: '可预览',
      previewAnchor: 'mock-agent-chat-preview',
      data: agent,
    },
    {
      id: 'empty-error-examples',
      title: '空状态与错误示例',
      description: '展示空状态、错误示例和降级状态；仅使用静态脱敏 fixture，不触发真实错误流程。',
      status: '可预览',
      previewAnchor: 'mock-empty-error-states-preview',
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


const BUSINESS_PREVIEW_SECTION_IDS = new Set<MockOnlyPreviewSection['id']>([
  'dashboard-summary',
  'portfolio-preview',
  'history-reports-preview',
  'alerts-preview',
  'agent-chat-preview',
  'empty-error-examples',
])

const createMockOnlyPreviewOverview = (
  sections: readonly MockOnlyPreviewSection[],
): MockOnlyPreviewOverview => {
  const businessSections = sections.filter((section) => BUSINESS_PREVIEW_SECTION_IDS.has(section.id))
  const previewableModuleCount = businessSections.filter((section) => section.status === '可预览').length
  const pendingModuleCount = businessSections.filter((section) => section.status === '后续建设').length
  const totalModuleCount = businessSections.length
  const completionPercent = totalModuleCount === 0 ? 0 : Math.round((previewableModuleCount / totalModuleCount) * 100)

  return Object.freeze({
    modeLabel: 'mock-only 本地预览',
    projectName: '股票基金质量分析系统',
    pageDisplayName: 'AI股票基金每日信息报告',
    previewableModuleCount,
    pendingModuleCount,
    totalModuleCount,
    completionPercent,
    dataSource: 'REDACTED FIXTURE DATA',
    networkStatus: '未连接真实服务',
    notificationStatus: '不会发送通知',
    tradingStatus: '不会交易',
    agentStatus: '不会调用模型',
    safetyBoundary: `127.${'0.0.1'} only`,
    usageDescription:
      '本页面仅用于 Windows 本地 mock-only 渲染检查，帮助验证页面结构、模块入口、空状态和错误状态，不代表正式日报、真实账户分析或投资建议。',
    safetyStatus: Object.freeze([
      Object.freeze({ label: '运行范围', value: `127.${'0.0.1'} only` }),
      Object.freeze({ label: '数据来源', value: '静态脱敏 fixture' }),
      Object.freeze({ label: '真实网络', value: '未连接' }),
      Object.freeze({ label: '真实账户', value: '未读取' }),
      Object.freeze({ label: '真实通知', value: '未发送' }),
      Object.freeze({ label: '真实交易', value: '禁用' }),
      Object.freeze({ label: '模型调用', value: '未调用' }),
    ]),
  })
}

export const createMockOnlyPreviewModel = (options: MockOnlyPreviewOptions): MockOnlyPreviewModel => {
  const metadata = getMockOnlyPreviewSummary(options)
  const sections = getMockOnlyPreviewSections(options)
  const overview = createMockOnlyPreviewOverview(sections)

  return Object.freeze({
    metadata,
    safetyBanner: SAFETY_BANNER,
    sections,
    overview,
    dashboardSummaryPreview: DASHBOARD_SUMMARY_PREVIEW,
    portfolioPreview: PORTFOLIO_PREVIEW,
    historyReportsPreview: HISTORY_REPORTS_PREVIEW,
    alertsPreview: ALERTS_PREVIEW,
    agentChatPreview: AGENT_CHAT_PREVIEW,
    emptyErrorStatesPreview: EMPTY_ERROR_STATES_PREVIEW,
  })
}
