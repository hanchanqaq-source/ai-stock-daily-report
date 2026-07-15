const DEFAULT_LOAD_TIMEOUT_MS = 15000;

function normalizeUrl(candidate) {
  if (typeof candidate !== 'string' || !candidate.trim()) return '';
  try {
    return new URL(candidate).href;
  } catch (_error) {
    return '';
  }
}

function isTargetMainFrameFailure(targetUrl, eventUrl, isMainFrame) {
  if (isMainFrame === false) return false;
  return normalizeUrl(eventUrl) === targetUrl;
}

function waitForLoad(win, url, errorCode, { timeoutMs = DEFAULT_LOAD_TIMEOUT_MS } = {}) {
  return new Promise((resolve) => {
    const targetUrl = normalizeUrl(url);
    let settled = false;
    let timer = null;
    const cleanup = () => {
      if (timer) clearTimeout(timer);
      win.webContents.removeListener('did-fail-load', onFail);
      win.webContents.removeListener('did-finish-load', onFinish);
      win.webContents.removeListener('dom-ready', onDomReady);
    };
    const finish = (ok) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(ok ? null : errorCode);
    };
    const onFail = (_event, _errorCode, _errorDescription, validatedURL, isMainFrame) => {
      if (isTargetMainFrameFailure(targetUrl, validatedURL, isMainFrame)) finish(false);
    };
    const onFinish = () => {
      // Observed only for cleanup; success is tied to the loadURL promise for this target.
    };
    const onDomReady = () => {
      // Observe DOM readiness for stage diagnostics without emitting browser details.
    };

    win.webContents.on('did-fail-load', onFail);
    win.webContents.once('did-finish-load', onFinish);
    win.webContents.once('dom-ready', onDomReady);
    timer = setTimeout(() => finish(false), timeoutMs);

    try {
      Promise.resolve(win.loadURL(url)).then(() => finish(true), () => finish(false));
    } catch (_error) {
      finish(false);
    }
  });
}

module.exports = {
  DEFAULT_LOAD_TIMEOUT_MS,
  isTargetMainFrameFailure,
  normalizeUrl,
  waitForLoad,
};
