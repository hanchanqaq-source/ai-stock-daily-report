const path = require('node:path');
const { spawn } = require('node:child_process');

const ERROR_CODES = Object.freeze({
  ELECTRON_RESOLVE_FAILED: 'electron_resolve_failed',
  ELECTRON_READY_SPAWN_FAILED: 'electron_ready_spawn_failed',
  ELECTRON_READY_EXIT_FAILED: 'electron_ready_exit_failed',
  ELECTRON_READY_TIMEOUT: 'electron_ready_timeout',
  CONTROLLER_SPAWN_FAILED: 'smoke_controller_spawn_failed',
  CONTROLLER_FAILED_AFTER_READY: 'smoke_controller_failed_after_electron_ready',
  UNHANDLED_FAILURE: 'preflight_unhandled_failure',
});

const PREFLIGHT_TIMEOUT_MS = 15000;

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

function createElectronEnvironment(source = process.env) {
  const env = { ...source };
  delete env.ELECTRON_RUN_AS_NODE;
  return env;
}

function runElectronReadyPreflight({
  electronBinary,
  spawnFn = spawn,
  timeoutMs = PREFLIGHT_TIMEOUT_MS,
} = {}) {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawnFn(
        electronBinary,
        [path.join(__dirname, 'windowsCredentialSmokePreflightElectron.js')],
        {
          cwd: path.resolve(__dirname, '..'),
          windowsHide: true,
          env: createElectronEnvironment(),
          stdio: ['ignore', 'ignore', 'pipe'],
        },
      );
    } catch (_error) {
      resolve(ERROR_CODES.ELECTRON_READY_SPAWN_FAILED);
      return;
    }

    let settled = false;
    let timer = null;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      resolve(result);
    };

    timer = setTimeout(() => {
      try {
        child.kill();
      } catch (_error) {
        // Best effort only; never print local diagnostics.
      }
      finish(ERROR_CODES.ELECTRON_READY_TIMEOUT);
    }, timeoutMs);

    child.stderr.on('data', () => {
      // Consume but never print Electron diagnostics because they may contain local paths.
    });
    child.on('error', () => finish(ERROR_CODES.ELECTRON_READY_SPAWN_FAILED));
    child.on('close', (code) => {
      finish(code === 0 ? null : ERROR_CODES.ELECTRON_READY_EXIT_FAILED);
    });
  });
}

function runController({ spawnFn = spawn } = {}) {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawnFn(
        process.execPath,
        [path.join(__dirname, 'windowsCredentialSmokeController.js')],
        {
          cwd: path.resolve(__dirname, '..'),
          windowsHide: true,
          env: { ...process.env },
          stdio: 'inherit',
        },
      );
    } catch (_error) {
      resolve(ERROR_CODES.CONTROLLER_SPAWN_FAILED);
      return;
    }

    child.on('error', () => resolve(ERROR_CODES.CONTROLLER_SPAWN_FAILED));
    child.on('close', (code) => {
      resolve(code === 0 ? null : ERROR_CODES.CONTROLLER_FAILED_AFTER_READY);
    });
  });
}

function printFixedFailure(errorCode) {
  console.log('========================================');
  console.log('Windows DPAPI credential smoke preflight');
  console.log('========================================');
  console.log('FAIL');
  console.log(`errorCode: ${errorCode}`);
}

async function main() {
  let electronBinary;
  try {
    electronBinary = resolveElectronBinary();
  } catch (_error) {
    printFixedFailure(ERROR_CODES.ELECTRON_RESOLVE_FAILED);
    process.exitCode = 1;
    return;
  }

  if (!electronBinary) {
    printFixedFailure(ERROR_CODES.ELECTRON_RESOLVE_FAILED);
    process.exitCode = 1;
    return;
  }

  console.log('[CHECK] Electron app readiness preflight');
  const preflightError = await runElectronReadyPreflight({ electronBinary });
  if (preflightError) {
    printFixedFailure(preflightError);
    process.exitCode = 1;
    return;
  }
  console.log('[OK] Electron app readiness preflight passed');

  const controllerError = await runController();
  if (controllerError) {
    console.log(`[DIAGNOSTIC] ${controllerError}`);
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main().catch(() => {
    printFixedFailure(ERROR_CODES.UNHANDLED_FAILURE);
    process.exitCode = 1;
  });
}

module.exports = {
  ERROR_CODES,
  PREFLIGHT_TIMEOUT_MS,
  createElectronEnvironment,
  printFixedFailure,
  resolveElectronBinary,
  runController,
  runElectronReadyPreflight,
};
