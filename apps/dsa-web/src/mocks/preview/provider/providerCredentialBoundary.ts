export type ProviderCredentialBoundaryStatus = 'not-configured' | 'unavailable' | 'blocked'

export interface ProviderCredentialBoundaryResult {
  readonly status: ProviderCredentialBoundaryStatus
  readonly hasCredential: false
  readonly secretMaterialAccessible: false
  readonly environmentReadAllowed: false
  readonly storageReadAllowed: false
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
}

export const inspectProviderCredentialBoundary = (): ProviderCredentialBoundaryResult =>
  Object.freeze({
    status: 'not-configured',
    hasCredential: false,
    secretMaterialAccessible: false,
    environmentReadAllowed: false,
    storageReadAllowed: false,
    errors: Object.freeze([]),
    warnings: Object.freeze([]),
  })
