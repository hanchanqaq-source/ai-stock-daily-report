const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createChildEnvironment, findPort, makeConfig, printSummary, resolveChildSmokeTempLocalAppData, runSmoke } = require('../scripts/windowsSettingsCredentialSmokeController');

test('settings credential smoke skips non-Windows without creating secrets', async () => {
  const summary = await runSmoke({ platform: 'linux' });
  assert.equal(summary.success, false);
  assert.equal(summary.errorCode, 'unsupported_platform');
  assert.equal(summary.cleanupPassed, true);
});

test('settings credential smoke config never lets the mock backend manufacture configured state', () => {
  const config = makeConfig(true);
  assert.equal(config.items.length, 1);
  assert.equal(config.items[0].key, 'APP_M423B1_TEST_TOKEN');
  assert.equal(config.items[0].schema.is_sensitive, true);
  assert.equal(config.items[0].value, '');
  assert.equal(config.items[0].raw_value_exists, false);
  assert.equal(config.items[0].is_masked, false);
});

test('settings credential smoke child environment overrides real LOCALAPPDATA', () => {
  const env = createChildEnvironment(
    { phase: 'set', port: 8000, tempLocalAppData: 'C:\\Temp\\dsa-secure-credential-smoke-unit', testValue: 'fake-unit-value' },
    { LOCALAPPDATA: 'C:\\Users\\real-user\\AppData\\Local', ELECTRON_RUN_AS_NODE: '1' },
  );
  assert.equal(env.LOCALAPPDATA, 'C:\\Temp\\dsa-secure-credential-smoke-unit');
  assert.equal(env.DSA_SETTINGS_CREDENTIAL_SMOKE_LOCALAPPDATA, 'C:\\Temp\\dsa-secure-credential-smoke-unit');
  assert.equal(env.ELECTRON_RUN_AS_NODE, undefined);
});


test('settings credential smoke child temp resolver accepts overridden LOCALAPPDATA smoke directory', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-secure-credential-smoke-unit-'));
  try {
    assert.equal(
      resolveChildSmokeTempLocalAppData(tempDir, { LOCALAPPDATA: tempDir }),
      fs.realpathSync(tempDir),
    );
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});

test('settings credential smoke child temp resolver rejects mismatched env variables', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-secure-credential-smoke-unit-'));
  const otherTempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-secure-credential-smoke-unit-'));
  try {
    assert.equal(resolveChildSmokeTempLocalAppData(tempDir, { LOCALAPPDATA: otherTempDir }), null);
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
    fs.rmSync(otherTempDir, { recursive: true, force: true });
  }
});

test('settings credential smoke child temp resolver rejects non-temp or wrong-prefix directories', () => {
  const wrongPrefix = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-wrong-prefix-'));
  try {
    assert.equal(resolveChildSmokeTempLocalAppData(wrongPrefix, { LOCALAPPDATA: wrongPrefix }), null);
    assert.equal(resolveChildSmokeTempLocalAppData(path.resolve('/not-temp/dsa-secure-credential-smoke-unit'), { LOCALAPPDATA: path.resolve('/not-temp/dsa-secure-credential-smoke-unit') }), null);
  } finally {
    fs.rmSync(wrongPrefix, { recursive: true, force: true });
  }
});

test('settings credential smoke port finder uses desktop trusted range', async () => {
  const port = await findPort();
  assert.ok(port >= 8000 && port <= 8100);
});

test('settings credential smoke summary prints required PASS labels', () => {
  const lines = [];
  const originalLog = console.log;
  console.log = (line) => lines.push(line);
  try {
    printSummary({
      success: true,
      cleanupPassed: true,
      errorCode: null,
      stages: [
        { phase: 'set', settingsPageSet: true, mockBackendSecretLeakFree: true },
        { phase: 'restart-read-clear', restartConfiguredState: true, plaintextNotReturned: true, settingsPageClear: true, mockBackendSecretLeakFree: true },
      ],
    });
  } finally {
    console.log = originalLog;
  }
  assert.ok(lines.includes('Settings page set: PASS'));
  assert.ok(lines.includes('Restart configured state: PASS'));
  assert.ok(lines.includes('Plaintext not returned: PASS'));
  assert.ok(lines.includes('Settings page clear: PASS'));
  assert.ok(lines.includes('Mock backend secret leak check: PASS'));
  assert.ok(lines.includes('Temp cleanup: PASS'));
  assert.ok(lines.includes('App-M4.2.3B.1 PASS'));
});
