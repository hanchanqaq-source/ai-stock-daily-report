import agentChatFixture from '../fixtures/agent_chat.json'
import alertsFixture from '../fixtures/alerts.json'
import alphasiftFixture from '../fixtures/alphasift.json'
import analysisTasksFixture from '../fixtures/analysis_tasks.json'
import authFixture from '../fixtures/auth.json'
import backtestFixture from '../fixtures/backtest.json'
import dashboardFixture from '../fixtures/dashboard.json'
import decisionSignalsFixture from '../fixtures/decision_signals.json'
import emptyStatesFixture from '../fixtures/empty_states.json'
import errorsFixture from '../fixtures/errors.json'
import historyReportsFixture from '../fixtures/history_reports.json'
import portfolioFixture from '../fixtures/portfolio.json'
import stocksImportFixture from '../fixtures/stocks_import.json'
import systemConfigFixture from '../fixtures/system_config.json'
import usageFixture from '../fixtures/usage.json'
import type {
  MockFixtureCatalog,
  MockFixtureCatalogEntry,
  MockFixtureName,
  MockResponse,
  MockScenarioName,
} from './mockApiTypes'

const DEFAULT_SCENARIO: MockScenarioName = 'default'

const mockFixtureMap = Object.freeze({
  auth: authFixture,
  dashboard: dashboardFixture,
  analysis: analysisTasksFixture,
  history: historyReportsFixture,
  portfolio: portfolioFixture,
  alerts: alertsFixture,
  systemConfig: systemConfigFixture,
  agent: agentChatFixture,
  alphasift: alphasiftFixture,
  usage: usageFixture,
  backtest: backtestFixture,
  decisionSignals: decisionSignalsFixture,
  stocksImport: stocksImportFixture,
  errors: errorsFixture,
  emptyStates: emptyStatesFixture,
} satisfies Record<MockFixtureName, unknown>)

const mockFixtureFiles = Object.freeze({
  auth: 'auth.json',
  dashboard: 'dashboard.json',
  analysis: 'analysis_tasks.json',
  history: 'history_reports.json',
  portfolio: 'portfolio.json',
  alerts: 'alerts.json',
  systemConfig: 'system_config.json',
  agent: 'agent_chat.json',
  alphasift: 'alphasift.json',
  usage: 'usage.json',
  backtest: 'backtest.json',
  decisionSignals: 'decision_signals.json',
  stocksImport: 'stocks_import.json',
  errors: 'errors.json',
  emptyStates: 'empty_states.json',
} satisfies Record<MockFixtureName, string>)

export const getMockFixtureCatalog = (): MockFixtureCatalog => {
  return Object.fromEntries(
    Object.entries(mockFixtureFiles).map(([moduleName, fixtureFile]) => [
      moduleName,
      {
        moduleName,
        fixtureFile,
        scenarios: [DEFAULT_SCENARIO],
      } satisfies MockFixtureCatalogEntry,
    ]),
  ) as MockFixtureCatalog
}

export const loadMockFixture = <TFixture = unknown>(name: MockFixtureName): TFixture => {
  return mockFixtureMap[name] as TFixture
}

export const getMockResponse = <TFixture = unknown>(
  moduleName: MockFixtureName,
  scenarioName: MockScenarioName = DEFAULT_SCENARIO,
): MockResponse<TFixture> => {
  return {
    moduleName,
    scenarioName,
    fixture: loadMockFixture<TFixture>(moduleName),
  }
}
