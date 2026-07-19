const assert = require('node:assert/strict');
const test = require('node:test');
const { buildWindowsPortableUpdateHelper } = require('../portableUpdateHandoff');

test('Windows portable helper waits, extracts, preserves user directories, validates startup, and rolls back', () => {
  const script = buildWindowsPortableUpdateHelper({ appDir: 'C:\\portable', zipPath: 'C:\\downloads\\new.zip', expectedHash: 'a'.repeat(64), stageRoot: 'C:\\temp\\new', backupRoot: 'C:\\portable\\.portable-update-backups\\x', markerPath: 'C:\\portable\\.portable-update-backups\\x\\portable-update-handoff.json', exePath: 'C:\\portable\\股票基金质量分析系统.exe', parentPid: 42 });
  assert.match(script, /while \(Get-Process/);
  assert.match(script, /Expand-Archive -LiteralPath/);
  assert.match(script, /Get-FileHash -LiteralPath/);
  assert.match(script, /archive layout is invalid after extraction/);
  assert.match(script, /'data','config','logs','plugins'/);
  assert.match(script, /updated process did not report backend health/);
  assert.match(script, /Stop-Process/);
  assert.match(script, /catch/);
});

test('Windows portable helper rejects relative paths and invalid parent PID', () => {
  assert.throws(() => buildWindowsPortableUpdateHelper({ appDir: 'relative', zipPath: 'C:\\new.zip', expectedHash: 'a'.repeat(64), stageRoot: 'C:\\temp', backupRoot: 'C:\\backup', markerPath: 'C:\\backup\\portable-update-handoff.json', exePath: 'C:\\app.exe', parentPid: 1 }));
  assert.throws(() => buildWindowsPortableUpdateHelper({ appDir: 'C:\\app', zipPath: 'C:\\new.zip', expectedHash: 'a'.repeat(64), stageRoot: 'C:\\temp', backupRoot: 'C:\\backup', markerPath: 'C:\\backup\\portable-update-handoff.json', exePath: 'C:\\app.exe', parentPid: 0 }));
  assert.throws(() => buildWindowsPortableUpdateHelper({ appDir: 'C:\\app', zipPath: 'C:\\new.zip', expectedHash: 'not-a-hash', stageRoot: 'C:\\temp', backupRoot: 'C:\\backup', markerPath: 'C:\\backup\\portable-update-handoff.json', exePath: 'C:\\app.exe', parentPid: 1 }));
});
