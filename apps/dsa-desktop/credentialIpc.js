const path = require('path');
const { fileURLToPath } = require('url');
const { createSecureCredentialStore } = require('./secureCredentialStore');

const DESKTOP_CREDENTIAL_STATUS_CHANNEL = 'desktop:credential-status';
const DESKTOP_SET_CREDENTIAL_CHANNEL = 'desktop:set-credential';
const DESKTOP_CLEAR_CREDENTIAL_CHANNEL = 'desktop:clear-credential';
const BACKEND_PORT_MIN = 8000;
const BACKEND_PORT_MAX = 8100;

function rejectCredentialIpc(errorCode = 'forbidden_source') {
  return {
    success: false,
    configured: false,
    supported: false,
    errorCode,
  };
}

function hasExactObjectKeys(payload, expectedKeys) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return false;
  }
  const keys = Object.keys(payload).sort();
  const expected = [...expectedKeys].sort();
  return keys.length === expected.length && keys.every((key, index) => key === expected[index]);
}

function resolveTrustedBackendOrigin(candidateUrl) {
  try {
    const parsed = new URL(candidateUrl);
    const port = Number.parseInt(parsed.port, 10);
    const cacheBust = parsed.searchParams.get('cache_bust') || '';
    if (
      parsed.protocol !== 'http:'
      || parsed.hostname !== '127.0.0.1'
      || parsed.username
      || parsed.password
      || !Number.isInteger(port)
      || port < BACKEND_PORT_MIN
      || port > BACKEND_PORT_MAX
      || parsed.pathname !== '/'
      || !parsed.searchParams.has('desktop_version')
      || !/^\d+$/.test(cacheBust)
    ) {
      return '';
    }
    return parsed.origin;
  } catch (_error) {
    return '';
  }
}

function isTrustedRendererFileUrl(candidateUrl, rendererRoot) {
  try {
    const parsed = new URL(candidateUrl);
    if (parsed.protocol !== 'file:') {
      return false;
    }
    const framePath = path.resolve(fileURLToPath(parsed));
    const relative = path.relative(rendererRoot, framePath);
    return Boolean(relative)
      && relative !== '..'
      && !relative.startsWith(`..${path.sep}`)
      && !path.isAbsolute(relative);
  } catch (_error) {
    return false;
  }
}

function createCredentialIpcController({
  app,
  ipcMain,
  safeStorage,
  credentialStore,
  rendererRoot = path.resolve(__dirname, 'renderer'),
} = {}) {
  const store = credentialStore || createSecureCredentialStore({ safeStorage });
  let trustedWindow = null;
  let trustedBackendOrigin = '';
  let registered = false;

  function rememberTrustedWindow(windowRef) {
    if (!windowRef || !windowRef.webContents) {
      return;
    }
    if (trustedWindow && trustedWindow !== windowRef && !trustedWindow.isDestroyed?.()) {
      return;
    }

    trustedWindow = windowRef;
    trustedBackendOrigin = '';
    const webContents = windowRef.webContents;

    webContents.on('did-start-navigation', (_event, url, _isInPlace, isMainFrame) => {
      if (!isMainFrame || trustedBackendOrigin) {
        return;
      }
      const resolvedOrigin = resolveTrustedBackendOrigin(url);
      if (resolvedOrigin) {
        trustedBackendOrigin = resolvedOrigin;
      }
    });

    windowRef.once('closed', () => {
      if (trustedWindow === windowRef) {
        trustedWindow = null;
        trustedBackendOrigin = '';
      }
    });
  }

  function isAllowedDesktopIpcSource(event) {
    if (!trustedWindow || trustedWindow.isDestroyed?.()) {
      return false;
    }
    const webContents = trustedWindow.webContents;
    const senderFrame = event && event.senderFrame;
    if (!event || event.sender !== webContents || !senderFrame) {
      return false;
    }
    if (webContents.mainFrame && senderFrame !== webContents.mainFrame) {
      return false;
    }
    if (senderFrame.parent) {
      return false;
    }

    const frameUrl = typeof senderFrame.url === 'string' ? senderFrame.url : '';
    if (!frameUrl) {
      return false;
    }
    if (isTrustedRendererFileUrl(frameUrl, rendererRoot)) {
      return true;
    }
    if (!trustedBackendOrigin) {
      return false;
    }
    try {
      const parsed = new URL(frameUrl);
      return parsed.protocol === 'http:' && parsed.origin === trustedBackendOrigin;
    } catch (_error) {
      return false;
    }
  }

  function handleCredentialStatus(event, payload) {
    if (!isAllowedDesktopIpcSource(event)) {
      return rejectCredentialIpc();
    }
    if (!hasExactObjectKeys(payload, ['key']) || typeof payload.key !== 'string') {
      return rejectCredentialIpc('invalid_payload');
    }
    return store.getCredentialStatus(payload.key);
  }

  function handleSetCredential(event, payload) {
    if (!isAllowedDesktopIpcSource(event)) {
      return rejectCredentialIpc();
    }
    if (
      !hasExactObjectKeys(payload, ['key', 'value'])
      || typeof payload.key !== 'string'
      || typeof payload.value !== 'string'
      || payload.value.length === 0
    ) {
      return rejectCredentialIpc('invalid_payload');
    }
    return store.setCredential(payload.key, payload.value);
  }

  function handleClearCredential(event, payload) {
    if (!isAllowedDesktopIpcSource(event)) {
      return rejectCredentialIpc();
    }
    if (!hasExactObjectKeys(payload, ['key']) || typeof payload.key !== 'string') {
      return rejectCredentialIpc('invalid_payload');
    }
    return store.clearCredential(payload.key);
  }

  function register() {
    if (registered) {
      return;
    }
    registered = true;
    app.on('browser-window-created', (_event, windowRef) => {
      rememberTrustedWindow(windowRef);
    });
    ipcMain.handle(DESKTOP_CREDENTIAL_STATUS_CHANNEL, handleCredentialStatus);
    ipcMain.handle(DESKTOP_SET_CREDENTIAL_CHANNEL, handleSetCredential);
    ipcMain.handle(DESKTOP_CLEAR_CREDENTIAL_CHANNEL, handleClearCredential);
  }

  return {
    register,
    rememberTrustedWindow,
    isAllowedDesktopIpcSource,
    handleCredentialStatus,
    handleSetCredential,
    handleClearCredential,
    getTrustedBackendOrigin: () => trustedBackendOrigin,
  };
}

function bootstrapDesktopMain({
  electron = require('electron'),
  loadMain = () => require('./main.js'),
} = {}) {
  const controller = createCredentialIpcController({
    app: electron.app,
    ipcMain: electron.ipcMain,
    safeStorage: electron.safeStorage,
  });
  controller.register();
  loadMain();
  return controller;
}

module.exports = {
  BACKEND_PORT_MAX,
  BACKEND_PORT_MIN,
  DESKTOP_CLEAR_CREDENTIAL_CHANNEL,
  DESKTOP_CREDENTIAL_STATUS_CHANNEL,
  DESKTOP_SET_CREDENTIAL_CHANNEL,
  bootstrapDesktopMain,
  createCredentialIpcController,
  hasExactObjectKeys,
  isTrustedRendererFileUrl,
  rejectCredentialIpc,
  resolveTrustedBackendOrigin,
};
