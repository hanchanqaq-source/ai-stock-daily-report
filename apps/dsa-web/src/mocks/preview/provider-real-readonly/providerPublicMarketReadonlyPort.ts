import { MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE } from '../provider/providerCandidatePayloadFixture'
import { runProviderDryRunGate } from '../provider/providerDryRunGate'
import { normalizePublicMarketReadonlyCandidateToDryRunInput } from './publicMarketReadonlyNormalizer'
import { validatePublicMarketReadonlyCandidate, type PublicMarketReadonlyCandidate, REDACTED_PROVIDER_LABEL, type RealReadonlyResult } from './publicMarketReadonlyCandidateValidator'

const ENDPOINT = 'http://127.0.0.1:8000/api/v1/provider-readonly/akshare/dry-run' as const
export const PUBLIC_MARKET_READONLY_PORT_CAPABILITIES = Object.freeze({ mode: 'real-readonly-dry-run', networkEnabled: true, networkScope: 'localhost-only', providerLabel: REDACTED_PROVIDER_LABEL, credentialReadEnabled: false, accountReadEnabled: false, tradingEnabled: false, notificationEnabled: false, aiCallEnabled: false, persistenceEnabled: false })
export const createPublicMarketReadonlyRequest = (symbol: string, humanApproved: true) => Object.freeze({ mode: 'real-readonly-dry-run', provider: 'akshare-public-market', market: 'cn-a', instrumentType: 'stock', symbol, humanApproved, readOnly: true, allowAccountRead: false, allowTrading: false, allowNotificationSend: false, allowAiCall: false, allowPersistence: false })
const toCandidate = (snapshot: Record<string, unknown>): PublicMarketReadonlyCandidate => ({ contractVersion: 'core-m3.public-market-readonly.v1', sourceType: 'real-readonly', providerLabel: REDACTED_PROVIDER_LABEL, market: 'cn-a', instrumentType: 'stock', symbol: snapshot.symbol as string, instrumentName: snapshot.instrumentName as string, tradeDate: snapshot.tradeDate as string, prices: { open: snapshot.open as number, high: snapshot.high as number, low: snapshot.low as number, close: snapshot.close as number, previousClose: snapshot.previousClose as number | null, changePercent: snapshot.changePercent as number | null }, volume: snapshot.volume as number, amount: snapshot.amount as number, delayed: true, readOnly: true, redacted: true })
export const runPublicMarketReadonlyDryRun = async (input: { enabled?: boolean; humanApproved?: boolean; symbol: string; fetchImpl?: typeof fetch }): Promise<RealReadonlyResult> => {
  if (input.enabled !== true) return { status: 'disabled', providerAttempted: false, realDataUsed: false, fallbackUsed: false }
  if (input.humanApproved !== true || !/^\d{6}$/.test(input.symbol)) return { status: 'blocked', providerAttempted: false, realDataUsed: false, fallbackUsed: false, errors: ['real-readonly.request-blocked'] }
  try {
    const response = await (input.fetchImpl ?? fetch)(ENDPOINT, { method: 'POST', redirect: 'error', headers: { 'content-type': 'application/json' }, body: JSON.stringify(createPublicMarketReadonlyRequest(input.symbol, true)) })
    if (!response.ok) return { status: 'blocked', providerAttempted: true, realDataUsed: false, fallbackUsed: false, errors: ['real-readonly.http-error'] }
    const body = await response.json() as Record<string, unknown>
    if (body.status === 'completed-real-readonly' && typeof body.snapshot === 'object' && body.snapshot !== null) {
      const candidate = validatePublicMarketReadonlyCandidate(toCandidate(body.snapshot as Record<string, unknown>))
      if (candidate.status !== 'passed') return { status: 'blocked', providerAttempted: true, realDataUsed: false, fallbackUsed: false, errors: candidate.errors }
      const normalized = normalizePublicMarketReadonlyCandidateToDryRunInput(candidate.candidate)
      return normalized.status === 'completed-real-readonly' ? { status: 'completed-real-readonly', normalizedInput: normalized.normalizedInput, providerAttempted: true, realDataUsed: true, fallbackUsed: false } : { status: 'blocked', providerAttempted: true, realDataUsed: false, fallbackUsed: false, errors: normalized.errors }
    }
    if (body.status === 'unavailable' || body.status === 'timeout') {
      const gate = runProviderDryRunGate({ featureFlag: { enabled: true }, candidate: MOCK_ONLY_PROVIDER_CANDIDATE_PAYLOAD_FIXTURE })
      return gate.status === 'completed-mock-only' ? { status: 'completed-mock-only-fallback', normalizedInput: gate.normalizedInput, providerAttempted: true, realDataUsed: false, fallbackUsed: true, warnings: [`real-readonly.${body.status}`] } : { status: 'blocked', providerAttempted: true, realDataUsed: false, fallbackUsed: false, errors: gate.errors }
    }
    return { status: 'blocked', providerAttempted: true, realDataUsed: false, fallbackUsed: false, errors: ['real-readonly.invalid-response'] }
  } catch { return { status: 'blocked', providerAttempted: true, realDataUsed: false, fallbackUsed: false, errors: ['real-readonly.fetch-blocked'] } }
}
export const PUBLIC_MARKET_READONLY_ENDPOINT = ENDPOINT
