const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const ERROR_CODES = Object.freeze({
  UNSUPPORTED_PLATFORM: 'unsupported_platform',
  CHILD_PROCESS_FAILED: 'child_process_failed',
  INVALID_RESULT: 'invalid_result',
  CLEANUP_FAILED: 'cleanup_failed',
});

const PHASES = Object.freeze(['write', 'restart-read-clear']);
const TEST_KEY = 'DSA_SMOKE_TEST_KEY';
const FORBIDDEN_RESULT_KEYS = new Set([
  'value',
  'plaintext',
  'plainText',
  'testValue',
  'secret',
  'ciphertext',
  'cipherText',
  'encrypted',
  'encryptedValue',
  'encryptedValues',
  'buffer',
  'Buffer',
  'path',
  'storePath',
  'localAppData',
  'env',
  'stack',
]);

function makeStageResult(phase, fields = {}) {
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

function makeSummary(fields = {}) {
  const stages = Array.isArray(fields.stages) ? fields.stages : [];
  const write = stages.find((stage) => stage.phase === 'write');
  const restart = stages.find((stage) => stage.phase === 'restart-read-clear');
  return {
    success: Boolean(fields.success),
    writePassed: Boolean(write && write.success),
    restartReadPassed: Boolean(restart && restart.success && restart.configured),
    clearPassed: Boolean(restart && restart.success && restart.cleared),
    cleanupPassed: Boolean(fields.cleanupPassed),
    errorCode: fields.errorCode || null,
    stages,
  };
}

function containsForbiddenResultKey(value) {
  if (!value || typeof value !== 'object') {
    return false;
  }
  if (Array.isArray(value)) {
    return value.some(containsForbiddenResultKey);
  }
  return Object.entries(value).some(([key, nested]) => (
    FORBIDDEN_RESULT_KEYS.has(key) || containsForbiddenResultKey(nested)
  ));
}

function validateStageResult(result, expectedPhase) {
  if (!result || typeof result !== 'object' || Array.isArray(result)) {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  if (containsForbiddenResultKey(result)) {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  const required = ['phase', 'success', 'encryptionAvailable', 'configured', 'plaintextAbsent', 'statusConfiguredOnly', 'cleared', 'errorCode'];
  if (!required.every((key) => Object.prototype.hasOwnProperty.call(result, key))) {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  if (result.phase !== expectedPhase) {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  for (const key of ['success', 'encryptionAvailable', 'configured', 'plaintextAbsent', 'statusConfiguredOnly', 'cleared']) {
    if (typeof result[key] !== 'boolean') {
      return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
    }
  }
  if (result.errorCode !== null && typeof result.errorCode !== 'string') {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  return makeStageResult(expectedPhase, result);
}

function parseChildResult(stdout, expectedPhase) {
  const lines = String(stdout || '').trim().split(/\r?\n/).filter(Boolean);
  if (lines.length !== 1) {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  try {
    return validateStageResult(JSON.parse(lines[0]), expectedPhase);
  } catch (_error) {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
}

function resolveElectronBinary() {
  const electronModulePath = require.resolve('electron');
  const electron = require(electronModulePath);
  if (typeof electron === 'string' && electron) {
    return electron;
  }
  if (electron && typeof electron === 'object' && typeof electron.default === 'string') {
    return electron.default;
  }
  return null;
}

function runElectronPhase({ phase, tempLocalAppData, testValue, spawnFn = spawn, electronBinary = resolveElectronBinary() }) {
  return new Promise((resolve) => {
    if (!electronBinary) {
      resolve(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
      return;
    }
    const child = spawnFn(electronBinary, [path.join(__dirname, 'windowsCredentialSmokeElectron.js')], {
      cwd: path.resolve(__dirname, '..'),
      windowsHide: true,
      env: {
        ...process.env,
        DSA_CREDENTIAL_SMOKE_PHASE: phase,
        DSA_CREDENTIAL_SMOKE_LOCALAPPDATA: tempLocalAppData,
        DSA_CREDENTIAL_SMOKE_KEY: TEST_KEY,
        DSA_CREDENTIAL_SMOKE_VALUE: testValue,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk.toString('utf8'); });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString('utf8'); });
    child.on('error', () => {
      resolve(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
        return;
      }
      if (stderr.trim()) {
        resolve(makeStageResult(phase, { errorCode: ERROR_CODES.INVALID_RESULT }));
        return;
      }
      resolve(parseChildResult(stdout, phase));
    });
  });
}

function removeTempDir(tempDir, fsModule = fs) {
  try {
    fsModule.rmSync(tempDir, { recursive: true, force: true });
    return true;
  } catch (_error) {
    return false;
  }
}

async function runSmoke({ platform = process.platform, spawnFn = spawn, fsModule = fs, electronBinary } = {}) {
  if (platform !== 'win32') {
    return makeSummary({
      success: false,
      cleanupPassed: true,
      errorCode: ERROR_CODES.UNSUPPORTED_PLATFORM,
      stages: [],
    });
  }

  const tempLocalAppData = fsModule.mkdtempSync(path.join(os.tmpdir(), 'dsa-secure-credential-smoke-'));
  const testValue = `DSA_SMOKE_FAKE_${crypto.randomUUID()}_${crypto.randomUUID()}`;
  const stages = [];
  let cleanupPassed = false;
  try {
    for (const phase of PHASES) {
      const result = await runElectronPhase({ phase, tempLocalAppData, testValue, spawnFn, electronBinary });
      stages.push(result);
      if (!result.success) {
        break;
      }
    }
  } finally {
    cleanupPassed = removeTempDir(tempLocalAppData, fsModule);
  }

  const success = stages.length === PHASES.length && stages.every((stage) => stage.success) && cleanupPassed;
  return makeSummary({
    success,
    cleanupPassed,
    errorCode: success ? null : (stages.find((stage) => !stage.success)?.errorCode || (cleanupPassed ? ERROR_CODES.INVALID_RESULT : ERROR_CODES.CLEANUP_FAILED)),
    stages,
  });
}

function printSummary(summary) {
  console.log('========================================');
  console.log('Windows DPAPI credential smoke summary');
  console.log('========================================');
  console.log(summary.success ? 'PASS' : 'FAIL');
  console.log(`write: ${summary.writePassed ? 'PASS' : 'FAIL'}`);
  console.log(`restart-read: ${summary.restartReadPassed ? 'PASS' : 'FAIL'}`);
  console.log(`clear: ${summary.clearPassed ? 'PASS' : 'FAIL'}`);
  console.log(`cleanup: ${summary.cleanupPassed ? 'PASS' : 'FAIL'}`);
  if (summary.errorCode) {
    console.log(`errorCode: ${summary.errorCode}`);
  }
}

async function main() {
  const summary = await runSmoke();
  printSummary(summary);
  process.exitCode = summary.success ? 0 : 1;
}

if (require.main === module) {
  main().catch(() => {
    printSummary(makeSummary({ success: false, cleanupPassed: false, errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
    process.exitCode = 1;
  });
}

module.exports = {
  ERROR_CODES,
  FORBIDDEN_RESULT_KEYS,
  PHASES,
  TEST_KEY,
  containsForbiddenResultKey,
  makeStageResult,
  parseChildResult,
  printSummary,
  removeTempDir,
  runSmoke,
  validateStageResult,
};
