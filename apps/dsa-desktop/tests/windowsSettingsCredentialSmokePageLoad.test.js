const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { waitForLoad } = require('../scripts/windowsSettingsCredentialSmokePageLoad');

test('settings credential smoke waitForLoad times out with stage error and cleans listeners', async () => {
  const webContents = new EventEmitter();
  const win = {
    webContents,
    loadURL() {
      return new Promise(() => undefined);
    },
  };

  const result = await waitForLoad(win, 'http://127.0.0.1:8000/settings', 'settings_navigation_failed', { timeoutMs: 5 });

  assert.equal(result, 'settings_navigation_failed');
  assert.equal(webContents.listenerCount('did-fail-load'), 0);
  assert.equal(webContents.listenerCount('did-finish-load'), 0);
  assert.equal(webContents.listenerCount('dom-ready'), 0);
});

test('settings credential smoke waitForLoad cleans listeners after successful finish', async () => {
  const webContents = new EventEmitter();
  const win = {
    webContents,
    loadURL() {
      queueMicrotask(() => webContents.emit('did-finish-load'));
      return Promise.resolve();
    },
  };

  const result = await waitForLoad(win, 'http://127.0.0.1:8000/', 'initial_navigation_failed', { timeoutMs: 50 });

  assert.equal(result, null);
  assert.equal(webContents.listenerCount('did-fail-load'), 0);
  assert.equal(webContents.listenerCount('did-finish-load'), 0);
  assert.equal(webContents.listenerCount('dom-ready'), 0);
});
