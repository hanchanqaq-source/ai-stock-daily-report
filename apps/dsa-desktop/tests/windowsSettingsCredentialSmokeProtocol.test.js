const test = require('node:test');
const assert = require('node:assert/strict');
const { ERROR_CODES, makeResult, parseResult, validateResult } = require('../scripts/windowsSettingsCredentialSmokeProtocol');

test('settings credential smoke result accepts fixed low-sensitivity success payload', () => {
  const result = makeResult('set', { success: true, settingsPageSet: true, plaintextNotReturned: true, mockBackendSecretLeakFree: true });
  assert.deepEqual(validateResult(result, 'set'), result);
});

test('settings credential smoke result rejects forbidden diagnostic keys', () => {
  const result = { ...makeResult('set', { success: true, settingsPageSet: true }), path: 'C:/sensitive' };
  assert.equal(validateResult(result, 'set').errorCode, ERROR_CODES.INVALID_RESULT);
});

test('settings credential smoke parser requires exactly one JSON result line', () => {
  const parsed = parseResult(`${JSON.stringify(makeResult('set', { success: true, settingsPageSet: true }))}\nextra\n`, 'set');
  assert.equal(parsed.errorCode, ERROR_CODES.INVALID_RESULT);
});
