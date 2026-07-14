const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CREDENTIAL_SCHEMA_VERSION = 1;
const CREDENTIAL_KEY_PATTERN = /^[A-Z][A-Z0-9_]{1,127}$/;
const DEFAULT_PRODUCT_DIR_NAME = 'Daily Stock Analysis';
const CREDENTIAL_RELATIVE_PATH = Object.freeze(['secure', 'credentials.v1.json']);

const ERROR_CODES = Object.freeze({
  UNSUPPORTED_PLATFORM: 'unsupported_platform',
  STORAGE_UNAVAILABLE: 'storage_unavailable',
  INVALID_KEY: 'invalid_key',
  INVALID_VALUE: 'invalid_value',
  CORRUPT_STORE: 'corrupt_store',
  ENCRYPTION_FAILED: 'encryption_failed',
  DECRYPTION_FAILED: 'decryption_failed',
  WRITE_FAILED: 'write_failed',
  READ_FAILED: 'read_failed',
});

function makeResult(fields = {}) {
  return {
    success: Boolean(fields.success),
    configured: Boolean(fields.configured),
    supported: Boolean(fields.supported),
    ...(fields.errorCode ? { errorCode: fields.errorCode } : {}),
  };
}

function validateCredentialKey(key) {
  return typeof key === 'string' && CREDENTIAL_KEY_PATTERN.test(key);
}

function resolveCredentialStorePath({
  platform = process.platform,
  env = process.env,
  productDirName = DEFAULT_PRODUCT_DIR_NAME,
} = {}) {
  if (platform !== 'win32') {
    return { supported: false, errorCode: ERROR_CODES.UNSUPPORTED_PLATFORM };
  }

  const localAppData = typeof env.LOCALAPPDATA === 'string' ? env.LOCALAPPDATA.trim() : '';
  if (!localAppData) {
    return { supported: false, errorCode: ERROR_CODES.STORAGE_UNAVAILABLE };
  }

  const root = path.resolve(localAppData);
  const safeProductDirName = String(productDirName || DEFAULT_PRODUCT_DIR_NAME).replace(/[^A-Za-z0-9 ._-]/g, '').trim();
  const storePath = path.resolve(root, safeProductDirName || DEFAULT_PRODUCT_DIR_NAME, ...CREDENTIAL_RELATIVE_PATH);
  const relative = path.relative(root, storePath);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
    return { supported: false, errorCode: ERROR_CODES.STORAGE_UNAVAILABLE };
  }

  return { supported: true, storePath };
}

function emptyStore() {
  return {
    schemaVersion: CREDENTIAL_SCHEMA_VERSION,
    encryptedValues: {},
    updatedAt: null,
  };
}

function isValidStoreDocument(document) {
  if (!document || typeof document !== 'object' || Array.isArray(document)) {
    return false;
  }
  if (document.schemaVersion !== CREDENTIAL_SCHEMA_VERSION) {
    return false;
  }
  if (!document.encryptedValues || typeof document.encryptedValues !== 'object' || Array.isArray(document.encryptedValues)) {
    return false;
  }
  return Object.entries(document.encryptedValues).every(
    ([key, value]) => validateCredentialKey(key) && typeof value === 'string' && /^[A-Za-z0-9+/]+={0,2}$/.test(value)
  );
}

function cloneStore(document) {
  return {
    schemaVersion: CREDENTIAL_SCHEMA_VERSION,
    encryptedValues: { ...document.encryptedValues },
    updatedAt: typeof document.updatedAt === 'string' ? document.updatedAt : null,
  };
}

function createSecureCredentialStore({
  safeStorage,
  platform = process.platform,
  env = process.env,
  fsModule = fs,
  productDirName = DEFAULT_PRODUCT_DIR_NAME,
  now = () => new Date().toISOString(),
} = {}) {
  const pathState = resolveCredentialStorePath({ platform, env, productDirName });

  function isSupported() {
    if (!pathState.supported) {
      return { supported: false, errorCode: pathState.errorCode };
    }
    if (!safeStorage || typeof safeStorage.isEncryptionAvailable !== 'function' || !safeStorage.isEncryptionAvailable()) {
      return { supported: false, errorCode: ERROR_CODES.STORAGE_UNAVAILABLE };
    }
    return { supported: true };
  }

  function readStoreDocument() {
    if (!pathState.supported) {
      return { ok: false, missing: true, document: emptyStore(), errorCode: pathState.errorCode };
    }
    try {
      if (!fsModule.existsSync(pathState.storePath)) {
        return { ok: true, missing: true, document: emptyStore() };
      }
      const raw = fsModule.readFileSync(pathState.storePath, 'utf8');
      const parsed = JSON.parse(raw);
      if (!isValidStoreDocument(parsed)) {
        return { ok: false, errorCode: ERROR_CODES.CORRUPT_STORE };
      }
      return { ok: true, missing: false, document: cloneStore(parsed) };
    } catch (_error) {
      return { ok: false, errorCode: ERROR_CODES.CORRUPT_STORE };
    }
  }

  function writeStoreDocument(document) {
    const dir = path.dirname(pathState.storePath);
    const tempPath = path.join(dir, `.credentials.v1.${process.pid}.${crypto.randomBytes(8).toString('hex')}.tmp`);
    const content = `${JSON.stringify(document, null, 2)}\n`;
    try {
      fsModule.mkdirSync(dir, { recursive: true, mode: 0o700 });
      fsModule.writeFileSync(tempPath, content, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
      fsModule.renameSync(tempPath, pathState.storePath);
      try {
        fsModule.chmodSync(pathState.storePath, 0o600);
      } catch (_error) {
        // Best effort only on platforms/filesystems that support chmod semantics.
      }
      return { ok: true };
    } catch (_error) {
      try {
        if (fsModule.existsSync(tempPath)) {
          fsModule.unlinkSync(tempPath);
        }
      } catch (_cleanupError) {
        // Keep the returned error low-sensitivity and deterministic.
      }
      return { ok: false, errorCode: ERROR_CODES.WRITE_FAILED };
    }
  }

  function getCredentialStatus(key) {
    const support = isSupported();
    if (!support.supported) {
      return makeResult({ success: false, supported: false, configured: false, errorCode: support.errorCode });
    }
    if (!validateCredentialKey(key)) {
      return makeResult({ success: false, supported: true, configured: false, errorCode: ERROR_CODES.INVALID_KEY });
    }
    const readResult = readStoreDocument();
    if (!readResult.ok) {
      return makeResult({ success: false, supported: true, configured: false, errorCode: readResult.errorCode });
    }
    return makeResult({ success: true, supported: true, configured: Boolean(readResult.document.encryptedValues[key]) });
  }

  function setCredential(key, plaintext) {
    const support = isSupported();
    if (!support.supported) {
      return makeResult({ success: false, supported: false, configured: false, errorCode: support.errorCode });
    }
    if (!validateCredentialKey(key)) {
      return makeResult({ success: false, supported: true, configured: false, errorCode: ERROR_CODES.INVALID_KEY });
    }
    if (typeof plaintext !== 'string' || plaintext.length === 0) {
      return makeResult({ success: false, supported: true, configured: false, errorCode: ERROR_CODES.INVALID_VALUE });
    }

    const readResult = readStoreDocument();
    if (!readResult.ok) {
      return makeResult({ success: false, supported: true, configured: false, errorCode: readResult.errorCode });
    }

    let encryptedBase64;
    try {
      encryptedBase64 = safeStorage.encryptString(plaintext).toString('base64');
    } catch (_error) {
      return makeResult({ success: false, supported: true, configured: false, errorCode: ERROR_CODES.ENCRYPTION_FAILED });
    }

    const nextDocument = cloneStore(readResult.document);
    nextDocument.encryptedValues[key] = encryptedBase64;
    nextDocument.updatedAt = now();
    const writeResult = writeStoreDocument(nextDocument);
    if (!writeResult.ok) {
      return makeResult({ success: false, supported: true, configured: Boolean(readResult.document.encryptedValues[key]), errorCode: writeResult.errorCode });
    }
    return makeResult({ success: true, supported: true, configured: true });
  }

  function clearCredential(key) {
    const support = isSupported();
    if (!support.supported) {
      return makeResult({ success: false, supported: false, configured: false, errorCode: support.errorCode });
    }
    if (!validateCredentialKey(key)) {
      return makeResult({ success: false, supported: true, configured: false, errorCode: ERROR_CODES.INVALID_KEY });
    }
    const readResult = readStoreDocument();
    if (!readResult.ok) {
      return makeResult({ success: false, supported: true, configured: false, errorCode: readResult.errorCode });
    }
    const nextDocument = cloneStore(readResult.document);
    delete nextDocument.encryptedValues[key];
    nextDocument.updatedAt = now();
    const writeResult = writeStoreDocument(nextDocument);
    if (!writeResult.ok) {
      return makeResult({ success: false, supported: true, configured: Boolean(readResult.document.encryptedValues[key]), errorCode: writeResult.errorCode });
    }
    return makeResult({ success: true, supported: true, configured: false });
  }

  function readCredentialForMainProcess(key) {
    const support = isSupported();
    if (!support.supported) {
      return { success: false, supported: false, value: null, errorCode: support.errorCode };
    }
    if (!validateCredentialKey(key)) {
      return { success: false, supported: true, value: null, errorCode: ERROR_CODES.INVALID_KEY };
    }
    const readResult = readStoreDocument();
    if (!readResult.ok) {
      return { success: false, supported: true, value: null, errorCode: readResult.errorCode };
    }
    const encryptedBase64 = readResult.document.encryptedValues[key];
    if (!encryptedBase64) {
      return { success: true, supported: true, value: null, configured: false };
    }
    try {
      return {
        success: true,
        supported: true,
        configured: true,
        value: safeStorage.decryptString(Buffer.from(encryptedBase64, 'base64')),
      };
    } catch (_error) {
      return { success: false, supported: true, value: null, errorCode: ERROR_CODES.DECRYPTION_FAILED };
    }
  }

  return {
    storePath: pathState.storePath || null,
    getCredentialStatus,
    setCredential,
    clearCredential,
    readCredentialForMainProcess,
  };
}

module.exports = {
  CREDENTIAL_KEY_PATTERN,
  ERROR_CODES,
  resolveCredentialStorePath,
  createSecureCredentialStore,
  validateCredentialKey,
};
