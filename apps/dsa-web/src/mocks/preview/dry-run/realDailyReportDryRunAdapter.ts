import type { DailyReportViewModel, DailyReportViewSection } from '../mockOnlyPreviewTypes'
import type { RealDailyReportDryRunInput } from './realDailyReportDryRunTypes'
import { validateRealDailyReportDryRunInput } from './realDailyReportDryRunValidator'

export interface RealDailyReportDryRunAdapterResult {
  readonly status: 'adapted' | 'blocked'
  readonly validationStatus: 'passed' | 'blocked'
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
  readonly fallbackMode: 'mock-only'
  readonly canFallbackToMockOnly: true
  readonly viewModel?: DailyReportViewModel
}

const PROJECT_NAME = '股票基金质量分析系统'
const REPORT_DISPLAY_NAME = 'AI股票基金每日信息报告'
const REDACTED_VALUE = 'REDACTED_VALUE'
const REDACTED_PROVIDER_LABEL = 'REDACTED_PROVIDER_LABEL'
const MOCK_AMOUNT = 'MOCK_AMOUNT'
const MOCK_RATIO = 'MOCK_RATIO'
const ALLOWED_SECTION_VALUE_LABELS = new Set([MOCK_AMOUNT, MOCK_RATIO, REDACTED_VALUE])
const ASCII_IDENTIFIER_OR_NUMBER_PATTERN = /[A-Za-z0-9]/

const toSafeDisplayText = (value: string): string =>
  ASCII_IDENTIFIER_OR_NUMBER_PATTERN.test(value) ? REDACTED_VALUE : value

const toSafeSectionLabel = (value: string): string =>
  ALLOWED_SECTION_VALUE_LABELS.has(value) ? value : REDACTED_VALUE

const adaptSection = (section: RealDailyReportDryRunInput['report']['sections'][number]): DailyReportViewSection =>
  Object.freeze({
    title: toSafeDisplayText(section.title),
    content: [
      toSafeDisplayText(section.summary),
      `amountLabel=${toSafeSectionLabel(section.amountLabel)}`,
      `ratioLabel=${toSafeSectionLabel(section.ratioLabel)}`,
    ].join('；'),
  })

export const adaptRealDailyReportDryRunInputToViewModel = (
  input: RealDailyReportDryRunInput,
): RealDailyReportDryRunAdapterResult => {
  const validation = validateRealDailyReportDryRunInput(input)

  if (validation.status === 'blocked') {
    return Object.freeze({
      status: 'blocked',
      validationStatus: 'blocked',
      errors: Object.freeze([...validation.errors]),
      warnings: Object.freeze([...validation.warnings]),
      fallbackMode: 'mock-only',
      canFallbackToMockOnly: true,
    })
  }

  return Object.freeze({
    status: 'adapted',
    validationStatus: 'passed',
    errors: Object.freeze([...validation.errors]),
    warnings: Object.freeze([...validation.warnings]),
    fallbackMode: 'mock-only',
    canFallbackToMockOnly: true,
    viewModel: Object.freeze({
      id: input.report.reportId,
      projectName: PROJECT_NAME,
      reportDateLabel: input.report.reportDateLabel,
      title: REPORT_DISPLAY_NAME,
      displayName: REPORT_DISPLAY_NAME,
      modeLabel: 'dry-run mock-only 草案',
      dataSourceLabel: `${REDACTED_PROVIDER_LABEL} / dry-run / REDACTED / 非真实运行`,
      generatedAtLabel: input.report.generatedAtLabel,
      deliveryStatus: 'dry-run 未发送：不通知、不交易、不调用 AI',
      marketMood: toSafeDisplayText(input.report.marketMood),
      headline: toSafeDisplayText(input.report.headline),
      portfolioAction: toSafeDisplayText(input.report.portfolioAction),
      riskLevel: toSafeDisplayText(input.report.riskLevel),
      sections: Object.freeze(input.report.sections.map(adaptSection)),
      safetyLabels: Object.freeze([
        'mock-only fallback 可用',
        'dry-run 非真实运行',
        '不读取账户',
        '不读取数据库',
        '不发送通知',
        '不交易',
        '不调用 AI',
      ]),
      redactionLabels: Object.freeze([
        'REDACTED dry-run input',
        input.redaction.redactionStatus,
        '不读取凭据',
        '不读取推送端点',
        '不读取环境配置',
      ]),
      notes: Object.freeze([
        'Web-P42 仅为 dry-run adapter 纯函数草案。',
        '只消费静态传入 payload，不接真实 provider、API、AI、通知、账户、数据库或交易。',
        'validator blocked 时保持 mock-only fallback，不生成展示模型。',
      ]),
    }),
  })
}
