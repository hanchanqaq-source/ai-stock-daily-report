import type { MockApiServiceOptions } from '../service/mockApiServiceTypes'

export type MockOnlyPreviewOptions = MockApiServiceOptions & {
  readonly mode: 'mock'
  readonly source: 'local_preview_only'
}

export type MockOnlyPreviewSectionId =
  | 'safety-banner'
  | 'dashboard-summary'
  | 'portfolio-preview'
  | 'history-reports-preview'
  | 'alerts-preview'
  | 'agent-chat-preview'
  | 'empty-error-examples'
  | 'local-settings-import-export'

export interface MockOnlyPreviewMetadata {
  readonly mode: 'mock'
  readonly source: 'local_preview_only'
  readonly containsRealData: false
  readonly containsSecrets: false
  readonly safeForWindowsPreview: true
}

export type MockOnlyPreviewSectionStatus = '可预览' | '后续建设'

export interface MockOnlyPreviewSection<TData = unknown> {
  readonly id: MockOnlyPreviewSectionId
  readonly title: string
  readonly description: string
  readonly status: MockOnlyPreviewSectionStatus
  readonly previewAnchor?: string
  readonly data: TData
}

export interface MockOnlyDashboardSummaryPreview {
  readonly headline: string
  readonly marketStatus: string
  readonly totalHoldingAmount: string
  readonly dailyChange: string
  readonly positionRatio: string
  readonly riskLevel: string
  readonly labels: readonly string[]
  readonly holdingStructure: readonly { readonly name: string; readonly ratio: string }[]
  readonly riskWarnings: readonly string[]
  readonly actionSuggestions: readonly string[]
}

export interface MockOnlyPortfolioHoldingPreview {
  readonly name: string
  readonly category: string
  readonly amountLabel: string
  readonly weightLabel: string
  readonly pnlLabel: string
  readonly riskLevel: string
  readonly note: string
}

export interface MockOnlyPortfolioPreview {
  readonly accountLabel: string
  readonly totalAmountLabel: string
  readonly targetAmountLabel: string
  readonly positionRatioLabel: string
  readonly labels: readonly string[]
  readonly holdings: readonly MockOnlyPortfolioHoldingPreview[]
  readonly riskNotes: readonly string[]
  readonly actionNotes: readonly string[]
}

export interface MockOnlyHistoryReportItemPreview {
  readonly reportDateLabel: string
  readonly title: string
  readonly status: string
  readonly marketMood: string
  readonly portfolioAction: string
  readonly riskLevel: string
  readonly deliveryStatus: string
  readonly note: string
}

export interface MockOnlyHistoryReportDetailPreview {
  readonly title: string
  readonly generatedAtLabel: string
  readonly headline: string
  readonly sections: readonly { readonly title: string; readonly content: string }[]
  readonly tags: readonly string[]
}

export interface MockOnlyHistoryReportsPreview {
  readonly summary: readonly { readonly label: string; readonly value: string }[]
  readonly reports: readonly MockOnlyHistoryReportItemPreview[]
  readonly selectedReport: MockOnlyHistoryReportDetailPreview
  readonly riskNotes: readonly string[]
  readonly actionNotes: readonly string[]
}

export interface MockOnlyAlertRulePreview {
  readonly name: string
  readonly scope: string
  readonly condition: string
  readonly severity: string
  readonly status: string
  readonly note: string
}

export interface MockOnlyAlertTriggerPreview {
  readonly triggeredAtLabel: string
  readonly ruleName: string
  readonly status: string
  readonly observedValue: string
  readonly decision: string
  readonly note: string
}

export interface MockOnlyAlertDeliveryPreview {
  readonly channel: string
  readonly status: string
  readonly targetLabel: string
  readonly sentAtLabel: string
  readonly message: string
}

export interface MockOnlyAlertsPreview {
  readonly summary: readonly { readonly label: string; readonly value: string }[]
  readonly labels: readonly string[]
  readonly rules: readonly MockOnlyAlertRulePreview[]
  readonly triggers: readonly MockOnlyAlertTriggerPreview[]
  readonly deliveries: readonly MockOnlyAlertDeliveryPreview[]
  readonly riskNotes: readonly string[]
  readonly actionNotes: readonly string[]
}

export interface MockOnlyAgentSessionPreview {
  readonly sessionLabel: string
  readonly status: string
  readonly startedAtLabel: string
  readonly topic: string
  readonly mode: string
  readonly note: string
}

export interface MockOnlyAgentMessagePreview {
  readonly role: string
  readonly content: string
  readonly status: string
  readonly timestampLabel: string
  readonly note: string
}

export interface MockOnlyAgentStreamChunkPreview {
  readonly order: number
  readonly type: string
  readonly content: string
  readonly status: string
  readonly note: string
}

export interface MockOnlyAgentErrorPreview {
  readonly title: string
  readonly status: string
  readonly message: string
  readonly recoveryHint: string
}

export interface MockOnlyAgentChatPreview {
  readonly summary: readonly { readonly label: string; readonly value: string }[]
  readonly labels: readonly string[]
  readonly sessions: readonly MockOnlyAgentSessionPreview[]
  readonly messages: readonly MockOnlyAgentMessagePreview[]
  readonly streamChunks: readonly MockOnlyAgentStreamChunkPreview[]
  readonly errorExamples: readonly MockOnlyAgentErrorPreview[]
  readonly riskNotes: readonly string[]
  readonly actionNotes: readonly string[]
}

export interface MockOnlyPreviewModel {
  readonly metadata: MockOnlyPreviewMetadata
  readonly safetyBanner: readonly string[]
  readonly sections: readonly MockOnlyPreviewSection[]
  readonly dashboardSummaryPreview: MockOnlyDashboardSummaryPreview
  readonly portfolioPreview: MockOnlyPortfolioPreview
  readonly historyReportsPreview: MockOnlyHistoryReportsPreview
  readonly alertsPreview: MockOnlyAlertsPreview
  readonly agentChatPreview: MockOnlyAgentChatPreview
}
