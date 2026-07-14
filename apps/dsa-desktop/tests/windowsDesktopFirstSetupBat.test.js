const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const batPath = path.resolve(__dirname, '../../../scripts/windows_desktop_first_setup.bat');
const source = fs.readFileSync(batPath, 'utf8');
const normalized = source.replace(/\r\n/g, '\n');

test('first setup checks Electron executable before installing dependencies', () => {
  const electronCheck = normalized.indexOf('node_modules\\electron\\dist\\electron.exe');
  const npmCi = normalized.indexOf('call "%NPM_CMD%" ci');
  assert.notEqual(electronCheck, -1);
  assert.notEqual(npmCi, -1);
  assert.ok(electronCheck < npmCi);
  assert.match(normalized, /if exist "%ELECTRON_EXE%" \([\s\S]*dependency installation skipped/);
});

test('first setup verifies npm ci and Electron before running the existing smoke BAT', () => {
  const npmCi = normalized.indexOf('call "%NPM_CMD%" ci');
  const postInstallCheck = normalized.lastIndexOf('if exist "%ELECTRON_EXE%"');
  const smokeCall = normalized.indexOf('call "%SMOKE_BAT%"');
  assert.ok(npmCi >= 0);
  assert.ok(postInstallCheck > npmCi);
  assert.ok(smokeCall > postInstallCheck);
  assert.match(normalized, /package-lock\.json/);
  assert.match(normalized, /exit \/b !SMOKE_EXIT!/);
});

test('first setup stays repository-local and excludes unsafe install shortcuts', () => {
  const forbidden = [
    /npm\s+audit\s+fix/i,
    /npm\s+approve-scripts/i,
    /npm\s+install\s+-g/i,
    /\.env/i,
    /goto\s+/i,
    /0\.0\.0\.0/,
  ];
  for (const pattern of forbidden) {
    assert.equal(pattern.test(normalized), false, `forbidden pattern found: ${pattern}`);
  }
  assert.match(normalized, /Running npm ci in apps\\dsa-desktop/);
  assert.match(normalized, /only writes inside this repository/);
});
