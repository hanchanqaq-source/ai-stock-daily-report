const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const {
  DESKTOP_CLEAR_CREDENTIAL_CHANNEL,
  DESKTOP_CREDENTIAL_STATUS_CHANNEL,
  DESKTOP_SET_CREDENTIAL_CHANNEL,
  bootstrapDesktopMain,
  createCredentialIpcController,
  resolveTrustedBackendOrigin,
} = require('../credentialIpc');

function createHarness() {
  const appListeners = new Map();
  const handlers = new Map();
  const navigationListeners = new Map();
  const closedListeners = [];
  const app = {
    on(name, listener) {
      appListeners.set(name, listener);
    },
  };
  const ipcMain = {
    handle(name, listener) {
      handlers.set(name, listener);
    },
  };
  const mainFrame = { url: '', parent: null };
  const webContents = {
    mainFrame,
    on(name, listener) {
      navigationListeners.set(name, listener);
    },
  };
  const windowRef = {
    webContents,
    isDestroyed: () => false,
    once(name, listener) {
      if (name === 'closed') closedListeners.push(listener);
    },
  };
  const calls = [];
  const credentialStore = {
    getCredentialStatus(key) {
      calls.push(['status', key]);
      return { success: true, configured: true, supported: true };
    },
    setCredential(key, value) {
      calls.push(['set', key, value]);
      return { success: true, configured: true, supported: true };
    },
    clearCredential(key) {
      calls.push(['clear', key]);
      return { success: true, configured: false, supported: true };
    },
  };
  const rendererRoot = path.resolve('/tmp/dsa-renderer');
  const controller = createCredentialIpcController({
    app,
    ipcMain,
    credentialStore,
    rendererRoot,
  });
  controller.register();
  appListeners.get('browser-window-created')({}, windowRef);
  return {
    app,
    handlers,
    navigationListeners,
    windowRef,
    webContents,
    mainFrame,
    calls,
    rendererRoot,
    controller,
    close: () => closedListeners.forEach((listener) => listener()),
  };
}

function makeMainFrameEvent(harness, url) {
  harness.mainFrame.url = url;
  return {
    sender: harness.webContents,
    senderFrame: harness.mainFrame,
  };
}

test('trusted backend origin requires the exact desktop startup URL contract', () => {
  assert.equal(
    resolveTrustedBackendOrigin('http://127.0.0.1:8000/?desktop_version=3.21.0&cache_bust=123'),
    'http://127.0.0.1:8000',
  );
  for (const candidate of [
    'http://127.0.0.1:7999/?desktop_version=3.21.0&cache_bust=123',
    'http://127.0.0.1:8000/settings?desktop_version=3.21.0&cache_bust=123',
    'http://localhost:8000/?desktop_version=3.21.0&cache_bust=123',
    'https://127.0.0.1:8000/?desktop_version=3.21.0&cache_bust=123',
    'http://user@127.0.0.1:8000/?desktop_version=3.21.0&cache_bust=123',
    'http://127.0.0.1:8000/?desktop_version=3.21.0',
    'http://127.0.0.1:8000/?desktop_version=3.21.0&cache_bust=not-a-number',
  ]) {
    assert.equal(resolveTrustedBackendOrigin(candidate), '', candidate);
  }
});

test('credential IPC allows only the registered BrowserWindow main frame and exact captured origin', () => {
  const harness = createHarness();
  const beforeCapture = makeMainFrameEvent(harness, 'http://127.0.0.1:8000/settings');
  assert.equal(harness.controller.isAllowedDesktopIpcSource(beforeCapture), false);

  harness.navigationListeners.get('did-start-navigation')(
    {},
    'http://127.0.0.1:8000/?desktop_version=3.21.0&cache_bust=123',
    false,
    true,
  );
  assert.equal(harness.controller.getTrustedBackendOrigin(), 'http://127.0.0.1:8000');
  assert.equal(
    harness.controller.isAllowedDesktopIpcSource(
      makeMainFrameEvent(harness, 'http://127.0.0.1:8000/settings'),
    ),
    true,
  );
  assert.equal(
    harness.controller.isAllowedDesktopIpcSource(
      makeMainFrameEvent(harness, 'http://127.0.0.1:8001/settings'),
    ),
    false,
  );

  const foreignSender = {
    sender: { mainFrame: harness.mainFrame },
    senderFrame: harness.mainFrame,
  };
  assert.equal(harness.controller.isAllowedDesktopIpcSource(foreignSender), false);

  const childFrame = {
    url: 'http://127.0.0.1:8000/settings',
    parent: harness.mainFrame,
  };
  assert.equal(
    harness.controller.isAllowedDesktopIpcSource({
      sender: harness.webContents,
      senderFrame: childFrame,
    }),
    false,
  );
});

test('packaged renderer files are allowed only inside the registered renderer root', () => {
  const harness = createHarness();
  const trustedUrl = pathToFileURL(path.join(harness.rendererRoot, 'loading.html')).href;
  const outsideUrl = pathToFileURL(path.resolve('/tmp/not-renderer/loading.html')).href;
  assert.equal(
    harness.controller.isAllowedDesktopIpcSource(makeMainFrameEvent(harness, trustedUrl)),
    true,
  );
  assert.equal(
    harness.controller.isAllowedDesktopIpcSource(makeMainFrameEvent(harness, outsideUrl)),
    false,
  );
});

test('credential handlers enforce exact payload shapes and never echo submitted values', () => {
  const harness = createHarness();
  const event = makeMainFrameEvent(
    harness,
    pathToFileURL(path.join(harness.rendererRoot, 'loading.html')).href,
  );

  const setResult = harness.handlers.get(DESKTOP_SET_CREDENTIAL_CHANNEL)(event, {
    key: 'OPENAI_API_KEY',
    value: 'fake-token-for-unit-test',
  });
  assert.equal(setResult.success, true);
  assert.equal(Object.prototype.hasOwnProperty.call(setResult, 'value'), false);
  assert.deepEqual(harness.calls.at(-1), ['set', 'OPENAI_API_KEY', 'fake-token-for-unit-test']);

  assert.equal(
    harness.handlers.get(DESKTOP_CREDENTIAL_STATUS_CHANNEL)(event, {
      key: 'OPENAI_API_KEY',
      extra: true,
    }).errorCode,
    'invalid_payload',
  );
  assert.equal(
    harness.handlers.get(DESKTOP_SET_CREDENTIAL_CHANNEL)(event, {
      key: 'OPENAI_API_KEY',
      value: '',
    }).errorCode,
    'invalid_payload',
  );
  assert.equal(
    harness.handlers.get(DESKTOP_CLEAR_CREDENTIAL_CHANNEL)(event, {
      key: 'OPENAI_API_KEY',
      value: 'fake-token-for-unit-test',
    }).errorCode,
    'invalid_payload',
  );
  assert.equal(
    harness.handlers.get(DESKTOP_CREDENTIAL_STATUS_CHANNEL)(
      { sender: harness.webContents, senderFrame: { url: 'https://example.com', parent: null } },
      { key: 'OPENAI_API_KEY' },
    ).errorCode,
    'forbidden_source',
  );
});

test('bootstrap registers credential IPC before loading the existing desktop main module', () => {
  const order = [];
  const app = {
    on(name) {
      order.push(`app:${name}`);
    },
  };
  const ipcMain = {
    handle(name) {
      order.push(`ipc:${name}`);
    },
  };
  bootstrapDesktopMain({
    electron: {
      app,
      ipcMain,
      safeStorage: {
        isEncryptionAvailable: () => false,
      },
    },
    loadMain: () => {
      order.push('load-main');
    },
  });
  assert.equal(order.at(-1), 'load-main');
  assert.ok(order.indexOf(`ipc:${DESKTOP_CREDENTIAL_STATUS_CHANNEL}`) < order.indexOf('load-main'));
  assert.ok(order.indexOf(`ipc:${DESKTOP_SET_CREDENTIAL_CHANNEL}`) < order.indexOf('load-main'));
  assert.ok(order.indexOf(`ipc:${DESKTOP_CLEAR_CREDENTIAL_CHANNEL}`) < order.indexOf('load-main'));
});
