export type MockFixtureName =
  | 'auth'
  | 'dashboard'
  | 'analysis'
  | 'history'
  | 'portfolio'
  | 'alerts'
  | 'systemConfig'
  | 'agent'
  | 'alphasift'
  | 'usage'
  | 'backtest'
  | 'decisionSignals'
  | 'stocksImport'
  | 'errors'
  | 'emptyStates'

export type MockScenarioName = 'default' | string

export interface MockFixtureCatalogEntry {
  readonly moduleName: MockFixtureName
  readonly fixtureFile: string
  readonly scenarios: readonly MockScenarioName[]
}

export type MockFixtureCatalog = Record<MockFixtureName, MockFixtureCatalogEntry>

export interface MockResponse<TFixture = unknown> {
  readonly moduleName: MockFixtureName
  readonly scenarioName: MockScenarioName
  readonly fixture: TFixture
}
