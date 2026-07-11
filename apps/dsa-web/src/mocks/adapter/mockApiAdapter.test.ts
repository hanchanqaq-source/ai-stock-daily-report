import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { getMockFixtureCatalog, getMockResponse, loadMockFixture } from './mockApiAdapter'

const adapterSourcePath = 'src/mocks/adapter/mockApiAdapter.ts'
const adapterSource = readFileSync(adapterSourcePath, 'utf-8')

describe('mockApiAdapter non-runtime scaffold', () => {
  it('exposes the expected local fixture catalog', () => {
    expect(getMockFixtureCatalog()).toMatchObject({
      auth: { fixtureFile: 'auth.json', scenarios: ['default'] },
      dashboard: { fixtureFile: 'dashboard.json', scenarios: ['default'] },
      analysis: { fixtureFile: 'analysis_tasks.json', scenarios: ['default'] },
      history: { fixtureFile: 'history_reports.json', scenarios: ['default'] },
      portfolio: { fixtureFile: 'portfolio.json', scenarios: ['default'] },
      alerts: { fixtureFile: 'alerts.json', scenarios: ['default'] },
      systemConfig: { fixtureFile: 'system_config.json', scenarios: ['default'] },
      agent: { fixtureFile: 'agent_chat.json', scenarios: ['default'] },
      alphasift: { fixtureFile: 'alphasift.json', scenarios: ['default'] },
      usage: { fixtureFile: 'usage.json', scenarios: ['default'] },
      backtest: { fixtureFile: 'backtest.json', scenarios: ['default'] },
      decisionSignals: { fixtureFile: 'decision_signals.json', scenarios: ['default'] },
      stocksImport: { fixtureFile: 'stocks_import.json', scenarios: ['default'] },
      errors: { fixtureFile: 'errors.json', scenarios: ['default'] },
      emptyStates: { fixtureFile: 'empty_states.json', scenarios: ['default'] },
    })
  })

  it('loads fixture data from the static fixture map', () => {
    const fixture = loadMockFixture('dashboard')
    expect(fixture).toBeTruthy()
    expect(getMockResponse('dashboard')).toEqual({
      moduleName: 'dashboard',
      scenarioName: 'default',
      fixture,
    })
  })

  it('does not contain network, environment, or secret access primitives', () => {
    expect(adapterSource).not.toMatch(/\bfetch\b/)
    expect(adapterSource).not.toMatch(/\baxios\b/)
    expect(adapterSource).not.toContain('XMLHttpRequest')
    expect(adapterSource).not.toMatch(/https?:\/\//)
    expect(adapterSource).not.toContain('127.0.0.1')
    expect(adapterSource).not.toContain('0.0.0.0')
    expect(adapterSource).not.toContain('import.meta.env')
    expect(adapterSource).not.toMatch(/VITE_[A-Z0-9_]+/)
    expect(adapterSource).not.toMatch(/token|webhook|api[_-]?key/i)
    expect(adapterSource).not.toMatch(/from ['"](?:\.\.\/)*api\//)
  })
})
