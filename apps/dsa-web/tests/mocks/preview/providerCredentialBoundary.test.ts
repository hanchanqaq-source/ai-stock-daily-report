import { describe, expect, it, vi } from 'vitest'
import { inspectProviderCredentialBoundary } from '../../../src/mocks/preview/provider/providerCredentialBoundary'

describe('provider credential boundary', () => {
  it('describes unavailable credentials without reading secret material', () => {
    vi.stubGlobal('localStorage', { getItem: vi.fn() })
    const envSpy = vi.spyOn(process, 'env', 'get')
    const result = inspectProviderCredentialBoundary()
    expect(result).toEqual({ status: 'not-configured', hasCredential: false, secretMaterialAccessible: false, environmentReadAllowed: false, storageReadAllowed: false, errors: [], warnings: [] })
    expect(result).not.toHaveProperty('token')
    expect(result).not.toHaveProperty('apiKey')
    expect(result).not.toHaveProperty('credentialValue')
    expect(Object.isFrozen(result)).toBe(true)
    expect(Object.isFrozen(result.errors)).toBe(true)
    expect(envSpy).not.toHaveBeenCalled()
    expect(localStorage.getItem).not.toHaveBeenCalled()
    expect(inspectProviderCredentialBoundary()).toEqual(result)
  })
})
