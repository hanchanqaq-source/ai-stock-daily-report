const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  ERROR_CODES,
  createSecureCredentialStore,
  resolveCredentialStorePath,
  validateCredentialKey,
} = require('../secureCredentialStore');

function makeTempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-secure-store-'));
}

function fakeSafeStorage({ available = true, failEncrypt = false, failDecrypt = false } = {}) {
  return {
    isEncryptionAvailable: () => available,
    encryptString(value) {
      if (failEncrypt) throw new Error('encrypt failed');
      return Buffer.from(`encrypted:${value}`, 'utf8');
    },
    decryptString(buffer) {
      if (failDecrypt) throw new Error('decrypt failed');
      const text = buffer.toString('utf8');
      if (!text.startsWith('encrypted:')) throw new Error('bad ciphertext');
      return text.slice('encrypted:'.length);
    },
  };
}

test('resolveCredentialStorePath uses LOCALAPPDATA on Windows only', () => {
  const localAppData = makeTempDir();
  const resolved = resolveCredentialStorePath({ platform: 'win32', env: { LOCALAPPDATA: localAppData } });
  assert.equal(resolved.supported, true);
  assert.equal(resolved.storePath, path.join(localAppData, 'Daily Stock Analysis', 'secure', 'credentials.v1.json'));
  assert.equal(path.relative(localAppData, resolved.storePath).startsWith('..'), false);
  assert.equal(resolved.storePath.includes(process.cwd()), false);

  assert.deepEqual(resolveCredentialStorePath({ platform: 'win32', env: {} }), {
    supported: false,
    errorCode: ERROR_CODES.STORAGE_UNAVAILABLE,
  });
  assert.deepEqual(resolveCredentialStorePath({ platform: 'linux', env: { LOCALAPPDATA: localAppData } }), {
    supported: false,
    errorCode: ERROR_CODES.UNSUPPORTED_PLATFORM,
  });
});

test('validateCredentialKey rejects path-like, empty, control, and overlong keys', () => {
  assert.equal(validateCredentialKey('OPENAI_API_KEY'), true);
  assert.equal(validateCredentialKey('A1'), true);
  for (const key of ['', 'a1', 'A', '../KEY', 'BAD/KEY', 'BAD\\KEY', 'BAD\nKEY', `A${'B'.repeat(128)}`]) {
    assert.equal(validateCredentialKey(key), false, key);
  }
});

test('set stores only base64 ciphertext and main-process read decrypts it', () => {
  const localAppData = makeTempDir();
  const store = createSecureCredentialStore({
    safeStorage: fakeSafeStorage(),
    platform: 'win32',
    env: { LOCALAPPDATA: localAppData },
    now: () => '2026-07-14T00:00:00.000Z',
  });
  const result = store.setCredential('OPENAI_API_KEY', 'test-secret-value');
  assert.deepEqual(result, { success: true, configured: true, supported: true });

  const raw = fs.readFileSync(store.storePath, 'utf8');
  assert.equal(raw.includes('test-secret-value'), false);
  const parsed = JSON.parse(raw);
  assert.equal(parsed.schemaVersion, 1);
  assert.equal(parsed.updatedAt, '2026-07-14T00:00:00.000Z');
  assert.match(parsed.encryptedValues.OPENAI_API_KEY, /^[A-Za-z0-9+/]+={0,2}$/);
  assert.equal(store.readCredentialForMainProcess('OPENAI_API_KEY').value, 'test-secret-value');
  assert.deepEqual(store.getCredentialStatus('OPENAI_API_KEY'), { success: true, configured: true, supported: true });
  assert.deepEqual(store.getCredentialStatus('MISSING_KEY'), { success: true, configured: false, supported: true });
});

test('update replaces a value and clear removes it while keeping versioned empty file', () => {
  const localAppData = makeTempDir();
  const store = createSecureCredentialStore({ safeStorage: fakeSafeStorage(), platform: 'win32', env: { LOCALAPPDATA: localAppData } });
  assert.equal(store.setCredential('OPENAI_API_KEY', 'test-secret-value').success, true);
  assert.equal(store.setCredential('OPENAI_API_KEY', 'new-test-key').success, true);
  assert.equal(store.readCredentialForMainProcess('OPENAI_API_KEY').value, 'new-test-key');
  assert.equal(fs.readFileSync(store.storePath, 'utf8').includes('test-secret-value'), false);

  assert.deepEqual(store.clearCredential('OPENAI_API_KEY'), { success: true, configured: false, supported: true });
  const parsed = JSON.parse(fs.readFileSync(store.storePath, 'utf8'));
  assert.deepEqual(parsed.encryptedValues, {});
});

test('safeStorage unavailable or encrypt failure refuses plaintext persistence', () => {
  const localAppData = makeTempDir();
  const unavailableStore = createSecureCredentialStore({ safeStorage: fakeSafeStorage({ available: false }), platform: 'win32', env: { LOCALAPPDATA: localAppData } });
  assert.equal(unavailableStore.setCredential('OPENAI_API_KEY', 'fake-token-for-unit-test').errorCode, ERROR_CODES.STORAGE_UNAVAILABLE);
  assert.equal(fs.existsSync(unavailableStore.storePath), false);

  const encryptFailStore = createSecureCredentialStore({ safeStorage: fakeSafeStorage({ failEncrypt: true }), platform: 'win32', env: { LOCALAPPDATA: localAppData } });
  assert.equal(encryptFailStore.setCredential('OPENAI_API_KEY', 'fake-token-for-unit-test').errorCode, ERROR_CODES.ENCRYPTION_FAILED);
  assert.equal(fs.existsSync(encryptFailStore.storePath), false);
});

test('write failure keeps the previous encrypted file unchanged', () => {
  const localAppData = makeTempDir();
  const store = createSecureCredentialStore({ safeStorage: fakeSafeStorage(), platform: 'win32', env: { LOCALAPPDATA: localAppData } });
  assert.equal(store.setCredential('OPENAI_API_KEY', 'test-secret-value').success, true);
  const before = fs.readFileSync(store.storePath, 'utf8');
  const fsModule = { ...fs, renameSync: () => { throw new Error('rename failed'); } };
  const failingStore = createSecureCredentialStore({ safeStorage: fakeSafeStorage(), platform: 'win32', env: { LOCALAPPDATA: localAppData }, fsModule });
  assert.equal(failingStore.setCredential('OPENAI_API_KEY', 'new-test-key').errorCode, ERROR_CODES.WRITE_FAILED);
  assert.equal(fs.readFileSync(store.storePath, 'utf8'), before);
});

test('corrupt JSON returns fixed low-sensitivity errors', () => {
  const localAppData = makeTempDir();
  const store = createSecureCredentialStore({ safeStorage: fakeSafeStorage(), platform: 'win32', env: { LOCALAPPDATA: localAppData } });
  fs.mkdirSync(path.dirname(store.storePath), { recursive: true });
  fs.writeFileSync(store.storePath, '{"encryptedValues":{"OPENAI_API_KEY":"not closed"', 'utf8');
  assert.equal(store.getCredentialStatus('OPENAI_API_KEY').errorCode, ERROR_CODES.CORRUPT_STORE);
  assert.equal(store.setCredential('OPENAI_API_KEY', 'test-secret-value').errorCode, ERROR_CODES.CORRUPT_STORE);
});
