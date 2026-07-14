const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');

test('handled smoke results use Electron normal quit lifecycle', () => {
  const runnerPath = path.resolve(__dirname, '../scripts/windowsCredentialSmokeElectron.js');
  const source = fs.readFileSync(runnerPath, 'utf8');

  assert.equal(source.includes('app.exit(result.success ? 0 : 1)'), false);
  assert.equal(source.includes('app.exit(0)'), false);
  assert.match(source, /writeResult\(result\);[\s\S]*?app\.quit\(\);/);
  assert.match(source, /normal quit lifecycle[\s\S]*safeStorage state/);
  assert.match(source, /\.catch\(\(\) => \{[\s\S]*?app\.exit\(1\);/);
});
