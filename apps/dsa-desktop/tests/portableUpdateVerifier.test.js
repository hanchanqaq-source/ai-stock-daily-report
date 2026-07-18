const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { verifyPortableArchive } = require('../portableUpdateVerifier');

function fixture(contents = 'portable-fixture') {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-portable-'));
  const zip = path.join(dir, '股票基金质量分析系统-Portable-v0.0.0.zip');
  const sha = `${zip}.sha256`;
  fs.writeFileSync(zip, contents);
  fs.writeFileSync(sha, `${crypto.createHash('sha256').update(contents).digest('hex')}  ${path.basename(zip)}\n`);
  return { dir, zip, sha };
}

test('accepts a matching portable ZIP checksum', () => {
  const { dir, zip, sha } = fixture();
  try { assert.equal(verifyPortableArchive(zip, sha).valid, true); } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('rejects malformed checksum files and mismatches', () => {
  const first = fixture();
  const second = fixture('changed');
  try {
    fs.writeFileSync(first.sha, 'not-a-checksum');
    assert.throws(() => verifyPortableArchive(first.zip, first.sha));
    assert.equal(verifyPortableArchive(first.zip, second.sha).valid, false);
  } finally { fs.rmSync(first.dir, { recursive: true, force: true }); fs.rmSync(second.dir, { recursive: true, force: true }); }
});

test('verification module only exposes a read-only verification operation', () => {
  assert.deepEqual(Object.keys(require('../portableUpdateVerifier')), ['verifyPortableArchive']);
});
