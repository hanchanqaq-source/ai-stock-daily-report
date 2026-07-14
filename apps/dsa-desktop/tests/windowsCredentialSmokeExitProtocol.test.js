const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');

test('handled smoke failures remain valid result protocol output', () => {
  const runnerPath = path.resolve(__dirname, '../scripts/windowsCredentialSmokeElectron.js');
  const source = fs.readFileSync(runnerPath, 'utf8');

  assert.equal(source.includes('app.exit(result.success ? 0 : 1)'), false);
  assert.match(source, /writeResult\(result\);[\s\S]*?app\.exit\(0\);/);
  assert.match(source, /\.catch\(\(\) => \{[\s\S]*?app\.exit\(1\);/);
});
