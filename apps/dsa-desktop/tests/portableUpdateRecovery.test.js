const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {
  createPortableUpdateRecoveryPoint,
  restorePortableUpdateRecoveryPoint,
} = require('../portableUpdateRecovery');

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-portable-recovery-'));
  const appDir = path.join(root, '股票基金质量分析系统');
  const backupRoot = path.join(appDir, '.portable-update-backups', 'm2-2-test');
  fs.mkdirSync(path.join(appDir, 'data'), { recursive: true });
  fs.mkdirSync(path.join(appDir, 'logs'), { recursive: true });
  fs.writeFileSync(path.join(appDir, '股票基金质量分析系统.exe'), 'old-program');
  fs.writeFileSync(path.join(appDir, 'resources.pak'), 'old-resource');
  fs.writeFileSync(path.join(appDir, 'data', 'stock_analysis.db'), 'user-data');
  fs.writeFileSync(path.join(appDir, 'logs', 'desktop.log'), 'user-log');
  return { root, appDir, backupRoot };
}

test('recovery point backs up replaceable program files without copying protected user directories', () => {
  const { root, appDir, backupRoot } = fixture();
  try {
    const manifest = createPortableUpdateRecoveryPoint({ appDir, backupRoot });
    assert.deepEqual(manifest.entries.sort(), ['resources.pak', '股票基金质量分析系统.exe']);
    assert.equal(fs.readFileSync(path.join(backupRoot, '股票基金质量分析系统.exe'), 'utf8'), 'old-program');
    assert.equal(fs.existsSync(path.join(backupRoot, 'data')), false);
    assert.equal(fs.readFileSync(path.join(appDir, 'data', 'stock_analysis.db'), 'utf8'), 'user-data');
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('recovery point restores program files while preserving user data and logs', () => {
  const { root, appDir, backupRoot } = fixture();
  try {
    createPortableUpdateRecoveryPoint({ appDir, backupRoot });
    fs.writeFileSync(path.join(appDir, '股票基金质量分析系统.exe'), 'broken-program');
    fs.writeFileSync(path.join(appDir, 'data', 'stock_analysis.db'), 'newer-user-data');
    restorePortableUpdateRecoveryPoint({ appDir, backupRoot });
    assert.equal(fs.readFileSync(path.join(appDir, '股票基金质量分析系统.exe'), 'utf8'), 'old-program');
    assert.equal(fs.readFileSync(path.join(appDir, 'data', 'stock_analysis.db'), 'utf8'), 'newer-user-data');
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('recovery rejects backup roots outside the portable program directory', () => {
  const { root, appDir } = fixture();
  try {
    assert.throws(() => createPortableUpdateRecoveryPoint({ appDir, backupRoot: path.join(root, 'outside') }));
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
