import type { RealDailyReportDryRunInput } from '../dry-run/realDailyReportDryRunTypes'

export const REDACTED_PROVIDER_LABEL = 'REDACTED_PROVIDER_LABEL' as const
export type PublicMarketReadonlyCandidate = Readonly<{
  contractVersion: 'core-m3.public-market-readonly.v1'
  sourceType: 'real-readonly'
  providerLabel: typeof REDACTED_PROVIDER_LABEL
  market: 'cn-a'
  instrumentType: 'stock'
  symbol: string
  instrumentName: string
  tradeDate: string
  prices: Readonly<{ open: number; high: number; low: number; close: number; previousClose: number | null; changePercent: number | null }>
  volume: number
  amount: number
  delayed: true
  readOnly: true
  redacted: true
}>
export type ValidationResult = { status: 'passed'; candidate: PublicMarketReadonlyCandidate } | { status: 'blocked'; errors: readonly string[] }
const keys = ['contractVersion','sourceType','providerLabel','market','instrumentType','symbol','instrumentName','tradeDate','prices','volume','amount','delayed','readOnly','redacted']
const priceKeys = ['open','high','low','close','previousClose','changePercent']
const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v) && Object.getPrototypeOf(v) === Object.prototype
const finite = (v: unknown) => typeof v === 'number' && Number.isFinite(v)
const noSensitive = (v: unknown): boolean => JSON.stringify(v).toLowerCase().match(/https?:|token|cookie|authorization|rawresponse|responsebody|endpoint/) === null
export const validatePublicMarketReadonlyCandidate = (input: unknown): ValidationResult => {
  const errors: string[] = []
  if (!isRecord(input)) return { status: 'blocked', errors: ['real-readonly.invalid-object'] }
  if (Object.keys(input).sort().join('|') !== [...keys].sort().join('|')) errors.push('real-readonly.unknown-field')
  if (!noSensitive(input)) errors.push('real-readonly.sensitive-marker')
  if (input.contractVersion !== 'core-m3.public-market-readonly.v1') errors.push('real-readonly.contract-version')
  if (input.sourceType !== 'real-readonly' || input.providerLabel !== REDACTED_PROVIDER_LABEL || input.market !== 'cn-a' || input.instrumentType !== 'stock') errors.push('real-readonly.identity')
  if (typeof input.symbol !== 'string' || !/^\d{6}$/.test(input.symbol)) errors.push('real-readonly.symbol')
  if (typeof input.instrumentName !== 'string' || input.instrumentName.length < 1 || input.instrumentName.length > 40) errors.push('real-readonly.instrument-name')
  if (typeof input.tradeDate !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(input.tradeDate)) errors.push('real-readonly.trade-date')
  if (!isRecord(input.prices) || Object.keys(input.prices).sort().join('|') !== [...priceKeys].sort().join('|')) errors.push('real-readonly.prices')
  const p = (input.prices ?? {}) as Record<string, unknown>
  for (const f of ['open','high','low','close']) if (!finite(p[f]) || (p[f] as number) < 0) errors.push(`real-readonly.number.${f}`)
  for (const f of ['previousClose','changePercent']) if (p[f] !== null && !finite(p[f])) errors.push(`real-readonly.number.${f}`)
  if (!finite(input.volume) || (input.volume as number) < 0 || !finite(input.amount) || (input.amount as number) < 0) errors.push('real-readonly.volume-amount')
  if (finite(p.high) && finite(p.low) && finite(p.close) && ((p.high as number) < (p.low as number) || (p.close as number) < (p.low as number) || (p.close as number) > (p.high as number))) errors.push('real-readonly.price-range')
  if (input.delayed !== true || input.readOnly !== true || input.redacted !== true) errors.push('real-readonly.flags')
  if (errors.length) return { status: 'blocked', errors: [...new Set(errors)] }
  return { status: 'passed', candidate: Object.freeze({ ...(input as PublicMarketReadonlyCandidate), prices: Object.freeze({ ...(input.prices as PublicMarketReadonlyCandidate['prices']) }) }) }
}
export type RealReadonlyResult = { status: 'disabled'|'completed-real-readonly'|'completed-mock-only-fallback'|'blocked'; normalizedInput?: RealDailyReportDryRunInput; errors?: readonly string[]; warnings?: readonly string[]; providerAttempted: boolean; realDataUsed: boolean; fallbackUsed: boolean }
