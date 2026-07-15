const path = require('node:path');
const { app, BrowserWindow } = require('electron');
const { bootstrapDesktopMain } = require('../credentialIpc');
const { ERROR_CODES, makeResult } = require('./windowsSettingsCredentialSmokeProtocol');
const { waitForLoad } = require('./windowsSettingsCredentialSmokePageLoad');
const { resolveChildSmokeTempLocalAppData } = require('./windowsSettingsCredentialSmokeController');

const TEST_KEY = 'APP_M423B1_TEST_TOKEN';
const phase = process.env.DSA_SETTINGS_CREDENTIAL_SMOKE_PHASE;
const port = Number(process.env.DSA_SETTINGS_CREDENTIAL_SMOKE_PORT || 0);
const testValue = process.env.DSA_SETTINGS_CREDENTIAL_SMOKE_VALUE || '';
const localAppData = resolveChildSmokeTempLocalAppData(
  process.env.DSA_SETTINGS_CREDENTIAL_SMOKE_LOCALAPPDATA,
  process.env,
);

if (localAppData) app.setPath('userData', path.join(localAppData, 'electron-user-data'));
bootstrapDesktopMain({ loadMain: () => undefined });

function clearEnv() {
  delete process.env.DSA_SETTINGS_CREDENTIAL_SMOKE_PHASE;
  delete process.env.DSA_SETTINGS_CREDENTIAL_SMOKE_PORT;
  delete process.env.DSA_SETTINGS_CREDENTIAL_SMOKE_VALUE;
  delete process.env.DSA_SETTINGS_CREDENTIAL_SMOKE_LOCALAPPDATA;
  delete process.env.LOCALAPPDATA;
}
function write(result) { process.stdout.write(`${JSON.stringify(result)}\n`); }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

async function runInPage(win, source, ...args) {
  return win.webContents.executeJavaScript(`(${source})(...${JSON.stringify(args)})`, true);
}


async function hasDesktopBridge(win) {
  try {
    return await runInPage(win, () => Boolean(
      window.dsaDesktop
      && typeof window.dsaDesktop.getCredentialStatus === 'function'
      && typeof window.dsaDesktop.setCredential === 'function'
      && typeof window.dsaDesktop.clearCredential === 'function',
    ));
  } catch (_error) {
    return false;
  }
}

async function waitForField(win) {
  try {
    const ok = await runInPage(win, async (key) => {
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline) {
        if (document.querySelector(`[data-testid="settings-field-${key}"]`)) return true;
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      return false;
    }, TEST_KEY);
    return ok ? null : ERROR_CODES.SETTINGS_FIELD_TIMEOUT;
  } catch (_error) {
    return ERROR_CODES.PAGE_AUTOMATION_FAILED;
  }
}


async function automateSet(win) {
  const fieldError = await waitForField(win);
  if (fieldError) return fieldError;
  const ok = await runInPage(win, async (key, value) => {
    const field = document.querySelector(`[data-testid="settings-field-${key}"]`);
    const input = document.querySelector(`[data-testid="settings-field-control-${key}"]`);
    if (!field || !input) return false;
    input.focus();
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 50));
    const save = [...document.querySelectorAll('button')].find((button) => /保存/.test(button.textContent || '') && !button.disabled);
    if (!save) return false;
    save.click();
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      const fresh = document.querySelector(`[data-testid="settings-field-${key}"]`);
      if (fresh && /已配置/.test(fresh.textContent || '')) return true;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return false;
  }, TEST_KEY, testValue);
  return ok ? null : ERROR_CODES.PAGE_AUTOMATION_FAILED;
}

async function automateRestartReadClear(win) {
  const fieldError = await waitForField(win);
  if (fieldError) return { errorCode: fieldError };
  return runInPage(win, async (key) => {
    const field = document.querySelector(`[data-testid="settings-field-${key}"]`);
    const input = document.querySelector(`[data-testid="settings-field-control-${key}"]`);
    if (!field || !input || !/已配置/.test(field.textContent || '') || input.value) {
      return { configured: false, plaintextAbsent: false, cleared: false };
    }
    const clear = [...field.querySelectorAll('button')].find((button) => /清除/.test(button.textContent || '') && !button.disabled);
    if (!clear) return { configured: true, plaintextAbsent: true, cleared: false };
    clear.click();
    await new Promise((resolve) => setTimeout(resolve, 100));
    const confirm = [...document.querySelectorAll('button')].find((button) => /确认清除/.test(button.textContent || '') && !button.disabled);
    if (!confirm) return { configured: true, plaintextAbsent: true, cleared: false };
    confirm.click();
    await new Promise((resolve) => setTimeout(resolve, 100));
    const save = [...document.querySelectorAll('button')].find((button) => /保存/.test(button.textContent || '') && !button.disabled);
    if (!save) return { configured: true, plaintextAbsent: true, cleared: false };
    save.click();
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      const fresh = document.querySelector(`[data-testid="settings-field-${key}"]`);
      if (fresh && /未配置/.test(fresh.textContent || '')) return { configured: true, plaintextAbsent: true, cleared: true };
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return { configured: true, plaintextAbsent: true, cleared: false };
  }, TEST_KEY);
}

async function run() {
  if (process.platform !== 'win32') return makeResult(phase || 'unknown', { errorCode: ERROR_CODES.UNSUPPORTED_PLATFORM });
  if (!localAppData || !port || !testValue || !['set', 'restart-read-clear'].includes(phase)) {
    return makeResult(phase || 'unknown', { errorCode: ERROR_CODES.INVALID_RESULT });
  }
  const win = new BrowserWindow({ show: false, webPreferences: { preload: path.join(__dirname, '..', 'preload.js'), contextIsolation: true, nodeIntegration: false } });
  try {
    const cacheBust = Date.now();
    const initialError = await waitForLoad(
      win,
      `http://127.0.0.1:${port}/?desktop_version=smoke&cache_bust=${cacheBust}`,
      ERROR_CODES.INITIAL_NAVIGATION_FAILED,
    );
    if (initialError) return makeResult(phase, { errorCode: initialError });
    const settingsError = await waitForLoad(
      win,
      `http://127.0.0.1:${port}/settings`,
      ERROR_CODES.SETTINGS_NAVIGATION_FAILED,
    );
    if (settingsError) return makeResult(phase, { errorCode: settingsError });
    await sleep(500);
    if (!await hasDesktopBridge(win)) {
      return makeResult(phase, { errorCode: ERROR_CODES.DESKTOP_BRIDGE_UNAVAILABLE });
    }
    if (phase === 'set') {
      const setError = await automateSet(win);
      const settingsPageSet = setError === null;
      return makeResult(phase, { success: settingsPageSet, settingsPageSet, plaintextNotReturned: true, errorCode: setError });
    }
    const result = await automateRestartReadClear(win);
    if (result.errorCode) return makeResult(phase, { errorCode: result.errorCode });
    const success = result.configured && result.plaintextAbsent && result.cleared;
    return makeResult(phase, { success, restartConfiguredState: result.configured, plaintextNotReturned: result.plaintextAbsent, settingsPageClear: result.cleared, errorCode: success ? null : (!result.plaintextAbsent ? ERROR_CODES.PLAINTEXT_RETURNED : result.configured ? ERROR_CODES.PAGE_CLEAR_FAILED : ERROR_CODES.RESTART_CONFIGURED_FAILED) });
  } catch (_) {
    return makeResult(phase, { errorCode: ERROR_CODES.PAGE_AUTOMATION_FAILED });
  } finally {
    try { win.destroy(); } catch (_) {}
  }
}

app.whenReady().then(run).then((result) => { clearEnv(); write(result); app.quit(); }).catch(() => { const failedPhase = phase || 'unknown'; clearEnv(); write(makeResult(failedPhase, { errorCode: ERROR_CODES.INVALID_RESULT })); app.exit(1); });
