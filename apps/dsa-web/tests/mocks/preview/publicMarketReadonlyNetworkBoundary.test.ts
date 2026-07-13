import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readonlyPortPath = 'src/mocks/preview/provider-real-readonly/providerPublicMarketReadonlyPort.ts'
const source = () => readFileSync(readonlyPortPath, 'utf-8')

describe('real public market readonly network boundary', () => {
  it('contains only the fixed 127.0.0.1 dry-run endpoint as network address', () => {
    const text = source()
    expect(text.match(/http:\/\/127\.0\.0\.1:8000\/api\/v1\/provider-readonly\/akshare\/dry-run/g)).toHaveLength(1)
    expect(text).not.toMatch(/localhost|0\.0\.0\.0|192\.168\.|\b10\.\d+\.|172\.(1[6-9]|2\d|3[01])\.|https?:\/\/(?!127\.0\.0\.1:8000\/api\/v1\/provider-readonly\/akshare\/dry-run)|wss?:\/\//)
  })

  it('does not contain dynamic endpoints, credentials, account, trading, or notification markers', () => {
    const text = source()
    for (const pattern of [/axios\b/, /EventSource\b/, /sendBeacon\b/, /import\.meta\.env/, /process\.env/, /token/i, /api[_-]?key/i, /Authorization/i, /Cookie/i, /accountId/i, /accountNumber/i, /tradingEndpoint/i, /notificationEndpoint/i]) {
      expect(text, `${readonlyPortPath} must not contain ${pattern}`).not.toMatch(pattern)
    }
    for (const allowed of [/\bfetch\b/, /AbortController/, /setTimeout/, /clearTimeout/]) {
      expect(text).toMatch(allowed)
    }
  })
})
