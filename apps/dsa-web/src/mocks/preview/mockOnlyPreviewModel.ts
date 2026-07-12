import { createMockApiService } from '../service/mockApiService'
import type {
  MockOnlyPreviewMetadata,
  MockOnlyPreviewModel,
  MockOnlyPreviewOptions,
  MockOnlyPreviewSection,
} from './mockOnlyPreviewTypes'

interface FixtureMetadata {
  readonly metadata?: {
    readonly mode?: string
    readonly source?: string
    readonly contains_real_data?: boolean
    readonly contains_secrets?: boolean
    readonly safe_for_windows_preview?: boolean
  }
}

const REQUIRED_OPTIONS: MockOnlyPreviewOptions = {
  mode: 'mock',
  source: 'local_preview_only',
}

const SAFETY_BANNER = Object.freeze([
  'MOCK ONLY',
  'LOCAL PREVIEW ONLY',
  'REDACTED FIXTURE DATA',
  'NO REAL NETWORK',
  'NO REAL ACCOUNT',
  'NO OUTBOUND DELIVERY',
])

const assertPreviewOptions = (options: MockOnlyPreviewOptions): void => {
  if (options.mode !== REQUIRED_OPTIONS.mode || options.source !== REQUIRED_OPTIONS.source) {
    throw new Error('Mock-only preview requires mode=mock and source=local_preview_only.')
  }
}

const getFixtureMetadata = (fixture: FixtureMetadata): MockOnlyPreviewMetadata => {
  const metadata = fixture.metadata

  if (
    metadata?.mode !== REQUIRED_OPTIONS.mode ||
    metadata.source !== REQUIRED_OPTIONS.source ||
    metadata.contains_real_data !== false ||
    metadata.contains_secrets !== false ||
    metadata.safe_for_windows_preview !== true
  ) {
    throw new Error('Mock-only preview fixture metadata is not safe for local preview.')
  }

  return {
    mode: REQUIRED_OPTIONS.mode,
    source: REQUIRED_OPTIONS.source,
    containsRealData: false,
    containsSecrets: false,
    safeForWindowsPreview: true,
  }
}

export const getMockOnlyPreviewSummary = (options: MockOnlyPreviewOptions): MockOnlyPreviewMetadata => {
  assertPreviewOptions(options)

  const service = createMockApiService(options)
  return getFixtureMetadata(service.getMockModule<FixtureMetadata>('dashboard'))
}

export const getMockOnlyPreviewSections = (
  options: MockOnlyPreviewOptions,
): readonly MockOnlyPreviewSection[] => {
  assertPreviewOptions(options)

  const service = createMockApiService(options)
  const dashboard = service.getMockModule('dashboard')
  const portfolio = service.getMockModule('portfolio')
  const history = service.getMockModule('history')
  const alerts = service.getMockModule('alerts')
  const agent = service.getMockModule('agent')
  const emptyStates = service.getMockModule('emptyStates')

  return Object.freeze([
    {
      id: 'safety-banner',
      title: 'Safety banner',
      description: 'Static mock-only labels that must remain visible in any future preview page.',
      data: SAFETY_BANNER,
    },
    {
      id: 'dashboard-summary',
      title: 'Dashboard summary',
      description: 'Dashboard cards and market status from redacted fixture data.',
      data: dashboard,
    },
    {
      id: 'portfolio-preview',
      title: 'Portfolio preview',
      description: 'Portfolio accounts, holdings, risk, and trade examples from redacted fixture data.',
      data: portfolio,
    },
    {
      id: 'history-reports-preview',
      title: 'History reports preview',
      description: 'History list and report detail examples from redacted fixture data.',
      data: history,
    },
    {
      id: 'alerts-preview',
      title: 'Alerts preview',
      description: 'Alert rule, trigger, and outbound-delivery-shaped examples from redacted fixture data.',
      data: alerts,
    },
    {
      id: 'agent-chat-preview',
      title: 'Agent chat preview',
      description: 'Agent chat sessions, messages, stream chunks, and error examples from redacted fixture data.',
      data: agent,
    },
    {
      id: 'empty-error-examples',
      title: 'Empty and error examples',
      description: 'Empty states and error-shaped examples for future preview rendering checks.',
      data: emptyStates,
    },
    {
      id: 'local-settings-import-export',
      title: 'Local settings and import/export preview',
      description: 'A static Web-P20 boundary preview. It does not read files, configuration, or secrets.',
      data: Object.freeze({
        settingsMode: 'mock_only_locked',
        importMode: 'review_only',
        exportMode: 'not_generated',
      }),
    },
  ])
}

export const createMockOnlyPreviewModel = (options: MockOnlyPreviewOptions): MockOnlyPreviewModel => {
  const metadata = getMockOnlyPreviewSummary(options)
  const sections = getMockOnlyPreviewSections(options)

  return Object.freeze({
    metadata,
    safetyBanner: SAFETY_BANNER,
    sections,
  })
}
