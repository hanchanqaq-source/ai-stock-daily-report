const fs = require('node:fs');
const path = require('node:path');
const { app, safeStorage } = require('electron');
const { createSecureCredentialStore } = require('../secureCredentialStore');

const ERROR_CODES = Object.freeze({
  UNSUPPORTED_PLATFORM: 'unsupported_platform',
  ENCRYPTION_UNAVAILABLE: 'encryption_unavailable',
  SET_FAILED: 'set_failed',
  RESTART_READ_FAILED: 'restart_read_failed',
  PLAINTEXT_DETECTED: 'plaintext_detected',
  CLEAR_FAILED: 'clear_failed',
  INVALID_RESULT: 'invalid_result',
});

function makeResult(phase, fields = {}) {
  return {
    phase,
    success: Boolean(fields.success),
    encryptionAvailable: Boolean(fields.encryptionAvailable),
    configured: Boolean(fields.configured),
    plaintextAbsent: Boolean(fields.plaintextAbsent),
    statusConfiguredOnly: Boolean(fields.statusConfiguredOnly),
    cleared: Boolean(fields.cleared),
    errorCode: fields.errorCode || null,
  };
}

function writeResult(result) {
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

function fileHasPlaintext(storePath, expectedValue) {
  if (!storePath || !fs.existsSync(storePath)) {
    return false;
  }
  const raw = fs.readFileSync(storePath, 'utf8');
  return raw.includes(expectedValue);
}

function hasValidCiphertext(storePath, key) {
  if (!storePath || !fs.existsSync(storePath)) {
    return false;
  }
  const parsed = JSON.parse(fs.readFileSync(storePath, 'utf8'));
  const encrypted = parsed && parsed.encryptedValues && parsed.encryptedValues[key];
  return typeof encrypted === 'string' && encrypted.length > 0 && /^[A-Za-z0-9+/]+={0,2}$/.test(encrypted);
}

function createSmokeStore(localAppData) {
  return createSecureCredentialStore({
    safeStorage,
    platform: process.platform,
    env: { LOCALAPPDATA: localAppData },
  });
}

function statusHasOnlyConfigured(status, expectedConfigured) {
  return Boolean(status)
    && Object.keys(status).sort().join(',') === 'configured,success,supported'
    && status.success === true
    && status.supported === true
    && status.configured === expectedConfigured;
}

async function runPhase() {
  const phase = process.env.DSA_CREDENTIAL_SMOKE_PHASE;
  const localAppData = process.env.DSA_CREDENTIAL_SMOKE_LOCALAPPDATA;
  const key = process.env.DSA_CREDENTIAL_SMOKE_KEY;
  const testValue = process.env.DSA_CREDENTIAL_SMOKE_VALUE;

  if ((phase !== 'write' && phase !== 'restart-read-clear') || !localAppData || !key || !testValue) {
    return makeResult(phase || 'unknown', { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  if (process.platform !== 'win32') {
    return makeResult(phase, { errorCode: ERROR_CODES.UNSUPPORTED_PLATFORM });
  }
  if (!safeStorage.isEncryptionAvailable()) {
    return makeResult(phase, { errorCode: ERROR_CODES.ENCRYPTION_UNAVAILABLE });
  }

  const store = createSmokeStore(localAppData);

  if (phase === 'write') {
    const setResult = store.setCredential(key, testValue);
    const status = store.getCredentialStatus(key);
    const read = store.readCredentialForMainProcess(key);
    const plaintextAbsent = !fileHasPlaintext(store.storePath, testValue);
    const validCiphertext = hasValidCiphertext(store.storePath, key);
    const success = setResult.success === true
      && setResult.configured === true
      && statusHasOnlyConfigured(status, true)
      && read.success === true
      && read.configured === true
      && read.value === testValue
      && plaintextAbsent
      && validCiphertext;
    return makeResult(phase, {
      success,
      encryptionAvailable: true,
      configured: status.configured === true,
      plaintextAbsent,
      statusConfiguredOnly: statusHasOnlyConfigured(status, true),
      cleared: false,
      errorCode: success ? null : (plaintextAbsent ? ERROR_CODES.SET_FAILED : ERROR_CODES.PLAINTEXT_DETECTED),
    });
  }

  const statusBefore = store.getCredentialStatus(key);
  const readBefore = store.readCredentialForMainProcess(key);
  const clearResult = store.clearCredential(key);
  const statusAfter = store.getCredentialStatus(key);
  const readAfter = store.readCredentialForMainProcess(key);
  const plaintextAbsent = !fileHasPlaintext(store.storePath, testValue);
  const restartReadOk = statusHasOnlyConfigured(statusBefore, true)
    && readBefore.success === true
    && readBefore.configured === true
    && readBefore.value === testValue;
  const clearOk = clearResult.success === true
    && clearResult.configured === false
    && statusHasOnlyConfigured(statusAfter, false)
    && readAfter.success === true
    && readAfter.configured === false
    && readAfter.value === null;
  const success = restartReadOk && clearOk && plaintextAbsent;
  return makeResult(phase, {
    success,
    encryptionAvailable: true,
    configured: restartReadOk,
    plaintextAbsent,
    statusConfiguredOnly: statusHasOnlyConfigured(statusBefore, true) && statusHasOnlyConfigured(statusAfter, false),
    cleared: clearOk,
    errorCode: success ? null : (!plaintextAbsent ? ERROR_CODES.PLAINTEXT_DETECTED : (restartReadOk ? ERROR_CODES.CLEAR_FAILED : ERROR_CODES.RESTART_READ_FAILED)),
  });
}

app.whenReady()
  .then(runPhase)
  .then((result) => {
    writeResult(result);
    app.exit(result.success ? 0 : 1);
  })
  .catch(() => {
    writeResult(makeResult(process.env.DSA_CREDENTIAL_SMOKE_PHASE || 'unknown', { errorCode: ERROR_CODES.INVALID_RESULT }));
    app.exit(1);
  });

module.exports = {
  ERROR_CODES,
  fileHasPlaintext,
  hasValidCiphertext,
  makeResult,
  statusHasOnlyConfigured,
};
