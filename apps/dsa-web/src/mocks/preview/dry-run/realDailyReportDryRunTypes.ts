export type RealDailyReportDryRunSourceType = 'mock-only' | 'dry-run' | 'real-readonly'

export type RealDailyReportDryRunValidationStatus = 'pending' | 'passed' | 'blocked'

export interface RealDailyReportDryRunSource {
  readonly sourceType: RealDailyReportDryRunSourceType
  readonly providerName: string
  readonly isMock: boolean
  readonly isRealReadOnly: boolean
  readonly isRedacted: boolean
  readonly collectedAtLabel: string
}

export interface RealDailyReportDryRunSection {
  readonly sectionId: string
  readonly title: string
  readonly summary: string
  readonly amountLabel: string
  readonly ratioLabel: string
}

export interface RealDailyReportDryRunReport {
  readonly reportId: string
  readonly reportDateLabel: string
  readonly generatedAtLabel: string
  readonly title: 'AI股票基金每日信息报告'
  readonly headline: string
  readonly marketMood: string
  readonly riskLevel: string
  readonly portfolioAction: string
  readonly sections: readonly RealDailyReportDryRunSection[]
}

export interface RealDailyReportDryRunSafety {
  readonly allowRealProvider: false
  readonly allowRealAccountRead: false
  readonly allowNotificationSend: false
  readonly allowTrading: false
  readonly allowAiCall: false
  readonly requiresHumanApproval: true
}

export interface RealDailyReportDryRunRedaction {
  readonly containsRealAccountData: false
  readonly containsSecrets: false
  readonly containsWebhook: false
  readonly containsToken: false
  readonly containsApiKey: false
  readonly containsPersonalContact: false
  readonly redactionStatus: string
}

export interface RealDailyReportDryRunValidation {
  readonly schemaVersion: string
  readonly status: RealDailyReportDryRunValidationStatus
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
}

export interface RealDailyReportDryRunRollback {
  readonly fallbackMode: 'mock-only'
  readonly fallbackReason: string
  readonly canFallbackToMockOnly: true
}

export interface RealDailyReportDryRunInput {
  readonly contractVersion: string
  readonly mode: 'dry-run'
  readonly dryRun: true
  readonly projectName: '股票基金质量分析系统'
  readonly reportDisplayName: 'AI股票基金每日信息报告'
  readonly source: RealDailyReportDryRunSource
  readonly report: RealDailyReportDryRunReport
  readonly safety: RealDailyReportDryRunSafety
  readonly redaction: RealDailyReportDryRunRedaction
  readonly validation: RealDailyReportDryRunValidation
  readonly rollback: RealDailyReportDryRunRollback
}
