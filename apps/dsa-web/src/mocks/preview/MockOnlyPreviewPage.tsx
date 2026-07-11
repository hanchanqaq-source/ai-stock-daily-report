import { createMockOnlyPreviewModel } from './mockOnlyPreviewModel'
import type { MockOnlyPreviewOptions } from './mockOnlyPreviewTypes'

const DEFAULT_OPTIONS: MockOnlyPreviewOptions = {
  mode: 'mock',
  source: 'local_preview_only',
}

export const MockOnlyPreviewPage = ({ options = DEFAULT_OPTIONS }: { readonly options?: MockOnlyPreviewOptions }) => {
  const model = createMockOnlyPreviewModel(options)

  return (
    <main aria-label="Mock-only local preview draft">
      <header>
        <h1>MOCK ONLY · LOCAL PREVIEW ONLY</h1>
        <p>REDACTED FIXTURE DATA · NO REAL NETWORK · NO REAL ACCOUNT · NO NOTIFICATION</p>
      </header>
      <section aria-label="Safety banner">
        {model.safetyBanner.map((label) => (
          <strong key={label}>{label}</strong>
        ))}
      </section>
      {model.sections.map((section) => (
        <section key={section.id} aria-label={section.title}>
          <h2>{section.title}</h2>
          <p>{section.description}</p>
        </section>
      ))}
    </main>
  )
}
