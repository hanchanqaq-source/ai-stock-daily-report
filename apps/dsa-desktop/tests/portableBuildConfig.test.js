const assert = require('node:assert/strict');
const test = require('node:test');

const packageJson = require('../package.json');
const portableConfig = require('../electron-builder.portable.cjs');

test('portable build keeps the installer target unchanged', () => {
  assert.equal(packageJson.build.win.target, 'nsis');
  assert.equal(packageJson.build.win.artifactName, 'daily-stock-analysis-windows-installer-v${version}.${ext}');
});

test('portable build uses the Chinese product name and unpacked x64 target', () => {
  assert.equal(portableConfig.productName, '股票基金质量分析系统');
  assert.deepEqual(portableConfig.win.target, [
    {
      target: 'dir',
      arch: ['x64'],
    },
  ]);
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
