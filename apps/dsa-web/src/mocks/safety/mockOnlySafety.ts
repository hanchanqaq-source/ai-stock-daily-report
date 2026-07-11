import type { MockOnlyMode, MockOnlyRequestTargetInspection } from './mockOnlySafetyTypes'

const ENABLED_MOCK_ONLY_MODES = new Set(['mock', 'mock-only', 'mock_only'])

const BLOCKED_TARGET_MARKERS = [
  '/api/v1',
  'http://',
  'https://',
  '127.0.0.1',
  'localhost',
  '0.0.0.0',
  'provider',
  'backend',
  'openai',
  'litellm',
  'notification',
  'webhook',
  'daily-report',
  'formal-report',
] as const

const ALLOWED_TARGET_MARKERS = ['fixture:', 'mock:', 'mock://', 'local_preview_only'] as const

const normalizeValue = (value: string): string => value.trim().toLowerCase()

export const isMockOnlyModeEnabled = (mode: MockOnlyMode): boolean => {
  if (typeof mode !== 'string') {
    return false
  }

  return ENABLED_MOCK_ONLY_MODES.has(normalizeValue(mode))
}

export const assertMockOnlyMode = (mode: MockOnlyMode): void => {
  if (!isMockOnlyModeEnabled(mode)) {
    throw new Error('Mock-only fixture access requires an explicit mock-only mode.')
  }
}

export const inspectMockOnlyRequestTarget = (target: string): MockOnlyRequestTargetInspection => {
  const normalizedTarget = normalizeValue(target)

  const blockedMarker = BLOCKED_TARGET_MARKERS.find((marker) => normalizedTarget.includes(marker))
  if (blockedMarker) {
    return {
      target,
      allowed: false,
      reason: 'blocked_real_network_or_runtime_target',
      matchedMarker: blockedMarker,
    }
  }

  const allowedMarker = ALLOWED_TARGET_MARKERS.find((marker) => normalizedTarget.startsWith(marker))
  if (allowedMarker) {
    return {
      target,
      allowed: true,
      reason: 'allowed_mock_only_marker',
      matchedMarker: allowedMarker,
    }
  }

  if (/^[a-z][a-z0-9_-]*(?:\.json)?$/i.test(target.trim())) {
    return {
      target,
      allowed: true,
      reason: 'allowed_local_fixture_or_module_name',
    }
  }

  return {
    target,
    allowed: false,
    reason: 'blocked_unknown_target_shape',
  }
}

export const assertNoRealNetworkTarget = (target: string): void => {
  const inspection = inspectMockOnlyRequestTarget(target)

  if (!inspection.allowed) {
    throw new Error(`Mock-only mode blocks target: ${inspection.reason}`)
  }
}
