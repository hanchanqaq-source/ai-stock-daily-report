import type { MockApiServiceOptions } from '../service/mockApiServiceTypes'

export type MockOnlyPreviewOptions = MockApiServiceOptions & {
  readonly mode: 'mock'
  readonly source: 'local_preview_only'
}

export type MockOnlyPreviewSectionId =
  | 'safety-banner'
  | 'dashboard-summary'
  | 'portfolio-preview'
  | 'history-reports-preview'
  | 'alerts-preview'
  | 'agent-chat-preview'
  | 'empty-error-examples'
  | 'local-settings-import-export'

export interface MockOnlyPreviewMetadata {
  readonly mode: 'mock'
  readonly source: 'local_preview_only'
  readonly containsRealData: false
  readonly containsSecrets: false
  readonly safeForWindowsPreview: true
}

export interface MockOnlyPreviewSection<TData = unknown> {
  readonly id: MockOnlyPreviewSectionId
  readonly title: string
  readonly description: string
  readonly data: TData
}

export interface MockOnlyPreviewModel {
  readonly metadata: MockOnlyPreviewMetadata
  readonly safetyBanner: readonly string[]
  readonly sections: readonly MockOnlyPreviewSection[]
}
