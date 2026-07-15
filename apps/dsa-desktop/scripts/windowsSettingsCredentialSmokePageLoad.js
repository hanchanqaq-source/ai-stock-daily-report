const DEFAULT_LOAD_TIMEOUT_MS = 15000;

function waitForLoad(win, url, errorCode, { timeoutMs = DEFAULT_LOAD_TIMEOUT_MS } = {}) {
  return new Promise((resolve) => {
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
    const onFail = (_event, _errorCode, _errorDescription, _validatedURL, isMainFrame) => {
      if (isMainFrame !== false) finish(false);
    };
    const onFinish = () => finish(true);
    const onDomReady = () => {
      // Observe DOM readiness for stage diagnostics without emitting browser details.
    };

    win.webContents.on('did-fail-load', onFail);
    win.webContents.once('did-finish-load', onFinish);
    win.webContents.once('dom-ready', onDomReady);
    timer = setTimeout(() => finish(false), timeoutMs);

    try {
      Promise.resolve(win.loadURL(url)).catch(() => finish(false));
    } catch (_error) {
      finish(false);
    }
  });
}

module.exports = {
  DEFAULT_LOAD_TIMEOUT_MS,
  waitForLoad,
};
