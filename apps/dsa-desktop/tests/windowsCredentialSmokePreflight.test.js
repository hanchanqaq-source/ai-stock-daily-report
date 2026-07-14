const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { EventEmitter } = require('node:events');
const {
  ERROR_CODES,
  createElectronEnvironment,
  runElectronReadyPreflight,
} = require('../scripts/windowsCredentialSmokePreflight');

function makeChild(code = 0) {
  const child = new EventEmitter();
  child.stderr = new EventEmitter();
  child.kill = () => true;
  process.nextTick(() => child.emit('close', code));
  return child;
}

test('Electron readiness preflight removes ELECTRON_RUN_AS_NODE and suppresses child output', async () => {
  const calls = [];
  const spawnFn = (binary, argv, options) => {
    calls.push({ binary, argv, options });
    return makeChild(0);
  };
  const previous = process.env.ELECTRON_RUN_AS_NODE;
  process.env.ELECTRON_RUN_AS_NODE = '1';
  try {
    const result = await runElectronReadyPreflight({
      electronBinary: 'electron-test-binary',
      spawnFn,
      timeoutMs: 50,
    });
    assert.equal(result, null);
    assert.equal(calls.length, 1);
    assert.equal(Object.prototype.hasOwnProperty.call(calls[0].options.env, 'ELECTRON_RUN_AS_NODE'), false);
    assert.deepEqual(calls[0].options.stdio, ['ignore', 'ignore', 'pipe']);
  } finally {
    if (previous === undefined) delete process.env.ELECTRON_RUN_AS_NODE;
    else process.env.ELECTRON_RUN_AS_NODE = previous;
  }
});

test('Electron readiness preflight returns fixed low-sensitivity failure codes', async () => {
  const exitFailure = await runElectronReadyPreflight({
    electronBinary: 'electron-test-binary',
    spawnFn: () => makeChild(1),
    timeoutMs: 50,
  });
  assert.equal(exitFailure, ERROR_CODES.ELECTRON_READY_EXIT_FAILED);

  const spawnFailure = await runElectronReadyPreflight({
    electronBinary: 'electron-test-binary',
    spawnFn: () => { throw new Error('local path must not be exposed'); },
    timeoutMs: 50,
  });
  assert.equal(spawnFailure, ERROR_CODES.ELECTRON_READY_SPAWN_FAILED);
});

test('preflight runner only waits for Electron readiness and stays isolated', () => {
  const runnerPath = path.resolve(__dirname, '../scripts/windowsCredentialSmokePreflightElectron.js');
  const source = fs.readFileSync(runnerPath, 'utf8');
  assert.match(source, /app\.whenReady\(\)/);
  assert.equal(source.includes('BrowserWindow'), false);
  assert.equal(source.includes('secureCredentialStore'), false);
  assert.equal(/require\(['"](?:node:)?(?:http|https|net|tls|dgram)['"]\)/.test(source), false);
});

test('package smoke command runs the preflight wrapper', () => {
  const packageJson = require('../package.json');
  assert.equal(
    packageJson.scripts['smoke:credential-store:windows'],
    'node scripts/windowsCredentialSmokePreflight.js',
  );
});

test('createElectronEnvironment does not mutate the source object', () => {
  const source = { ELECTRON_RUN_AS_NODE: '1', SAFE_MARKER: 'ok' };
  const env = createElectronEnvironment(source);
  assert.deepEqual(source, { ELECTRON_RUN_AS_NODE: '1', SAFE_MARKER: 'ok' });
  assert.deepEqual(env, { SAFE_MARKER: 'ok' });
});
