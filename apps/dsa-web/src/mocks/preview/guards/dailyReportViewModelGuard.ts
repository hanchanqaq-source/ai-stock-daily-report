import type { DailyReportViewModel } from '../mockOnlyPreviewTypes'

const REQUIRED_PROJECT_NAME = '股票基金质量分析系统'
const REQUIRED_REPORT_NAME = 'AI股票基金每日信息报告'
const REQUIRED_SOURCE_MARKER = 'REDACTED FIXTURE DATA'
const REQUIRED_SECTION_TITLES = Object.freeze(['市场概览', '组合观察', '风险提示', '动作建议'])
const REQUIRED_SAFETY_TEXT = Object.freeze([
  'mock-only',
  REQUIRED_SOURCE_MARKER,
  '非真实账户',
  '非投资建议',
  '不会发送通知',
  '不会交易',
])
const FORBIDDEN_REAL_VALUES = Object.freeze([
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
])
const FORBIDDEN_SECRET_TEXT = Object.freeze([
  ['tok', 'en='].join(''),
  ['API ', 'key'].join(''),
  ['web', 'hook URL'].join(''),
  ['.', 'env 内容'].join(''),
])

const collectViewModelText = (viewModel: DailyReportViewModel): string => JSON.stringify(viewModel)

export const validateMockOnlyDailyReportViewModel = (
  viewModel: DailyReportViewModel,
): readonly string[] => {
  const violations: string[] = []

  if (viewModel.projectName !== REQUIRED_PROJECT_NAME) {
    violations.push(`projectName must be ${REQUIRED_PROJECT_NAME}`)
  }

  if (viewModel.title !== REQUIRED_REPORT_NAME) {
    violations.push(`title must be ${REQUIRED_REPORT_NAME}`)
  }

  if (viewModel.displayName !== REQUIRED_REPORT_NAME) {
    violations.push(`displayName must be ${REQUIRED_REPORT_NAME}`)
  }

  if (!viewModel.dataSourceLabel.includes(REQUIRED_SOURCE_MARKER)) {
    violations.push(`dataSourceLabel must include ${REQUIRED_SOURCE_MARKER}`)
  }

  if (!viewModel.modeLabel.toLowerCase().includes('mock-only') && !viewModel.modeLabel.includes('本地预览')) {
    violations.push('modeLabel must describe mock-only local preview')
  }

  if (viewModel.sections.length !== REQUIRED_SECTION_TITLES.length) {
    violations.push(`sections must contain ${REQUIRED_SECTION_TITLES.length} items`)
  }

  REQUIRED_SECTION_TITLES.forEach((title, index) => {
    if (viewModel.sections[index]?.title !== title) {
      violations.push(`sections[${index}].title must be ${title}`)
    }
  })

  const labelText = [...viewModel.safetyLabels, ...viewModel.redactionLabels, ...viewModel.notes].join('\n')
  for (const requiredText of REQUIRED_SAFETY_TEXT) {
    if (!labelText.includes(requiredText)) {
      violations.push(`safety text must include ${requiredText}`)
    }
  }

  const viewModelText = collectViewModelText(viewModel)
  for (const forbiddenValue of FORBIDDEN_REAL_VALUES) {
    if (viewModelText.includes(forbiddenValue)) {
      violations.push(`view model must not include old precise value ${forbiddenValue}`)
    }
  }

  for (const forbiddenText of FORBIDDEN_SECRET_TEXT) {
    if (viewModelText.includes(forbiddenText)) {
      violations.push(`view model must not include sensitive text ${forbiddenText}`)
    }
  }

  return Object.freeze(violations)
}
