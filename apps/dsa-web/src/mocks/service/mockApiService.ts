import {
  getMockFixtureCatalog,
  getMockResponse,
  loadMockFixture,
} from '../adapter/mockApiAdapter'
import type { MockFixtureCatalog, MockFixtureName, MockResponse, MockScenarioName } from '../adapter/mockApiTypes'
import { assertMockOnlyMode, assertNoRealNetworkTarget } from '../safety/mockOnlySafety'
import type {
  MockApiService,
  MockApiServiceOptions,
  MockApiServiceReadyState,
} from './mockApiServiceTypes'

const MOCK_SERVICE_SOURCE = 'local_preview_only' as const

const getCatalog = (): MockFixtureCatalog => getMockFixtureCatalog()

const assertKnownMockModule = (moduleName: MockFixtureName): void => {
  const catalog = getCatalog()

  if (!Object.prototype.hasOwnProperty.call(catalog, moduleName)) {
    throw new Error(`Unknown mock module: ${String(moduleName)}`)
  }
}

export const assertMockServiceReady = (options: MockApiServiceOptions): MockApiServiceReadyState => {
  assertMockOnlyMode(options.mode)

  if (options.source !== MOCK_SERVICE_SOURCE) {
    throw new Error('Mock service requires the local preview source.')
  }

  assertNoRealNetworkTarget(options.source)

  return {
    ready: true,
    source: options.source,
  }
}

export const listMockModules = (options: MockApiServiceOptions): readonly MockFixtureName[] => {
  assertMockServiceReady(options)

  return Object.freeze(Object.keys(getCatalog()) as MockFixtureName[])
}

export const getMockModule = <TFixture = unknown>(
  options: MockApiServiceOptions,
  moduleName: MockFixtureName,
): TFixture => {
  assertMockServiceReady(options)
  assertNoRealNetworkTarget(`mock:${moduleName}`)
  assertKnownMockModule(moduleName)

  return loadMockFixture<TFixture>(moduleName)
}

export const getMockScenario = <TFixture = unknown>(
  options: MockApiServiceOptions,
  moduleName: MockFixtureName,
  scenarioName: MockScenarioName = 'default',
): MockResponse<TFixture> => {
  assertMockServiceReady(options)
  assertNoRealNetworkTarget(`mock:${moduleName}`)
  assertKnownMockModule(moduleName)

  return getMockResponse<TFixture>(moduleName, scenarioName)
}

export const createMockApiService = (options: MockApiServiceOptions): MockApiService => {
  assertMockServiceReady(options)

  return Object.freeze({
    options,
    assertReady: () => assertMockServiceReady(options),
    listMockModules: () => listMockModules(options),
    getMockModule: <TFixture = unknown>(moduleName: MockFixtureName) => getMockModule<TFixture>(options, moduleName),
    getMockScenario: <TFixture = unknown>(moduleName: MockFixtureName, scenarioName?: MockScenarioName) =>
      getMockScenario<TFixture>(options, moduleName, scenarioName),
  })
}
