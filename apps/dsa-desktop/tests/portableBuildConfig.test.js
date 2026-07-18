const assert = require('node:assert/strict');
const test = require('node:test');

const packageJson = require('../package.json');
const portableConfig = require('../electron-builder.portable.cjs');

test('portable build keeps the installer target unchanged', () => {
  assert.equal(packageJson.build.win.target, 'nsis');
  assert.equal(packageJson.build.win.artifactName, 'daily-stock-analysis-windows-installer-v${version}.${ext}');
});

test('portable build uses the Chinese product name without inheriting the installer target', () => {
  assert.equal(portableConfig.productName, '股票基金质量分析系统');
  assert.equal(portableConfig.win.target, undefined);
  assert.match(packageJson.scripts['build:portable'], /--dir/);
  assert.match(packageJson.scripts['build:portable'], /--x64/);
});

test('portable build metadata points to the current repository', () => {
  assert.deepEqual(portableConfig.win.publish, [
    {
      provider: 'github',
      owner: 'hanchanqaq-source',
      repo: 'ai-stock-daily-report',
    },
  ]);
});

test('portable build includes the compiled backend resource contract', () => {
  assert.ok(Array.isArray(portableConfig.extraResources));
  assert.ok(portableConfig.extraResources.some((entry) => (
    entry.from === '../../dist/backend/stock_analysis' && entry.to === 'backend/stock_analysis'
  )));
});

test('portable build packages the read-only update verifier with the desktop main process', () => {
  assert.ok(packageJson.build.files.includes('portableUpdateVerifier.js'));
});

test('portable build packages the M2.2 recovery module with the desktop main process', () => {
  assert.ok(packageJson.build.files.includes('portableUpdateRecovery.js'));
});
