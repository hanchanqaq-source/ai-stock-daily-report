import { describe, expect, it, vi, afterEach } from 'vitest'
import { runPublicMarketReadonlyDryRun, PUBLIC_MARKET_READONLY_ENDPOINT, PUBLIC_MARKET_READONLY_TIMEOUT_MS } from '../../../src/mocks/preview/provider-real-readonly/providerPublicMarketReadonlyPort'
import { validatePublicMarketReadonlyCandidate } from '../../../src/mocks/preview/provider-real-readonly/publicMarketReadonlyCandidateValidator'
import { normalizePublicMarketReadonlyCandidateToDryRunInput } from '../../../src/mocks/preview/provider-real-readonly/publicMarketReadonlyNormalizer'
import { validateRealDailyReportDryRunInput } from '../../../src/mocks/preview/dry-run/realDailyReportDryRunValidator'

const snapshot={ schemaVersion:'core-m3.public-market-readonly.v1', sourceType:'real-readonly', providerLabel:'REDACTED_PROVIDER_LABEL', market:'cn-a', instrumentType:'stock', symbol:'600519', instrumentName:'贵州茅台', tradeDate:'2026-07-13', open:10, high:12, low:9, close:11, previousClose:10, changePercent:10, volume:100, amount:1000, delayed:true, readOnly:true, redacted:true }
const candidate={ contractVersion:'core-m3.public-market-readonly.v1', sourceType:'real-readonly', providerLabel:'REDACTED_PROVIDER_LABEL', market:'cn-a', instrumentType:'stock', symbol:'600519', instrumentName:'贵州茅台', tradeDate:'2026-07-13', prices:{open:10,high:12,low:9,close:11,previousClose:10,changePercent:10}, volume:100, amount:1000, delayed:true, readOnly:true, redacted:true } as const

describe('Core-M3 public market readonly dry-run', () => {
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

  it('does not fetch or create timers when disabled or unapproved', async () => {
    const fetchImpl=vi.fn()
    const timerSpy=vi.spyOn(globalThis, 'setTimeout')
    expect((await runPublicMarketReadonlyDryRun({enabled:false, humanApproved:true, symbol:'600519', fetchImpl})).status).toBe('disabled')
    expect((await runPublicMarketReadonlyDryRun({enabled:true, humanApproved:false, symbol:'600519', fetchImpl})).status).toBe('blocked')
    expect(fetchImpl).not.toHaveBeenCalled()
    expect(timerSpy).not.toHaveBeenCalled()
  })

  it('uses only fixed 127.0.0.1 endpoint, sends AbortSignal, and normalizes real-readonly input', async () => {
    const fetchImpl=vi.fn(async () =>({ok:true,json:async()=>({status:'completed-real-readonly',snapshot})}))
    const result=await runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl})
    expect(fetchImpl.mock.calls[0][0]).toBe(PUBLIC_MARKET_READONLY_ENDPOINT)
    expect(PUBLIC_MARKET_READONLY_ENDPOINT).toBe('http://127.0.0.1:8000/api/v1/provider-readonly/akshare/dry-run')
    expect(fetchImpl.mock.calls[0][1]?.redirect).toBe('error')
    expect(fetchImpl.mock.calls[0][1]?.signal).toBeInstanceOf(AbortSignal)
    expect(result.status).toBe('completed-real-readonly')
    expect(result.realDataUsed).toBe(true)
    expect(result.normalizedInput?.source.sourceType).toBe('real-readonly')
    expect(result.normalizedInput?.source.isMock).toBe(false)
    expect(result.normalizedInput?.source.isRealReadOnly).toBe(true)
    expect(validateRealDailyReportDryRunInput(result.normalizedInput!).status).toBe('passed')
  })

  it('does not allow callers to override endpoint or timeout', async () => {
    const fetchImpl=vi.fn(async () =>({ok:true,json:async()=>({status:'completed-real-readonly',snapshot})}))
    await runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl, endpoint:'http://evil.test', timeoutMs:1} as never)
    expect(fetchImpl.mock.calls[0][0]).toBe(PUBLIC_MARKET_READONLY_ENDPOINT)
    expect(PUBLIC_MARKET_READONLY_TIMEOUT_MS).toBe(12000)
  })

  it('front-end AbortController timeout falls back to mock-only and clears timer', async () => {
    vi.useFakeTimers()
    const clearSpy=vi.spyOn(globalThis, 'clearTimeout')
    const fetchImpl=vi.fn((_url, init) => new Promise((_resolve, reject) => {
      ;(init?.signal as AbortSignal).addEventListener('abort', () => reject(new DOMException('local timeout detail', 'AbortError')))
    }) as Promise<Response>)
    const promise=runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl})
    await vi.advanceTimersByTimeAsync(PUBLIC_MARKET_READONLY_TIMEOUT_MS)
    const result=await promise
    expect(result.status).toBe('completed-mock-only-fallback')
    expect(result.warnings).toEqual(['real-readonly.timeout'])
    expect(result.normalizedInput?.source.sourceType).toBe('mock-only')
    expect(result.realDataUsed).toBe(false)
    expect(result.fallbackUsed).toBe(true)
    expect(clearSpy).toHaveBeenCalled()
  })

  it('backend timeout status also falls back to mock-only timeout warning', async () => {
    const fetchImpl=vi.fn(async()=>({ok:true,json:async()=>({status:'timeout',errorCode:'real-readonly.provider-timeout'})}))
    const result=await runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl})
    expect(result.status).toBe('completed-mock-only-fallback')
    expect(result.warnings).toEqual(['real-readonly.timeout'])
    expect(result.normalizedInput?.source.sourceType).toBe('mock-only')
    expect(result.realDataUsed).toBe(false)
  })

  it('ordinary fetch errors stay blocked without leaking exception text', async () => {
    const fetchImpl=vi.fn(async()=>{ throw new Error('secret token traceback /tmp/path') })
    const result=await runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl})
    expect(result).toEqual({ status:'blocked', providerAttempted:true, realDataUsed:false, fallbackUsed:false, errors:['real-readonly.fetch-blocked'] })
    expect(JSON.stringify(result)).not.toMatch(/secret|traceback|\/tmp/)
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

  it('keeps invalid responses blocked without normalized input', async () => {
    const invalid=vi.fn(async()=>({ok:true,json:async()=>({status:'invalid-response',errorCode:'real-readonly.invalid-number'})}))
    const blocked=await runPublicMarketReadonlyDryRun({enabled:true,humanApproved:true,symbol:'600519',fetchImpl:invalid})
    expect(blocked.status).toBe('blocked')
    expect(blocked.errors).toEqual(['real-readonly.invalid-response'])
    expect(blocked).not.toHaveProperty('normalizedInput')
  })
})
