const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  ERROR_CODES,
  createSecureCredentialStore,
  resolveCredentialStorePath,
} = require('../secureCredentialStore');

function makeTempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-secure-store-hardening-'));
}

function fakeSafeStorage(overrides = {}) {
  return {
    isEncryptionAvailable: () => true,
    encryptString: (value) => Buffer.from(`encrypted:${value}`, 'utf8'),
    decryptString: (buffer) => buffer.toString('utf8').slice('encrypted:'.length),
    ...overrides,
  };
}

test('relative LOCALAPPDATA is rejected instead of resolving into the working directory', () => {
  assert.deepEqual(
    resolveCredentialStorePath({ platform: 'win32', env: { LOCALAPPDATA: 'relative/path' } }),
    { supported: false, errorCode: ERROR_CODES.STORAGE_UNAVAILABLE },
  );
});

test('safeStorage availability exceptions and invalid encrypted output fail closed', () => {
  const localAppData = makeTempDir();
  const availabilityFailure = createSecureCredentialStore({
    safeStorage: fakeSafeStorage({
      isEncryptionAvailable: () => { throw new Error('availability failed'); },
    }),
    platform: 'win32',
    env: { LOCALAPPDATA: localAppData },
  });
  assert.equal(
    availabilityFailure.setCredential('OPENAI_API_KEY', 'fake-token-for-unit-test').errorCode,
    ERROR_CODES.STORAGE_UNAVAILABLE,
  );

  const invalidEncryption = createSecureCredentialStore({
    safeStorage: fakeSafeStorage({ encryptString: () => 'not-a-buffer' }),
    platform: 'win32',
    env: { LOCALAPPDATA: localAppData },
  });
  assert.equal(
    invalidEncryption.setCredential('OPENAI_API_KEY', 'fake-token-for-unit-test').errorCode,
    ERROR_CODES.ENCRYPTION_FAILED,
  );
  assert.equal(fs.existsSync(invalidEncryption.storePath), false);
});

test('temporary-name generation failure preserves the previous encrypted file', () => {
  const localAppData = makeTempDir();
  const store = createSecureCredentialStore({
    safeStorage: fakeSafeStorage(),
    platform: 'win32',
    env: { LOCALAPPDATA: localAppData },
  });
  assert.equal(store.setCredential('OPENAI_API_KEY', 'test-secret-value').success, true);
  const before = fs.readFileSync(store.storePath, 'utf8');

  const failingStore = createSecureCredentialStore({
    safeStorage: fakeSafeStorage(),
    platform: 'win32',
    env: { LOCALAPPDATA: localAppData },
    cryptoModule: {
      randomBytes: () => { throw new Error('random failed'); },
    },
  });
  assert.equal(
    failingStore.setCredential('SECOND_API_KEY', 'new-test-key').errorCode,
    ERROR_CODES.WRITE_FAILED,
  );
  assert.equal(fs.readFileSync(store.storePath, 'utf8'), before);
});

test('non-string decrypt output returns a fixed low-sensitivity error', () => {
  const localAppData = makeTempDir();
  const store = createSecureCredentialStore({
    safeStorage: fakeSafeStorage({ decryptString: () => Buffer.from('not-a-string') }),
    platform: 'win32',
    env: { LOCALAPPDATA: localAppData },
  });
  assert.equal(store.setCredential('OPENAI_API_KEY', 'test-secret-value').success, true);
  assert.equal(
    store.readCredentialForMainProcess('OPENAI_API_KEY').errorCode,
    ERROR_CODES.DECRYPTION_FAILED,
  );
});
