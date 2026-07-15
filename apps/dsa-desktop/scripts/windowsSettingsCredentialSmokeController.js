const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const net = require('node:net');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');
const { ERROR_CODES, makeResult, parseResult } = require('./windowsSettingsCredentialSmokeProtocol');
const { SMOKE_TEMP_PREFIX, resolveSmokeTempLocalAppData, removeTempDir } = require('./windowsCredentialSmokeController');

const TEST_KEY = 'APP_M423B1_TEST_TOKEN';
const PHASES = ['set', 'restart-read-clear'];
const TIMEOUT_MS = 45000;
const PORT_START = 8000;
const PORT_END = 8100;
const MAX_STDOUT = 16 * 1024;

function resolveElectronBinary() {
  const electron = require(require.resolve('electron'));
  return typeof electron === 'string' ? electron : electron && electron.default;
}
function isDistMissing() { return !fs.existsSync(path.resolve(__dirname, '..', '..', '..', 'static', 'index.html')); }
function contentType(file) { return file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : file.endsWith('.html') ? 'text/html' : 'application/octet-stream'; }
function makeConfig() { return { config_version: 'app-m423b1-smoke', mask_token: '******', items: [{ key: TEST_KEY, value: '', raw_value_exists: false, is_masked: false, schema: { key: TEST_KEY, title: 'App M4.2.3B.1 Test Token', description: 'Fictional smoke-only sensitive field.', category: 'notification', data_type: 'string', ui_control: 'password', is_sensitive: true, is_required: false, is_editable: true, options: [], validation: {}, display_order: 1 } }] }; }
function makeSetupStatus() {
  return {
    is_complete: true,
    ready_for_smoke: true,
    required_missing_keys: [],
    next_step_key: null,
    checks: [],
  };
}
function makeAuthStatus() {
  return {
    authEnabled: false,
    loggedIn: false,
    passwordSet: false,
    passwordChangeable: false,
    setupState: 'no_password',
  };
}

async function isPortFree(port) { return new Promise((resolve) => { const server = net.createServer(); server.once('error', () => resolve(false)); server.listen(port, '127.0.0.1', () => server.close(() => resolve(true))); }); }
async function findPort() { for (let port = PORT_START; port <= PORT_END; port += 1) if (await isPortFree(port)) return port; return null; }

function startMockServer(port, state) {
  const dist = path.resolve(__dirname, '..', '..', '..', 'static');
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => {
      const body = Buffer.concat(chunks).toString('utf8');
      if (body && state.testValue && body.includes(state.testValue)) state.secretLeak = true;
      const sendJson = (status, payload) => { res.writeHead(status, { 'content-type': 'application/json' }); res.end(JSON.stringify(payload)); };
      if (req.url === '/api/v1/auth/status') return sendJson(200, makeAuthStatus());
      if (req.url && req.url.startsWith('/api/v1/system/config/setup/status')) return sendJson(200, makeSetupStatus());
      if (req.url && req.url.startsWith('/api/v1/system/scheduler/status')) return sendJson(200, { enabled: false, running: false, schedule_times: [], last_success: null, last_error: null });
      if (req.url && req.url.startsWith('/api/v1/system/config') && req.method === 'GET') return sendJson(200, makeConfig());
      if (req.url === '/api/v1/system/config/validate' && req.method === 'POST') return sendJson(200, { valid: true, issues: [] });
      if (req.url === '/api/v1/system/config' && req.method === 'PUT') return sendJson(200, { success: true, config_version: 'app-m423b1-smoke', applied_count: 0, skipped_masked_count: 0, reload_triggered: false, updated_keys: [], warnings: [] });
      let pathname = '/index.html';
      try { pathname = decodeURIComponent(new URL(req.url || '/', `http://127.0.0.1:${port}`).pathname); } catch (_) {}
      const safePath = pathname === '/' || pathname === '/settings' ? '/index.html' : pathname;
      const filePath = path.normalize(path.join(dist, safePath));
      if (!filePath.startsWith(dist)) { res.writeHead(404); res.end(''); return; }
      const finalPath = fs.existsSync(filePath) && fs.statSync(filePath).isFile() ? filePath : path.join(dist, 'index.html');
      res.writeHead(200, { 'content-type': contentType(finalPath) });
      fs.createReadStream(finalPath).pipe(res);
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', () => reject(new Error('mock_server_failed')));
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

function resolveChildSmokeTempLocalAppData(candidate, env = process.env) {
  if (typeof candidate !== 'string' || candidate !== env.LOCALAPPDATA) {
    return null;
  }
  return resolveSmokeTempLocalAppData(candidate, {
    realLocalAppData: '',
  });
}

function createChildEnvironment({ phase, port, tempLocalAppData, testValue }, sourceEnv = process.env) {
  const env = {
    ...sourceEnv,
    LOCALAPPDATA: tempLocalAppData,
    DSA_SETTINGS_CREDENTIAL_SMOKE_PHASE: phase,
    DSA_SETTINGS_CREDENTIAL_SMOKE_PORT: String(port),
    DSA_SETTINGS_CREDENTIAL_SMOKE_LOCALAPPDATA: tempLocalAppData,
    DSA_SETTINGS_CREDENTIAL_SMOKE_VALUE: testValue,
  };
  delete env.ELECTRON_RUN_AS_NODE;
  return env;
}

function runPhase({ phase, port, tempLocalAppData, testValue, electronBinary }) {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(electronBinary, [path.join(__dirname, 'windowsSettingsCredentialSmokeElectron.js')], { cwd: path.resolve(__dirname, '..'), windowsHide: true, env: createChildEnvironment({ phase, port, tempLocalAppData, testValue }), stdio: ['ignore', 'pipe', 'pipe'] });
    } catch (_) { resolve(makeResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED })); return; }
    let stdout = ''; let settled = false;
    const finish = (result) => { if (!settled) { settled = true; clearTimeout(timer); resolve(result); } };
    const timer = setTimeout(() => { try { child.kill(); } catch (_) {} finish(makeResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_TIMEOUT })); }, TIMEOUT_MS);
    child.stdout.on('data', (chunk) => { stdout += chunk.toString('utf8'); if (Buffer.byteLength(stdout, 'utf8') > MAX_STDOUT) finish(makeResult(phase, { errorCode: ERROR_CODES.INVALID_RESULT })); });
    child.stderr.on('data', () => {});
    child.on('error', () => finish(makeResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED })));
    child.on('close', (code) => finish(code === 0 ? parseResult(stdout, phase) : makeResult(phase, { errorCode: ERROR_CODES.CHILD_PROCESS_FAILED })));
  });
}

async function runSmoke({ platform = process.platform } = {}) {
  if (platform !== 'win32') return { success: false, cleanupPassed: true, errorCode: ERROR_CODES.UNSUPPORTED_PLATFORM, stages: [] };
  if (isDistMissing()) return { success: false, cleanupPassed: true, errorCode: ERROR_CODES.WEB_DIST_MISSING, stages: [] };
  let electronBinary;
  try { electronBinary = resolveElectronBinary(); } catch (_) { return { success: false, cleanupPassed: true, errorCode: ERROR_CODES.ELECTRON_RESOLVE_FAILED, stages: [] }; }
  const port = await findPort();
  if (!port) return { success: false, cleanupPassed: true, errorCode: ERROR_CODES.PORT_UNAVAILABLE, stages: [] };
  let tempLocalAppData = ''; let server = null; const state = { secretLeak: false, testValue: `DSA_FAKE_${crypto.randomUUID()}_${crypto.randomUUID()}` };
  try { tempLocalAppData = fs.mkdtempSync(path.join(os.tmpdir(), SMOKE_TEMP_PREFIX)); if (!resolveSmokeTempLocalAppData(tempLocalAppData)) throw new Error('temp'); } catch (_) { return { success: false, cleanupPassed: false, errorCode: ERROR_CODES.TEMP_DIRECTORY_FAILED, stages: [] }; }
  const stages = []; let cleanupPassed = false;
  try {
    server = await startMockServer(port, state);
    for (const phase of PHASES) {
      const result = await runPhase({ phase, port, tempLocalAppData, testValue: state.testValue, electronBinary });
      const resultWithLeakCheck = {
        ...result,
        mockBackendSecretLeakFree: !state.secretLeak,
      };
      stages.push(resultWithLeakCheck);
      if (state.secretLeak || !resultWithLeakCheck.success) break;
      // The mock backend must never manufacture configured state; the page can
      // show configured only via the Electron IPC status overlay.
    }
  } catch (_) {
    stages.push(makeResult(stages.length ? PHASES[stages.length] : 'set', { errorCode: ERROR_CODES.MOCK_SERVER_FAILED }));
  } finally {
    state.testValue = '';
    if (server) await new Promise((resolve) => server.close(resolve));
    cleanupPassed = removeTempDir(tempLocalAppData);
  }
  if (state.secretLeak) return { success: false, cleanupPassed, errorCode: ERROR_CODES.MOCK_BACKEND_SECRET_LEAK, stages };
  const success = stages.length === 2 && stages.every((stage) => stage.success) && cleanupPassed;
  return { success, cleanupPassed, errorCode: success ? null : (stages.find((stage) => !stage.success)?.errorCode || (cleanupPassed ? ERROR_CODES.INVALID_RESULT : ERROR_CODES.CLEANUP_FAILED)), stages };
}

function printSummary(summary) {
  const set = summary.stages.find((s) => s.phase === 'set');
  const restart = summary.stages.find((s) => s.phase === 'restart-read-clear');
  const leakFree = summary.errorCode !== ERROR_CODES.MOCK_BACKEND_SECRET_LEAK
    && !summary.stages.some((stage) => stage.mockBackendSecretLeakFree === false);
  console.log(`Settings page set: ${set?.settingsPageSet ? 'PASS' : 'FAIL'}`);
  console.log(`Restart configured state: ${restart?.restartConfiguredState ? 'PASS' : 'FAIL'}`);
  console.log(`Plaintext not returned: ${restart?.plaintextNotReturned ? 'PASS' : 'FAIL'}`);
  console.log(`Settings page clear: ${restart?.settingsPageClear ? 'PASS' : 'FAIL'}`);
  console.log(`Mock backend secret leak check: ${leakFree ? 'PASS' : 'FAIL'}`);
  console.log(`Temp cleanup: ${summary.cleanupPassed ? 'PASS' : 'FAIL'}`);
  console.log(`App-M4.2.3B.1 ${summary.success ? 'PASS' : 'FAIL'}`);
  if (summary.errorCode) console.log(`errorCode: ${summary.errorCode}`);
}

if (require.main === module) runSmoke().then((s) => { printSummary(s); process.exitCode = s.success ? 0 : 1; }).catch(() => { printSummary({ success: false, cleanupPassed: false, errorCode: ERROR_CODES.INVALID_RESULT, stages: [] }); process.exitCode = 1; });
module.exports = { TEST_KEY, createChildEnvironment, findPort, makeAuthStatus, makeConfig, makeSetupStatus, printSummary, resolveChildSmokeTempLocalAppData, runSmoke, startMockServer };
