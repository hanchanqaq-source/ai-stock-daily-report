import type { MockFixtureName, MockResponse, MockScenarioName } from '../adapter/mockApiTypes'
import type { MockOnlyMode } from '../safety/mockOnlySafetyTypes'

export type MockApiServiceSource = 'local_preview_only'

export interface MockApiServiceOptions {
  readonly mode: MockOnlyMode
  readonly source: MockApiServiceSource
}

export interface MockApiServiceReadyState {
  readonly ready: true
  readonly source: MockApiServiceSource
}

export interface MockApiService {
  readonly options: MockApiServiceOptions
  readonly assertReady: () => MockApiServiceReadyState
  readonly listMockModules: () => readonly MockFixtureName[]
  readonly getMockModule: <TFixture = unknown>(moduleName: MockFixtureName) => TFixture
  readonly getMockScenario: <TFixture = unknown>(
    moduleName: MockFixtureName,
    scenarioName?: MockScenarioName,
  ) => MockResponse<TFixture>
}

export type MockApiClient = MockApiService
