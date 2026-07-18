const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { inspectPortableArchive, verifyPortableArchive } = require('../portableUpdateVerifier');

function zipFixture(entries) {
  const chunks = [];
  const centralDirectory = [];
  let offset = 0;
  for (const name of entries) {
    const nameBuffer = Buffer.from(name, 'utf8');
    const localHeader = Buffer.alloc(30);
    localHeader.writeUInt32LE(0x04034b50, 0);
    localHeader.writeUInt16LE(20, 4);
    localHeader.writeUInt16LE(0x0800, 6);
    localHeader.writeUInt16LE(nameBuffer.length, 26);
    chunks.push(localHeader, nameBuffer);

    const centralHeader = Buffer.alloc(46);
    centralHeader.writeUInt32LE(0x02014b50, 0);
    centralHeader.writeUInt16LE(20, 4);
    centralHeader.writeUInt16LE(20, 6);
    centralHeader.writeUInt16LE(0x0800, 8);
    centralHeader.writeUInt16LE(nameBuffer.length, 28);
    centralHeader.writeUInt32LE(offset, 42);
    centralDirectory.push(centralHeader, nameBuffer);
    offset += localHeader.length + nameBuffer.length;
  }
  const centralDirectoryBuffer = Buffer.concat(centralDirectory);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);
  eocd.writeUInt16LE(entries.length, 8);
  eocd.writeUInt16LE(entries.length, 10);
  eocd.writeUInt32LE(centralDirectoryBuffer.length, 12);
  eocd.writeUInt32LE(offset, 16);
  return Buffer.concat([...chunks, centralDirectoryBuffer, eocd]);
}

const PORTABLE_ENTRIES = [
  '股票基金质量分析系统/股票基金质量分析系统.exe',
  '股票基金质量分析系统/resources/backend/stock_analysis/stock_analysis.exe',
  '股票基金质量分析系统/data/README.txt',
  '股票基金质量分析系统/logs/README.txt',
  '股票基金质量分析系统/config/README.txt',
  '股票基金质量分析系统/plugins/README.txt',
];

function portableFixture(entries = PORTABLE_ENTRIES) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-portable-structure-'));
  const zip = path.join(dir, '股票基金质量分析系统-Portable-v0.0.0.zip');
  const sha = `${zip}.sha256`;
  const contents = zipFixture(entries);
  fs.writeFileSync(zip, contents);
  fs.writeFileSync(sha, `${crypto.createHash('sha256').update(contents).digest('hex')}  ${path.basename(zip)}\n`);
  return { dir, zip, sha };
}

test('accepts a matching portable ZIP checksum', () => {
  const { dir, zip, sha } = portableFixture();
  try { assert.equal(verifyPortableArchive(zip, sha).valid, true); } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('rejects malformed checksum files and mismatches', () => {
  const first = portableFixture();
  const second = portableFixture([...PORTABLE_ENTRIES, '股票基金质量分析系统/VERSION.txt']);
  try {
    fs.writeFileSync(first.sha, 'not-a-checksum');
    assert.throws(() => verifyPortableArchive(first.zip, first.sha));
    assert.equal(verifyPortableArchive(first.zip, second.sha).valid, false);
  } finally { fs.rmSync(first.dir, { recursive: true, force: true }); fs.rmSync(second.dir, { recursive: true, force: true }); }
});

test('verification module only exposes a read-only verification operation', () => {
  assert.deepEqual(Object.keys(require('../portableUpdateVerifier')).sort(), [
    'inspectPortableArchive',
    'readZipEntryNames',
    'verifyPortableArchive',
  ]);
});

test('accepts a matching portable ZIP only when the packaged runtime structure is complete', () => {
  const { dir, zip, sha } = portableFixture();
  try {
    assert.deepEqual(verifyPortableArchive(zip, sha), {
      valid: true,
      expected: hashFileForTest(zip),
      actual: hashFileForTest(zip),
      checksumValid: true,
      structureValid: true,
      missingEntries: [],
    });
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('rejects a ZIP missing the Chinese executable, backend executable, or protected directories', () => {
  const { dir, zip } = portableFixture(['股票基金质量分析系统/data/README.txt']);
  try {
    const result = inspectPortableArchive(zip);
    assert.equal(result.valid, false);
    assert.ok(result.missing.includes('股票基金质量分析系统/股票基金质量分析系统.exe'));
    assert.ok(result.missing.includes('股票基金质量分析系统/resources/backend/stock_analysis/stock_analysis.exe'));
    assert.ok(result.missing.includes('股票基金质量分析系统/logs/'));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

function hashFileForTest(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}
