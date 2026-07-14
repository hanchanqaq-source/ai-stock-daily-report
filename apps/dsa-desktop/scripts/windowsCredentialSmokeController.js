const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const ERROR_CODES = Object.freeze({
  UNSUPPORTED_PLATFORM: 'unsupported_platform',
  CHILD_PROCESS_FAILED: 'child_process_failed',
  CHILD_PROCESS_TIMEOUT: 'child_process_timeout',
  INVALID_RESULT: 'invalid_result',
  TEMP_DIRECTORY_FAILED: 'temp_directory_failed',
  CLEANUP_FAILED: 'cleanup_failed',
});

const PHASES = Object.freeze(['write', 'restart-read-clear']);
const TEST_KEY = 'DSA_SMOKE_TEST_KEY';
const SMOKE_TEMP_PREFIX = 'dsa-secure-credential-smoke-';
const DEFAULT_PHASE_TIMEOUT_MS = 30000;
const MAX_CHILD_STDOUT_BYTES = 16 * 1024;
const STAGE_RESULT_KEYS = Object.freeze([
  'phase',
  'success',
  'encryptionAvailable',
  'configured',
  'plaintextAbsent',
  'statusConfiguredOnly',
  'cleared',
  'errorCode',
]);
const ALLOWED_STAGE_ERROR_CODES = new Set([
  ERROR_CODES.CHILD_PROCESS_FAILED,
  ERROR_CODES.CHILD_PROCESS_TIMEOUT,
  ERROR_CODES.INVALID_RESULT,
  'unsupported_platform',
  'encryption_unavailable',
  'invalid_temp_directory',
  'set_failed',
  'restart_read_failed',
  'plaintext_detected',
  'clear_failed',
]);
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

function hasExactStageResultKeys(result) {
  const actual = Object.keys(result).sort();
  const expected = [...STAGE_RESULT_KEYS].sort();
  return actual.length === expected.length
    && actual.every((key, index) => key === expected[index]);
}

function validateStageResult(result, expectedPhase) {
  if (!result || typeof result !== 'object' || Array.isArray(result)) {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  if (containsForbiddenResultKey(result) || !hasExactStageResultKeys(result)) {
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
  if (result.errorCode !== null && !ALLOWED_STAGE_ERROR_CODES.has(result.errorCode)) {
    return makeStageResult(expectedPhase, { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  if ((result.success && result.errorCode !== null) || (!result.success && result.errorCode === null)) {
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

function isPathInside(rootPath, candidatePath) {
  const relative = path.relative(rootPath, candidatePath);
  return Boolean(relative)
    && relative !== '..'
    && !relative.startsWith(`..${path.sep}`)
    && !path.isAbsolute(relative);
}

function resolveSmokeTempLocalAppData(candidate, {
  tempRoot = os.tmpdir(),
  realLocalAppData = process.env.LOCALAPPDATA,
  fsModule = fs,
} = {}) {
  if (typeof candidate !== 'string' || !candidate.trim() || !path.isAbsolute(candidate)) {
    return null;
  }
  try {
    const resolvedCandidate = path.resolve(candidate);
    const resolvedTempRoot = path.resolve(tempRoot);
    if (!isPathInside(resolvedTempRoot, resolvedCandidate)) {
      return null;
    }
    if (!path.basename(resolvedCandidate).startsWith(SMOKE_TEMP_PREFIX)) {
      return null;
    }
    if (typeof realLocalAppData === 'string' && realLocalAppData.trim()) {
      if (resolvedCandidate === path.resolve(realLocalAppData)) {
        return null;
      }
    }
    const realCandidate = fsModule.realpathSync(resolvedCandidate);
    const realTempRoot = fsModule.realpathSync(resolvedTempRoot);
    return isPathInside(realTempRoot, realCandidate) ? realCandidate : null;
  } catch (_error) {
    return null;
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

function createChildEnvironment({ phase, tempLocalAppData, testValue }) {
  const childEnv = {
    ...process.env,
    DSA_CREDENTIAL_SMOKE_PHASE: phase,
    DSA_CREDENTIAL_SMOKE_LOCALAPPDATA: tempLocalAppData,
    DSA_CREDENTIAL_SMOKE_KEY: TEST_KEY,
    DSA_CREDENTIAL_SMOKE_VALUE: testValue,
  };
  delete childEnv.ELECTRON_RUN_AS_NODE;
  return childEnv;
}

function runElectronPhase({
  phase,
  tempLocalAppData,
  testValue,
  spawnFn = spawn,
  electronBinary = null,
  phaseTimeoutMs = DEFAULT_PHASE_TIMEOUT_MS,
}) {
  return new Promise((resolve) => {
    let resolvedElectronBinary = electronBinary;
    if (!resolvedElectronBinary) {
      try {
        resolvedElectronBinary = resolveElectronBinary();
      } catch (_error) {
        resolve(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
        return;
      }
    }
    if (!resolvedElectronBinary) {
      resolve(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
      return;
    }

    let child;
    try {
      child = spawnFn(resolvedElectronBinary, [path.join(__dirname, 'windowsCredentialSmokeElectron.js')], {
        cwd: path.resolve(__dirname, '..'),
        windowsHide: true,
        env: createChildEnvironment({ phase, tempLocalAppData, testValue }),
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (_error) {
      resolve(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
      return;
    }

    let stdout = '';
    let settled = false;
    let timer = null;
    const finish = (result) => {
      if (settled) {
        return;
      }
      settled = true;
      if (timer) {
        clearTimeout(timer);
      }
      resolve(result);
    };

    timer = setTimeout(() => {
      try {
        child.kill();
      } catch (_error) {
        // Best effort only; timeout output remains fixed and low-sensitivity.
      }
      finish(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_TIMEOUT }));
    }, phaseTimeoutMs);

    child.stdout.on('data', (chunk) => {
      if (settled) {
        return;
      }
      stdout += chunk.toString('utf8');
      if (Buffer.byteLength(stdout, 'utf8') > MAX_CHILD_STDOUT_BYTES) {
        try {
          child.kill();
        } catch (_error) {
          // Best effort only.
        }
        finish(makeStageResult(phase, { errorCode: ERROR_CODES.INVALID_RESULT }));
      }
    });
    child.stderr.on('data', () => {
      // Consume but never print Electron diagnostics because they may contain local paths.
    });
    child.on('error', () => {
      finish(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
    });
    child.on('close', (code) => {
      if (settled) {
        return;
      }
      if (code !== 0) {
        finish(makeStageResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED }));
        return;
      }
      finish(parseChildResult(stdout, phase));
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

async function runSmoke({
  platform = process.platform,
  spawnFn = spawn,
  fsModule = fs,
  electronBinary,
  phaseTimeoutMs = DEFAULT_PHASE_TIMEOUT_MS,
} = {}) {
  if (platform !== 'win32') {
    return makeSummary({
      success: false,
      cleanupPassed: true,
      errorCode: ERROR_CODES.UNSUPPORTED_PLATFORM,
      stages: [],
    });
  }

  let tempLocalAppData = '';
  let testValue = '';
  try {
    tempLocalAppData = fsModule.mkdtempSync(path.join(os.tmpdir(), SMOKE_TEMP_PREFIX));
    testValue = `DSA_SMOKE_FAKE_${crypto.randomUUID()}_${crypto.randomUUID()}`;
  } catch (_error) {
    return makeSummary({
      success: false,
      cleanupPassed: false,
      errorCode: ERROR_CODES.TEMP_DIRECTORY_FAILED,
      stages: [],
    });
  }

  const stages = [];
  let cleanupPassed = false;
  try {
    for (const phase of PHASES) {
      const result = await runElectronPhase({
        phase,
        tempLocalAppData,
        testValue,
        spawnFn,
        electronBinary,
        phaseTimeoutMs,
      });
      stages.push(result);
      if (!result.success) {
        break;
      }
    }
  } finally {
    testValue = '';
    cleanupPassed = removeTempDir(tempLocalAppData, fsModule);
  }

  const success = stages.length === PHASES.length && stages.every((stage) => stage.success) && cleanupPassed;
  return makeSummary({
    success,
    cleanupPassed,
    errorCode: success
      ? null
      : (stages.find((stage) => !stage.success)?.errorCode
        || (cleanupPassed ? ERROR_CODES.INVALID_RESULT : ERROR_CODES.CLEANUP_FAILED)),
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
  ALLOWED_STAGE_ERROR_CODES,
  DEFAULT_PHASE_TIMEOUT_MS,
  ERROR_CODES,
  FORBIDDEN_RESULT_KEYS,
  PHASES,
  SMOKE_TEMP_PREFIX,
  STAGE_RESULT_KEYS,
  TEST_KEY,
  containsForbiddenResultKey,
  createChildEnvironment,
  makeStageResult,
  parseChildResult,
  printSummary,
  removeTempDir,
  resolveSmokeTempLocalAppData,
  runElectronPhase,
  runSmoke,
  validateStageResult,
};
