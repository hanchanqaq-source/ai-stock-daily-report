import type { DailyReportViewModel, MockOnlyDailyReportFixture } from '../mockOnlyPreviewTypes'

export const adaptMockOnlyDailyReportFixture = (
  fixture: MockOnlyDailyReportFixture,
): DailyReportViewModel => Object.freeze({
  id: fixture.reportId,
  projectName: fixture.projectName,
  reportDateLabel: fixture.reportDateLabel,
  title: fixture.title,
  displayName: fixture.displayName,
  modeLabel: fixture.modeLabel,
  dataSourceLabel: fixture.dataSourceLabel,
  generatedAtLabel: fixture.generatedAtLabel,
  deliveryStatus: fixture.deliveryStatus,
  marketMood: fixture.marketMood,
  headline: fixture.headline,
  portfolioAction: fixture.portfolioAction,
  riskLevel: fixture.riskLevel,
  sections: Object.freeze([
    Object.freeze({ ...fixture.sections.marketOverview }),
    Object.freeze({ ...fixture.sections.portfolioObservation }),
    Object.freeze({ ...fixture.sections.riskWarnings }),
    Object.freeze({ ...fixture.sections.actionSuggestions }),
  ]),
  safetyLabels: Object.freeze([...fixture.safetyLabels]),
  redactionLabels: Object.freeze([...fixture.redactionLabels]),
  notes: Object.freeze([...fixture.mockOnlyNotes]),
})
