const DEFAULT_ROUTE_TIMEOUT_MS = 15000;

function makeSettingsRouteScript(timeoutMs) {
  return `(() => new Promise((resolve) => {
    const deadline = Date.now() + ${Number(timeoutMs)};
    const finishIfReady = () => {
      if (window.location && window.location.pathname === '/settings') {
        resolve(true);
        return true;
      }
      return false;
    };
    if (finishIfReady()) return;
    window.history.pushState({}, '', '/settings');
    window.dispatchEvent(new PopStateEvent('popstate'));
    const timer = window.setInterval(() => {
      if (finishIfReady()) {
        window.clearInterval(timer);
        return;
      }
      if (Date.now() >= deadline) {
        window.clearInterval(timer);
        resolve(false);
      }
    }, 50);
  }))()`;
}

async function switchToSettingsRoute(win, errorCode, { timeoutMs = DEFAULT_ROUTE_TIMEOUT_MS } = {}) {
  try {
    const routed = await win.webContents.executeJavaScript(makeSettingsRouteScript(timeoutMs), true);
    return routed === true ? null : errorCode;
  } catch (_error) {
    return errorCode;
  }
}

module.exports = {
  DEFAULT_ROUTE_TIMEOUT_MS,
  makeSettingsRouteScript,
  switchToSettingsRoute,
};
