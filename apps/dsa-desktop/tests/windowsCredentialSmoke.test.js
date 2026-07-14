const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { EventEmitter } = require('node:events');
const {
  containsForbiddenResultKey,
  createChildEnvironment,
  parseChildResult,
  resolveSmokeTempLocalAppData,
  runSmoke,
  validateStageResult,
} = require('../scripts/windowsCredentialSmokeController');

function makeSuccessfulStage(phase) {
  return {
    phase,
    success: true,
    encryptionAvailable: true,
    configured: true,
    plaintextAbsent: true,
    statusConfiguredOnly: true,
    cleared: phase === 'restart-read-clear',
    errorCode: null,
  };
}

function makeChild({ code = 0, result, stderr = '', close = true } = {}) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.kill = () => {
    child.killed = true;
    if (!close) {
      process.nextTick(() => child.emit('close', null));
    }
    return true;
  };
  process.nextTick(() => {
    if (result) child.stdout.emit('data', `${JSON.stringify(result)}\n`);
    if (stderr) child.stderr.emit('data', stderr);
    if (close) child.emit('close', code);
  });
  return child;
}

function makeSpawn(results) {
  const calls = [];
  const spawnFn = (binary, argv, options) => {
    calls.push({ binary, argv, options });
    const phase = options.env.DSA_CREDENTIAL_SMOKE_PHASE;
    const next = results.shift();
    return makeChild(typeof next === 'function' ? next(phase, options) : next);
  };
  spawnFn.calls = calls;
  return spawnFn;
}

test('non-Windows platform refuses to run with fixed result', async () => {
  const summary = await runSmoke({ platform: 'linux' });
  assert.equal(summary.success, false);
  assert.equal(summary.errorCode, 'unsupported_platform');
  assert.equal(summary.cleanupPassed, true);
  assert.deepEqual(summary.stages, []);
});

test('controller parses two successful phases and reports PASS fields', async () => {
  const spawnFn = makeSpawn([
    (phase) => ({ code: 0, result: makeSuccessfulStage(phase) }),
    (phase) => ({ code: 0, result: makeSuccessfulStage(phase) }),
  ]);
  const summary = await runSmoke({ platform: 'win32', spawnFn, electronBinary: process.execPath });
  assert.equal(summary.success, true);
  assert.equal(summary.writePassed, true);
  assert.equal(summary.restartReadPassed, true);
  assert.equal(summary.clearPassed, true);
  assert.equal(summary.cleanupPassed, true);
  assert.equal(spawnFn.calls.length, 2);
  assert.equal(spawnFn.calls[0].options.env.DSA_CREDENTIAL_SMOKE_KEY, 'DSA_SMOKE_TEST_KEY');
  assert.equal(spawnFn.calls[0].argv.includes(spawnFn.calls[0].options.env.DSA_CREDENTIAL_SMOKE_VALUE), false);
});

test('any failed phase makes overall result fail', async () => {
  const failed = makeSuccessfulStage('write');
  failed.success = false;
  failed.errorCode = 'set_failed';
  const spawnFn = makeSpawn([{ code: 0, result: failed }]);
  const summary = await runSmoke({ platform: 'win32', spawnFn, electronBinary: process.execPath });
  assert.equal(summary.success, false);
  assert.equal(summary.errorCode, 'set_failed');
  assert.equal(summary.stages.length, 1);
});

test('non-zero child process exit is recognized', async () => {
  const spawnFn = makeSpawn([{ code: 1, result: makeSuccessfulStage('write') }]);
  const summary = await runSmoke({ platform: 'win32', spawnFn, electronBinary: process.execPath });
  assert.equal(summary.success, false);
  assert.equal(summary.errorCode, 'child_process_failed');
});

test('hung child process times out and temporary directory is cleaned', async () => {
  const createdDirs = [];
  const fsModule = {
    ...fs,
    mkdtempSync(prefix) {
      const dir = fs.mkdtempSync(prefix);
      createdDirs.push(dir);
      return dir;
    },
    rmSync: fs.rmSync,
  };
  const spawnFn = makeSpawn([{ close: false }]);
  const summary = await runSmoke({
    platform: 'win32',
    spawnFn,
    fsModule,
    electronBinary: process.execPath,
    phaseTimeoutMs: 5,
  });
  assert.equal(summary.success, false);
  assert.equal(summary.errorCode, 'child_process_timeout');
  assert.equal(summary.cleanupPassed, true);
  assert.equal(fs.existsSync(createdDirs[0]), false);
});

test('child result missing required fields is blocked', () => {
  const parsed = parseChildResult('{"phase":"write","success":true}\n', 'write');
  assert.equal(parsed.success, false);
  assert.equal(parsed.errorCode, 'invalid_result');
});

test('forbidden fields, extra fields, and arbitrary error codes are blocked', () => {
  assert.equal(containsForbiddenResultKey({ value: 'x' }), true);
  assert.equal(containsForbiddenResultKey({ nested: { ciphertext: 'x' } }), true);

  const forbidden = validateStageResult({ ...makeSuccessfulStage('write'), buffer: 'x' }, 'write');
  assert.equal(forbidden.success, false);
  assert.equal(forbidden.errorCode, 'invalid_result');

  const extra = validateStageResult({ ...makeSuccessfulStage('write'), harmless: true }, 'write');
  assert.equal(extra.success, false);
  assert.equal(extra.errorCode, 'invalid_result');

  const arbitraryError = makeSuccessfulStage('write');
  arbitraryError.success = false;
  arbitraryError.errorCode = 'DSA_SMOKE_FAKE_SHOULD_NOT_PRINT';
  const rejectedError = validateStageResult(arbitraryError, 'write');
  assert.equal(rejectedError.success, false);
  assert.equal(rejectedError.errorCode, 'invalid_result');
});

test('temporary directory is cleaned on success and failure', async () => {
  const createdDirs = [];
  const fsModule = {
    ...fs,
    mkdtempSync(prefix) {
      const dir = fs.mkdtempSync(prefix);
      createdDirs.push(dir);
      return dir;
    },
    rmSync: fs.rmSync,
  };
  const successSpawn = makeSpawn([
    (phase) => ({ code: 0, result: makeSuccessfulStage(phase) }),
    (phase) => ({ code: 0, result: makeSuccessfulStage(phase) }),
  ]);
  assert.equal((await runSmoke({ platform: 'win32', spawnFn: successSpawn, fsModule, electronBinary: process.execPath })).cleanupPassed, true);
  assert.equal(fs.existsSync(createdDirs[0]), false);

  const failSpawn = makeSpawn([{ code: 1 }]);
  assert.equal((await runSmoke({ platform: 'win32', spawnFn: failSpawn, fsModule, electronBinary: process.execPath })).cleanupPassed, true);
  assert.equal(fs.existsSync(createdDirs[1]), false);
});

test('controller uses temp LOCALAPPDATA and not the real production directory', async () => {
  const spawnFn = makeSpawn([
    (_phase, options) => {
      const localAppData = options.env.DSA_CREDENTIAL_SMOKE_LOCALAPPDATA;
      assert.equal(localAppData.startsWith(os.tmpdir()), true);
      assert.equal(localAppData.includes(path.join('Daily Stock Analysis', 'secure')), false);
      assert.notEqual(localAppData, process.env.LOCALAPPDATA || '');
      return { code: 0, result: makeSuccessfulStage('write') };
    },
    (phase) => ({ code: 0, result: makeSuccessfulStage(phase) }),
  ]);
  await runSmoke({ platform: 'win32', spawnFn, electronBinary: process.execPath });
});

test('child environment forces real Electron mode and keeps the value out of argv', () => {
  const previous = process.env.ELECTRON_RUN_AS_NODE;
  process.env.ELECTRON_RUN_AS_NODE = '1';
  try {
    const childEnv = createChildEnvironment({
      phase: 'write',
      tempLocalAppData: path.join(os.tmpdir(), 'dsa-secure-credential-smoke-example'),
      testValue: 'fake-value',
    });
    assert.equal(Object.prototype.hasOwnProperty.call(childEnv, 'ELECTRON_RUN_AS_NODE'), false);
    assert.equal(childEnv.DSA_CREDENTIAL_SMOKE_VALUE, 'fake-value');
  } finally {
    if (previous === undefined) delete process.env.ELECTRON_RUN_AS_NODE;
    else process.env.ELECTRON_RUN_AS_NODE = previous;
  }
});

test('Electron runner only accepts the dedicated random temp directory', () => {
  const accepted = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-secure-credential-smoke-'));
  const wrongPrefix = fs.mkdtempSync(path.join(os.tmpdir(), 'other-smoke-'));
  try {
    assert.equal(resolveSmokeTempLocalAppData(accepted, {
      tempRoot: os.tmpdir(),
      realLocalAppData: path.join(os.tmpdir(), 'production-local-app-data'),
    }), fs.realpathSync(accepted));
    assert.equal(resolveSmokeTempLocalAppData(wrongPrefix, { tempRoot: os.tmpdir() }), null);
    assert.equal(resolveSmokeTempLocalAppData('.', { tempRoot: os.tmpdir() }), null);
    assert.equal(resolveSmokeTempLocalAppData(path.resolve(os.tmpdir(), '..'), { tempRoot: os.tmpdir() }), null);
    assert.equal(resolveSmokeTempLocalAppData(accepted, {
      tempRoot: os.tmpdir(),
      realLocalAppData: accepted,
    }), null);
  } finally {
    fs.rmSync(accepted, { recursive: true, force: true });
    fs.rmSync(wrongPrefix, { recursive: true, force: true });
  }
});

test('Electron runner stays isolated from main, windows, network modules, and test value logs', () => {
  const runnerPath = path.resolve(__dirname, '../scripts/windowsCredentialSmokeElectron.js');
  const source = fs.readFileSync(runnerPath, 'utf8');
  assert.equal(source.includes("require('../main"), false);
  assert.equal(source.includes("require('./main"), false);
  assert.equal(source.includes('BrowserWindow'), false);
  assert.equal(/require\(['"]node:(http|https|net|tls|dgram)['"]\)/.test(source), false);
  assert.equal(/require\(['"](http|https|net|tls|dgram)['"]\)/.test(source), false);
  assert.equal(/console\.log\([^\n]*(testValue|DSA_CREDENTIAL_SMOKE_VALUE)/.test(source), false);
});
