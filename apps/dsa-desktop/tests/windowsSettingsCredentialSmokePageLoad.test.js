const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { isTargetMainFrameFailure, normalizeUrl, waitForLoad } = require('../scripts/windowsSettingsCredentialSmokePageLoad');

function assertNoListeners(webContents) {
  assert.equal(webContents.listenerCount('did-fail-load'), 0);
  assert.equal(webContents.listenerCount('did-finish-load'), 0);
  assert.equal(webContents.listenerCount('dom-ready'), 0);
}

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
  assertNoListeners(webContents);
});

test('settings credential smoke waitForLoad cleans listeners after target loadURL resolves', async () => {
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
  assertNoListeners(webContents);
});

test('settings credential smoke waitForLoad ignores late cancel from previous navigation', async () => {
  const webContents = new EventEmitter();
  const targetUrl = 'http://127.0.0.1:8000/settings';
  const previousUrl = 'http://127.0.0.1:8000/?desktop_version=smoke&cache_bust=1';
  const win = {
    webContents,
    loadURL() {
      queueMicrotask(() => {
        webContents.emit('did-fail-load', {}, -3, '', previousUrl, true);
      });
      return new Promise((resolve) => setTimeout(resolve, 10));
    },
  };

  const result = await waitForLoad(win, targetUrl, 'settings_navigation_failed', { timeoutMs: 50 });

  assert.equal(result, null);
  assertNoListeners(webContents);
});

test('settings credential smoke waitForLoad fails only on target main-frame failures', async () => {
  const webContents = new EventEmitter();
  const targetUrl = 'http://127.0.0.1:8000/settings';
  const win = {
    webContents,
    loadURL() {
      queueMicrotask(() => {
        webContents.emit('did-fail-load', {}, -105, '', targetUrl, true);
      });
      return new Promise(() => undefined);
    },
  };

  const result = await waitForLoad(win, targetUrl, 'settings_navigation_failed', { timeoutMs: 50 });

  assert.equal(result, 'settings_navigation_failed');
  assertNoListeners(webContents);
});

test('settings credential smoke waitForLoad ignores subframe failures for the target URL', async () => {
  const webContents = new EventEmitter();
  const targetUrl = 'http://127.0.0.1:8000/settings';
  const win = {
    webContents,
    loadURL() {
      queueMicrotask(() => {
        webContents.emit('did-fail-load', {}, -105, '', targetUrl, false);
      });
      return new Promise((resolve) => setTimeout(resolve, 10));
    },
  };

  const result = await waitForLoad(win, targetUrl, 'settings_navigation_failed', { timeoutMs: 50 });

  assert.equal(result, null);
  assertNoListeners(webContents);
});

test('settings credential smoke target failure matcher requires exact normalized URL and main frame', () => {
  const target = normalizeUrl('http://127.0.0.1:8000/settings');
  assert.equal(isTargetMainFrameFailure(target, 'http://127.0.0.1:8000/settings', true), true);
  assert.equal(isTargetMainFrameFailure(target, 'http://127.0.0.1:8000/', true), false);
  assert.equal(isTargetMainFrameFailure(target, 'http://127.0.0.1:8000/settings', false), false);
});
