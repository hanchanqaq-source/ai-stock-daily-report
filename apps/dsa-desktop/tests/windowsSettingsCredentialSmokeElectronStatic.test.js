const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('settings credential smoke Electron driver registers IPC without loading formal main', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokeElectron.js'), 'utf8');
  assert.match(source, /bootstrapDesktopMain\(\{\s*loadMain:\s*\(\)\s*=>\s*undefined\s*\}\)/);
  assert.doesNotMatch(source, /bootstrapDesktopMain\(\)/);
  assert.doesNotMatch(source, /require\(['"]\.\.\/main(?:\.js)?['"]\)/);
});

test('settings credential smoke Electron driver captures trusted root before settings route', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokeElectron.js'), 'utf8');
  assert.match(source, /desktop_version=smoke&cache_bust/);
  assert.match(source, /\/settings/);
});


test('settings credential smoke Electron driver has fixed low-sensitivity navigation diagnostics', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokeElectron.js'), 'utf8');
  const pageLoadSource = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokePageLoad.js'), 'utf8');
  assert.match(pageLoadSource, /did-fail-load/);
  assert.match(pageLoadSource, /did-finish-load/);
  assert.match(pageLoadSource, /dom-ready/);
  assert.match(pageLoadSource, /setTimeout/);
  assert.match(source, /INITIAL_NAVIGATION_FAILED/);
  assert.match(source, /SETTINGS_NAVIGATION_FAILED/);
  assert.match(source, /DESKTOP_BRIDGE_UNAVAILABLE/);
  assert.match(source, /SETTINGS_FIELD_TIMEOUT/);
  assert.match(source, /PAGE_AUTOMATION_FAILED/);
});

test('settings credential smoke Electron driver does not decide backend leak status', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokeElectron.js'), 'utf8');
  assert.doesNotMatch(source, /mockBackendSecretLeakFree:\s*true/);
});
