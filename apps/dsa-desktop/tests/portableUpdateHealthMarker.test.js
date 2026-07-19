const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { createPortableUpdateHealthMarker, markPortableUpdateHealthy, readPortableUpdateMarkerArg, readPortableUpdateOutcome, readPortableUpdateOutcomeArg } = require('../portableUpdateHealthMarker');

test('portable health marker is restricted to a recovery point and records backend readiness', () => {
  const appDir = fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-portable-health-'));
  const backupRoot = path.join(appDir, '.portable-update-backups', 'update-1');
  fs.mkdirSync(backupRoot, { recursive: true });
  const markerPath = createPortableUpdateHealthMarker({ appDir, backupRoot });
  assert.equal(markPortableUpdateHealthy({ appDir, markerPath }), true);
  assert.equal(JSON.parse(fs.readFileSync(markerPath, 'utf8')).status, 'healthy');
  assert.equal(readPortableUpdateOutcome({ appDir, markerPath }), 'healthy');
  assert.throws(() => markPortableUpdateHealthy({ appDir, markerPath: path.join(appDir, 'data', 'marker.json') }));
});

test('portable health marker reads only the dedicated startup argument', () => {
  assert.equal(readPortableUpdateMarkerArg(['electron', '--dsa-portable-update-marker=C:\\safe\\portable-update-handoff.json']), 'C:\\safe\\portable-update-handoff.json');
  assert.equal(readPortableUpdateOutcomeArg(['electron', '--dsa-portable-update-outcome=C:\\safe\\portable-update-handoff.json']), 'C:\\safe\\portable-update-handoff.json');
  assert.equal(readPortableUpdateMarkerArg(['electron', '--unrelated=1']), '');
});
