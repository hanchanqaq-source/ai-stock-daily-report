import type { ProviderReadonlyPortResult, ProviderReadonlyRequest } from './providerReadonlyTypes'

export interface ProviderReadonlyPort {
  readonly mode: 'local-dry-run'
  readonly providerLabel: 'REDACTED_PROVIDER_LABEL'
  readonly networkEnabled: false
  readonly credentialReadEnabled: false
  readonly accountReadEnabled: false

  readCandidate(request: ProviderReadonlyRequest): Promise<ProviderReadonlyPortResult>
}
