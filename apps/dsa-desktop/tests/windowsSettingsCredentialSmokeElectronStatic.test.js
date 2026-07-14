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
