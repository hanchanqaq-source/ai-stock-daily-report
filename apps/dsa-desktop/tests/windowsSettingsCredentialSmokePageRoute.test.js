const test = require('node:test');
const assert = require('node:assert/strict');
const { makeSettingsRouteScript, switchToSettingsRoute } = require('../scripts/windowsSettingsCredentialSmokePageRoute');

test('settings credential smoke route script uses History API and verifies /settings', () => {
  const script = makeSettingsRouteScript(15000);
  assert.match(script, /history\.pushState\(\{\}, '', '\/settings'\)/);
  assert.match(script, /PopStateEvent\('popstate'\)/);
  assert.match(script, /pathname === '\/settings'/);
});

test('settings credential smoke route switch returns null after successful SPA routing', async () => {
  const win = {
    webContents: {
      executeJavaScript(script) {
        assert.match(script, /\/settings/);
        return Promise.resolve(true);
      },
    },
  };

  const result = await switchToSettingsRoute(win, 'settings_navigation_failed', { timeoutMs: 5 });

  assert.equal(result, null);
});

test('settings credential smoke route switch returns settings error on timeout', async () => {
  const win = {
    webContents: {
      executeJavaScript() {
        return Promise.resolve(false);
      },
    },
  };

  const result = await switchToSettingsRoute(win, 'settings_navigation_failed', { timeoutMs: 5 });

  assert.equal(result, 'settings_navigation_failed');
});
