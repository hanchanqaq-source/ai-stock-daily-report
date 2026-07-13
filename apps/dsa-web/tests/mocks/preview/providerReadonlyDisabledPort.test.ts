import { describe, expect, it, vi } from 'vitest'
import { DEFAULT_PROVIDER_READONLY_REQUEST } from '../../../src/mocks/preview/provider/providerReadonlyTypes'
import { createDisabledProviderReadonlyPort } from '../../../src/mocks/preview/provider/providerReadonlyDisabledPort'

describe('disabled readonly provider port', () => {
  it('exposes only safe disabled properties and returns frozen unavailable results', async () => {
    const port = createDisabledProviderReadonlyPort()
    expect(Object.isFrozen(port)).toBe(true)
    expect(port).toMatchObject({ mode: 'local-dry-run', providerLabel: 'REDACTED_PROVIDER_LABEL', networkEnabled: false, credentialReadEnabled: false, accountReadEnabled: false })
    const result = await port.readCandidate(DEFAULT_PROVIDER_READONLY_REQUEST)
    expect(result).toMatchObject({ status: 'unavailable', errors: ['provider-readonly.unavailable'], fallbackMode: 'mock-only', canFallbackToMockOnly: true })
    expect(result).not.toHaveProperty('candidate')
    expect(Object.isFrozen(result)).toBe(true)
    expect(Object.isFrozen(result.errors)).toBe(true)
    await expect(port.readCandidate(DEFAULT_PROVIDER_READONLY_REQUEST)).resolves.toEqual(result)
  })

  it('does not read request getters or use network, storage, environment, time, or random APIs', async () => {
    const getter = vi.fn(() => 'dry-run')
    const request = Object.defineProperty({}, 'mode', { get: getter }) as never
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    vi.stubGlobal('localStorage', { getItem: vi.fn() })
    const envSpy = vi.spyOn(process, 'env', 'get')
    const nowSpy = vi.spyOn(Date, 'now')
    const randomSpy = vi.spyOn(Math, 'random')
    await createDisabledProviderReadonlyPort().readCandidate(request)
    expect(getter).not.toHaveBeenCalled()
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(envSpy).not.toHaveBeenCalled()
    expect(nowSpy).not.toHaveBeenCalled()
    expect(randomSpy).not.toHaveBeenCalled()
  })
})
