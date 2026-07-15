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

test('settings credential smoke Electron driver captures trusted root before SPA settings route', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokeElectron.js'), 'utf8');
  const routeSource = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokePageRoute.js'), 'utf8');
  assert.match(source, /desktop_version=smoke&cache_bust/);
  assert.match(source, /switchToSettingsRoute/);
  assert.match(routeSource, /\/settings/);
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


test('settings credential smoke Electron driver only performs the trusted root loadURL', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokeElectron.js'), 'utf8');
  assert.equal((source.match(/waitForLoad\(/g) || []).length, 1);
  assert.match(source, /desktop_version=smoke&cache_bust/);
  assert.doesNotMatch(source, /`http:\/\/127\.0\.0\.1:\$\{port\}\/settings`/);
});

test('settings credential smoke Electron driver checks bridge and fields after SPA route success', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../scripts/windowsSettingsCredentialSmokeElectron.js'), 'utf8');
  const routeIndex = source.indexOf('const settingsRouteError = await switchToSettingsRoute');
  const bridgeIndex = source.indexOf('if (!await hasDesktopBridge(win))');
  const setIndex = source.indexOf('const setError = await automateSet(win)');
  const clearIndex = source.indexOf('const result = await automateRestartReadClear(win)');
  assert.ok(routeIndex > -1);
  assert.ok(bridgeIndex > routeIndex);
  assert.ok(setIndex > bridgeIndex);
  assert.ok(clearIndex > bridgeIndex);
});
