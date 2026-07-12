import { createMockApiService } from '../service/mockApiService'
import type {
  MockOnlyDashboardSummaryPreview,
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
      description: '后续展示模拟账户、持仓结构、风险和交易示例；当前不伪装为已完成。',
      status: '后续建设',
      data: portfolio,
    },
    {
      id: 'history-reports-preview',
      title: '历史报告预览',
      description: '后续展示历史报告列表与详情示例；当前仅保留模块入口占位。',
      status: '后续建设',
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
  })
}
