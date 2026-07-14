const RESULT_KEYS = Object.freeze([
  'phase',
  'success',
  'settingsPageSet',
  'restartConfiguredState',
  'plaintextNotReturned',
  'settingsPageClear',
  'mockBackendSecretLeakFree',
  'errorCode',
]);

const ERROR_CODES = Object.freeze({
  UNSUPPORTED_PLATFORM: 'unsupported_platform',
  INVALID_RESULT: 'invalid_result',
  CHILD_PROCESS_FAILED: 'child_process_failed',
  CHILD_PROCESS_TIMEOUT: 'child_process_timeout',
  TEMP_DIRECTORY_FAILED: 'temp_directory_failed',
  CLEANUP_FAILED: 'cleanup_failed',
  WEB_DIST_MISSING: 'web_dist_missing',
  PORT_UNAVAILABLE: 'port_unavailable',
  MOCK_SERVER_FAILED: 'mock_server_failed',
  ELECTRON_RESOLVE_FAILED: 'electron_resolve_failed',
  PAGE_LOAD_FAILED: 'page_load_failed',
  INITIAL_NAVIGATION_FAILED: 'initial_navigation_failed',
  SETTINGS_NAVIGATION_FAILED: 'settings_navigation_failed',
  DESKTOP_BRIDGE_UNAVAILABLE: 'desktop_bridge_unavailable',
  SETTINGS_FIELD_TIMEOUT: 'settings_field_timeout',
  PAGE_AUTOMATION_FAILED: 'page_automation_failed',
  PAGE_SET_FAILED: 'page_set_failed',
  RESTART_CONFIGURED_FAILED: 'restart_configured_failed',
  PLAINTEXT_RETURNED: 'plaintext_returned',
  PAGE_CLEAR_FAILED: 'page_clear_failed',
  MOCK_BACKEND_SECRET_LEAK: 'mock_backend_secret_leak',
});

const ALLOWED_ERROR_CODES = new Set(Object.values(ERROR_CODES));
const FORBIDDEN_KEYS = new Set([
  'value', 'plaintext', 'plainText', 'testValue', 'secret', 'token', 'apiKey', 'password',
  'path', 'localAppData', 'env', 'stack', 'storePath', 'ciphertext', 'encrypted',
]);

function makeResult(phase, fields = {}) {
  return {
    phase,
    success: Boolean(fields.success),
    settingsPageSet: Boolean(fields.settingsPageSet),
    restartConfiguredState: Boolean(fields.restartConfiguredState),
    plaintextNotReturned: Boolean(fields.plaintextNotReturned),
    settingsPageClear: Boolean(fields.settingsPageClear),
    mockBackendSecretLeakFree: Boolean(fields.mockBackendSecretLeakFree),
    errorCode: fields.errorCode || null,
  };
}

function containsForbiddenKey(value) {
  if (!value || typeof value !== 'object') return false;
  if (Array.isArray(value)) return value.some(containsForbiddenKey);
  return Object.entries(value).some(([key, nested]) => FORBIDDEN_KEYS.has(key) || containsForbiddenKey(nested));
}

function validateResult(value, expectedPhase) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || containsForbiddenKey(value)) {
    return makeResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  const actualKeys = Object.keys(value).sort();
  const expectedKeys = [...RESULT_KEYS].sort();
  if (actualKeys.length !== expectedKeys.length || actualKeys.some((key, index) => key !== expectedKeys[index])) {
    return makeResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  if (value.phase !== expectedPhase) return makeResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  for (const key of RESULT_KEYS.filter((key) => key !== 'phase' && key !== 'errorCode')) {
    if (typeof value[key] !== 'boolean') return makeResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  if (value.errorCode !== null && (!ALLOWED_ERROR_CODES.has(value.errorCode) || typeof value.errorCode !== 'string')) {
    return makeResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  if ((value.success && value.errorCode !== null) || (!value.success && value.errorCode === null)) {
    return makeResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  return makeResult(expectedPhase, value);
}

function parseResult(stdout, expectedPhase) {
  const lines = String(stdout || '').trim().split(/\r?\n/).filter(Boolean);
  if (lines.length !== 1) return makeResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  try { return validateResult(JSON.parse(lines[0]), expectedPhase); } catch (_) { return makeResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT }); }
}

module.exports = { ALLOWED_ERROR_CODES, ERROR_CODES, FORBIDDEN_KEYS, RESULT_KEYS, containsForbiddenKey, makeResult, parseResult, validateResult };
