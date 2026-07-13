import { validateRealDailyReportDryRunInput } from '../dry-run/realDailyReportDryRunValidator'
import type { RealDailyReportDryRunInput } from '../dry-run/realDailyReportDryRunTypes'
import type { PublicMarketReadonlyCandidate } from './publicMarketReadonlyCandidateValidator'
import { validatePublicMarketReadonlyCandidate, REDACTED_PROVIDER_LABEL } from './publicMarketReadonlyCandidateValidator'

export const normalizePublicMarketReadonlyCandidateToDryRunInput = (candidate: PublicMarketReadonlyCandidate): { status: 'completed-real-readonly'; normalizedInput: RealDailyReportDryRunInput } | { status: 'blocked'; errors: readonly string[] } => {
  const validation = validatePublicMarketReadonlyCandidate(candidate)
  if (validation.status !== 'passed') return { status: 'blocked', errors: validation.errors }
  const c = validation.candidate
  const input: RealDailyReportDryRunInput = {
    contractVersion: 'core-m3.real-readonly-dry-run.v1', mode: 'dry-run', dryRun: true, projectName: '股票基金质量分析系统', reportDisplayName: 'AI股票基金每日信息报告',
    source: { sourceType: 'real-readonly' as const, providerName: REDACTED_PROVIDER_LABEL, isMock: false, isRealReadOnly: true, isRedacted: true, collectedAtLabel: c.tradeDate.replace(/-/g, '年').replace(/年(\d{2})年/, '年$1月') + '日' },
    report: { reportId: `real-readonly-${c.symbol}`, reportDateLabel: c.tradeDate.replace(/-/g, '年').replace(/年(\d{2})年/, '年$1月') + '日', generatedAtLabel: '本地手动 Dry-Run 生成', title: 'AI股票基金每日信息报告', headline: '公开市场只读数据 Dry-Run 已完成', marketMood: '未进行情绪判断', riskLevel: '未进行投资风险评级', portfolioAction: '仅展示公开行情，不生成操作建议', sections: Object.freeze([
      { sectionId: 'public-market-snapshot', title: `${c.instrumentName}（${c.symbol}）`, summary: `最新可用交易日 ${c.tradeDate.replace(/-/g, '年').replace(/年(\d{2})年/, '年$1月')}日：开盘 ${c.prices.open}，最高 ${c.prices.high}，最低 ${c.prices.low}，收盘 ${c.prices.close}。`, amountLabel: `成交额：${c.amount}`, ratioLabel: c.prices.changePercent === null ? '涨跌幅：未提供' : `涨跌幅：${c.prices.changePercent.toFixed(2)}%` },
      { sectionId: 'public-market-volume', title: '公开成交数据', summary: `成交量：${c.volume}。仅展示公开行情，不生成操作建议。`, amountLabel: `成交量：${c.volume}`, ratioLabel: '风险评级：未进行投资风险评级' },
    ]) },
    safety: { allowRealProvider: false, allowRealAccountRead: false, allowNotificationSend: false, allowTrading: false, allowAiCall: false, requiresHumanApproval: true },
    redaction: { containsRealAccountData: false, containsSecrets: false, containsWebhook: false, containsToken: false, containsApiKey: false, containsPersonalContact: false, redactionStatus: 'redacted' },
    validation: { schemaVersion: 'core-m3.real-readonly-dry-run.v1', status: 'passed', errors: [], warnings: [] },
    rollback: { fallbackMode: 'mock-only', fallbackReason: 'real-readonly can fall back to mock-only on provider unavailable/timeout', canFallbackToMockOnly: true },
  }
  const checked = validateRealDailyReportDryRunInput(input)
  return checked.status === 'passed' ? { status: 'completed-real-readonly', normalizedInput: input } : { status: 'blocked', errors: checked.errors }
}
