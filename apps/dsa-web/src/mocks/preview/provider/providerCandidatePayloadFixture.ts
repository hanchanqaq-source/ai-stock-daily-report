export interface ProviderCandidateSection {
  readonly sectionId: string
  readonly title: string
  readonly summary: string
  readonly notes: readonly string[]
}

export interface ProviderCandidateMetric {
  readonly metricId: string
  readonly label: string
  readonly valueLabel: string
  readonly unitLabel: string
  readonly notes: readonly string[]
}

export interface ProviderCandidateRiskSignal {
  readonly signalId: string
  readonly label: string
  readonly levelLabel: string
  readonly valueLabel: string
  readonly notes: readonly string[]
}

export interface ProviderCandidatePayload {
  readonly candidateId: string
  readonly candidateType: string
  readonly providerType: string
  readonly sourceLabel: string
  readonly dataFreshnessLabel: string
  readonly sections: readonly ProviderCandidateSection[]
  readonly metrics: readonly ProviderCandidateMetric[]
  readonly riskSignals: readonly ProviderCandidateRiskSignal[]
  readonly redactionLabels: readonly string[]
  readonly safetyLabels: readonly string[]
  readonly mockOnlyNotes: readonly string[]
}

const sections = Object.freeze([
  Object.freeze({
    sectionId: 'MOCK_SECTION_MARKET_OBSERVATION',
    title: '市场候选观察',
    summary: '静态脱敏候选数据，仅用于后续 schema normalization 和 validator 测试准备，不是真实行情。',
    notes: Object.freeze(['非真实来源', '不读取外部数据', '不调用 AI']),
  }),
  Object.freeze({
    sectionId: 'MOCK_SECTION_PORTFOLIO_OBSERVATION',
    title: '组合候选观察',
    summary: '虚构组合候选说明，不是真实账户、真实持仓或投资建议。',
    notes: Object.freeze(['非真实账户', '不交易', '不触发通知']),
  }),
  Object.freeze({
    sectionId: 'MOCK_SECTION_RISK_SIGNAL',
    title: '风险候选信号',
    summary: '仅包含 MOCK_RISK_LEVEL 与 REDACTED_VALUE 占位符，不代表真实风险结论。',
    notes: Object.freeze(['静态脱敏候选数据', '不可直接进入页面', '必须先经过 schema normalization']),
  }),
  Object.freeze({
    sectionId: 'MOCK_SECTION_ACTION_NOTE',
    title: '行动候选说明',
    summary: '候选 payload 不发送通知、不交易、不调用 AI，失败时必须 fallback mock-only。',
    notes: Object.freeze(['不是投资建议', '不是 DailyReportViewModel', '不是 RealDailyReportDryRunInput']),
  }),
] as const satisfies readonly ProviderCandidateSection[])

const metrics = Object.freeze([
  Object.freeze({
    metricId: 'MOCK_METRIC_AMOUNT_PLACEHOLDER',
    label: '候选金额占位',
    valueLabel: 'MOCK_AMOUNT',
    unitLabel: 'MOCK_UNIT',
    notes: Object.freeze(['虚构占位值', '不是精确资产金额']),
  }),
  Object.freeze({
    metricId: 'MOCK_METRIC_RATIO_PLACEHOLDER',
    label: '候选比例占位',
    valueLabel: 'MOCK_RATIO',
    unitLabel: 'MOCK_UNIT',
    notes: Object.freeze(['虚构占位值', '不是精确收益率或真实比例']),
  }),
  Object.freeze({
    metricId: 'MOCK_METRIC_REDACTED_PLACEHOLDER',
    label: '候选脱敏指标',
    valueLabel: 'REDACTED_VALUE',
    unitLabel: 'MOCK_UNIT',
    notes: Object.freeze(['静态脱敏候选数据', '非真实来源']),
  }),
] as const satisfies readonly ProviderCandidateMetric[])

const riskSignals = Object.freeze([
  Object.freeze({
    signalId: 'MOCK_SIGNAL_PLACEHOLDER',
    label: '候选风险信号',
    levelLabel: 'MOCK_RISK_LEVEL',
    valueLabel: 'MOCK_SIGNAL',
    notes: Object.freeze(['低敏虚构信号', '不构成强制交易指令']),
  }),
  Object.freeze({
    signalId: 'MOCK_SIGNAL_REDACTED_VALUE',
    label: '候选脱敏信号',
    levelLabel: 'MOCK_RISK_LEVEL',
    valueLabel: 'REDACTED_VALUE',
    notes: Object.freeze(['非真实来源', '不触发通知或交易']),
  }),
] as const satisfies readonly ProviderCandidateRiskSignal[])

export const MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE: ProviderCandidatePayload = Object.freeze({
  candidateId: 'MOCK_PROVIDER_CANDIDATE_ID',
  candidateType: 'MOCK_CANDIDATE_TYPE',
  providerType: 'PROVIDER_TYPE_PLACEHOLDER',
  sourceLabel: 'REDACTED_PROVIDER_LABEL',
  dataFreshnessLabel: 'MOCK_FRESHNESS_LABEL',
  sections,
  metrics,
  riskSignals,
  redactionLabels: Object.freeze(['REDACTED FIXTURE DATA', '静态脱敏候选数据', '非真实来源']),
  safetyLabels: Object.freeze(['mock-only', 'dry-run only', '非真实账户', '不发送通知', '不交易', '不调用 AI']),
  mockOnlyNotes: Object.freeze([
    'ProviderCandidatePayload mock-only fixture 只为后续 validator 和 schema normalization 测试准备。',
    'candidate payload 不是 RealDailyReportDryRunInput，normalization 后才可能形成 RealDailyReportDryRunInput。',
    'candidate payload 不是 DailyReportViewModel，不得直接进入页面、preview model 或正式 runtime。',
    'RealDailyReportDryRunInput 仍必须经过 validator，validator passed 后才允许 adapter 映射。',
    '任意失败必须 fallback mock-only；当前不接真实 API、provider、AI、通知、账户、数据库或交易。',
  ]),
})
