const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const { buildPortableDownloadPaths, selectPortableReleaseAssets } = require('../portableReleaseDownload');

test('selects only a matching portable ZIP and checksum from a GitHub release', () => {
  const assets = selectPortableReleaseAssets({ assets: [
    { name: 'installer.exe', browser_download_url: 'https://github.com/x/installer.exe' },
    { name: '股票基金质量分析系统-Portable-v3.21.1.zip', browser_download_url: 'https://github.com/x/portable.zip' },
    { name: '股票基金质量分析系统-Portable-v3.21.1.zip.sha256', browser_download_url: 'https://github.com/x/portable.zip.sha256' },
  ] });
  assert.equal(assets.zipUrl, 'https://github.com/x/portable.zip');
  assert.deepEqual(buildPortableDownloadPaths(path.resolve('tmp-download'), assets), { zipPath: path.join(path.resolve('tmp-download'), '股票基金质量分析系统-Portable-v3.21.1.zip'), sha256Path: path.join(path.resolve('tmp-download'), '股票基金质量分析系统-Portable-v3.21.1.zip.sha256') });
});

test('rejects release assets without a matching checksum', () => {
  assert.throws(() => selectPortableReleaseAssets({ assets: [{ name: 'Portable.zip', browser_download_url: 'https://github.com/x/a.zip' }] }));
});
