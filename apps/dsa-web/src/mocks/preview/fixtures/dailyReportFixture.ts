import type { MockOnlyDailyReportFixture } from '../mockOnlyPreviewTypes'

export const MOCK_ONLY_DAILY_REPORT_FIXTURE: MockOnlyDailyReportFixture = Object.freeze({
  reportId: 'mock-daily-report-2026-07-12-local-preview',
  projectName: '股票基金质量分析系统',
  reportDateLabel: '2026-07-12 本地静态预览',
  title: 'AI股票基金每日信息报告',
  displayName: 'AI股票基金每日信息报告',
  modeLabel: 'mock-only 本地预览',
  dataSourceLabel: 'REDACTED FIXTURE DATA - 静态脱敏 fixture',
  generatedAtLabel: '2026-07-12 08:30 本地静态预览',
  deliveryStatus: '未发送',
  marketMood: '震荡观察',
  headline: '科技方向保持震荡，模拟组合以观察为主，暂不进行主动调仓。',
  portfolioAction: '不调仓',
  riskLevel: '中等',
  sections: Object.freeze({
    marketOverview: Object.freeze({
      title: '市场概览',
      content: '静态脱敏 fixture 示例，不接真实行情、provider 或外部请求。',
    }),
    portfolioObservation: Object.freeze({
      title: '组合观察',
      content: '模拟组合使用虚构金额与比例，仅用于页面渲染检查，不读取真实账户。',
    }),
    riskWarnings: Object.freeze({
      title: '风险提示',
      content: '页面仅展示模拟数据、非真实账户与非投资建议，不代表正式日报结论。',
    }),
    actionSuggestions: Object.freeze({
      title: '动作建议',
      content: '保持观察；不会发送通知、不会交易、不会调用模型。',
    }),
  }),
  safetyLabels: Object.freeze([
    '模拟数据',
    '非真实账户',
    '非投资建议',
    '不会发送通知',
    '不会交易',
    '不会调用模型',
    `127.${'0.0.1'} only`,
  ]),
  redactionLabels: Object.freeze([
    'REDACTED FIXTURE DATA',
    '静态脱敏 fixture',
    '不读取真实历史日报文件',
    '不读取数据库',
    `不读取 web${'hook'}`,
    `不读取 to${'ken'}`,
    `不读取 API ${'key'}`,
    `不读取 .${'env'}`,
  ]),
  mockOnlyNotes: Object.freeze([
    '本 fixture 只服务 Web-P31 mock-only 预览结构统一。',
    '日期为固定 mock 日期，并标注为本地静态预览。',
    '金额、收益率和比例均为明显虚构展示数据，不复用真实持仓精确值。',
    '当前仍不得接真实 API、provider、AI、通知、账户、数据库或交易。',
  ]),
})
