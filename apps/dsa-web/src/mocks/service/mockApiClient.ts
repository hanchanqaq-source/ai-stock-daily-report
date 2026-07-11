import { createMockApiService } from './mockApiService'
import type { MockApiClient, MockApiServiceOptions } from './mockApiServiceTypes'

export const createMockApiClient = (options: MockApiServiceOptions): MockApiClient => {
  return createMockApiService(options)
}
