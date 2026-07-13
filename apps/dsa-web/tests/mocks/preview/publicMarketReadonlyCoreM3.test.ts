import { describe, expect, it, vi } from 'vitest'
import { runPublicMarketReadonlyDryRun, PUBLIC_MARKET_READONLY_ENDPOINT } from '../../../src/mocks/preview/provider-real-readonly/providerPublicMarketReadonlyPort'
import { validatePublicMarketReadonlyCandidate } from '../../../src/mocks/preview/provider-real-readonly/publicMarketReadonlyCandidateValidator'
import { normalizePublicMarketReadonlyCandidateToDryRunInput } from '../../../src/mocks/preview/provider-real-readonly/publicMarketReadonlyNormalizer'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'

const snapshot={ schemaVersion:'core-m3.public-market-readonly.v1', sourceType:'real-readonly', providerLabel:'REDACTED_PROVIDER_LABEL', market:'cn-a', instrumentType:'stock', symbol:'600519', instrumentName:'贵州茅台', tradeDate:'2026-07-13', open:10, high:12, low:9, close:11, previousClose:10, changePercent:10, volume:100, amount:1000, delayed:true, readOnly:true, redacted:true }
const candidate={ contractVersion:'core-m3.public-market-readonly.v1', sourceType:'real-readonly', providerLabel:'REDACTED_PROVIDER_LABEL', market:'cn-a', instrumentType:'stock', symbol:'600519', instrumentName:'贵州茅台', tradeDate:'2026-07-13', prices:{open:10,high:12,low:9,close:11,previousClose:10,changePercent:10}, volume:100, amount:1000, delayed:true, readOnly:true, redacted:true } as const

describe('Core-M3 public market readonly dry-run', () => {
  it('does not fetch when disabled or unapproved', async () => {
    const fetchImpl=vi.fn()
    expect((await runPublicMarketReadonlyDryRun({enabled:false, humanApproved:true, symbol:'600519', fetchImpl})).status).toBe('disabled')
    expect((await runPublicMarketReadonlyDryRun({enabled:true, humanApproved:false, symbol:'600519', fetchImpl})).status).toBe('blocked')
    expect(fetchImpl).not.toHaveBeenCalled()
  })
  it('uses only 127.0.0.1 endpoint and normalizes real-readonly input', async () => {
    const fetchImpl=vi.fn(async () =>({ok:true,json:async()=>({status:'completed-real-readonly',snapshot})}))
    const result=await runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl})
    expect(fetchImpl.mock.calls[0][0]).toBe(PUBLIC_MARKET_READONLY_ENDPOINT)
    expect(PUBLIC_MARKET_READONLY_ENDPOINT).toMatch(/^http:\/\/127\.0\.0\.1:8000\/api\/v1\/provider-readonly\/akshare\/dry-run$/)
    expect(result.status).toBe('completed-real-readonly')
    expect(result.normalizedInput?.source.sourceType).toBe('real-readonly')
    expect(result.normalizedInput?.source.isMock).toBe(false)
    expect(result.normalizedInput?.source.isRealReadOnly).toBe(true)
    expect(validateRealDailyReportDryRunInput(result.normalizedInput!).status).toBe('passed')
  })
  it('blocks unknown fields/provider drift/bad numbers and preserves input', () => {
    const original=structuredClone(candidate)
    expect(validatePublicMarketReadonlyCandidate({...candidate, rawResponse:{}}).status).toBe('blocked')
    expect(validatePublicMarketReadonlyCandidate({...candidate, providerLabel:'X'}).status).toBe('blocked')
    expect(validatePublicMarketReadonlyCandidate({...candidate, prices:{...candidate.prices, close:99}}).status).toBe('blocked')
    expect(candidate).toEqual(original)
  })
  it('normalizer keeps all safety switches false and does not create a view model', () => {
    const result=normalizePublicMarketReadonlyCandidateToDryRunInput(candidate)
    expect(result.status).toBe('completed-real-readonly')
    if (result.status === 'completed-real-readonly') {
      expect(result.normalizedInput.safety.allowRealProvider).toBe(false)
      expect(result.normalizedInput.safety.allowRealAccountRead).toBe(false)
      expect(result.normalizedInput.safety.allowNotificationSend).toBe(false)
      expect(result.normalizedInput.safety.allowTrading).toBe(false)
      expect(result.normalizedInput.safety.allowAiCall).toBe(false)
      expect('viewModel' in result).toBe(false)
    }
  })
  it('falls back only on unavailable/timeout and blocks invalid responses', async () => {
    const unavailable=vi.fn(async()=>({ok:true,json:async()=>({status:'timeout',errorCode:'real-readonly.provider-timeout'})}))
    expect((await runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl:unavailable})).status).toBe('completed-mock-only-fallback')
    const invalid=vi.fn(async()=>({ok:true,json:async()=>({status:'invalid-response',errorCode:'real-readonly.invalid-number'})}))
    const blocked=await runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl:invalid})
    expect(blocked.status).toBe('blocked')
    expect(blocked).not.toHaveProperty('normalizedInput')
  })
})
