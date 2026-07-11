import { createMockOnlyPreviewModel } from '../preview/mockOnlyPreviewModel'

const ROOT_ID = 'mock-only-preview-root'
const PREVIEW_OPTIONS = {
  mode: 'mock',
  source: 'local_preview_only',
} as const

export interface MockOnlyPreviewEntryRenderResult {
  readonly safetyBannerCount: number
  readonly sectionCount: number
}

const appendTextElement = (parent: HTMLElement, tagName: string, text: string): HTMLElement => {
  const element = document.createElement(tagName)
  element.textContent = text
  parent.appendChild(element)
  return element
}

export const renderMockOnlyPreviewEntry = (root: HTMLElement): MockOnlyPreviewEntryRenderResult => {
  const model = createMockOnlyPreviewModel(PREVIEW_OPTIONS)

  const container = document.createElement('section')
  appendTextElement(container, 'h2', 'MOCK ONLY PREVIEW ENTRY')

  const bannerList = document.createElement('ul')
  for (const banner of model.safetyBanner) {
    appendTextElement(bannerList, 'li', banner)
  }
  container.appendChild(bannerList)

  const sectionList = document.createElement('ol')
  for (const section of model.sections) {
    appendTextElement(sectionList, 'li', section.title)
  }
  container.appendChild(sectionList)

  root.appendChild(container)

  return {
    safetyBannerCount: model.safetyBanner.length,
    sectionCount: model.sections.length,
  }
}

const root = document.getElementById(ROOT_ID)

if (!root) {
  throw new Error(`Mock-only preview root element #${ROOT_ID} was not found.`)
}

renderMockOnlyPreviewEntry(root)
