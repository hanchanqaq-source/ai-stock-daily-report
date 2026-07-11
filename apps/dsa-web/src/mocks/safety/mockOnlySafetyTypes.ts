export type MockOnlyMode = string | boolean | null | undefined

export type MockOnlyRequestTargetInspection = {
  target: string
  allowed: boolean
  reason: string
  matchedMarker?: string
}
