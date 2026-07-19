const fs = require('fs');
const path = require('path');

const PORTABLE_UPDATE_MARKER_FILE = 'portable-update-handoff.json';
const PORTABLE_UPDATE_MARKER_ARG_PREFIX = '--dsa-portable-update-marker=';

function assertMarkerPath(appDir, markerPath) {
  if (!path.isAbsolute(appDir) || !path.isAbsolute(markerPath)) throw new Error('便携更新标记路径必须是绝对路径');
  const backupRoot = path.resolve(appDir, '.portable-update-backups');
  const resolvedMarker = path.resolve(markerPath);
  if (!resolvedMarker.startsWith(`${backupRoot}${path.sep}`) || path.basename(resolvedMarker) !== PORTABLE_UPDATE_MARKER_FILE) {
    throw new Error('便携更新标记必须位于受控恢复点目录');
  }
  return resolvedMarker;
}

function createPortableUpdateHealthMarker({ appDir, backupRoot, fsModule = fs }) {
  const markerPath = assertMarkerPath(appDir, path.join(backupRoot, PORTABLE_UPDATE_MARKER_FILE));
  fsModule.writeFileSync(markerPath, JSON.stringify({ version: 1, status: 'pending' }, null, 2));
  return markerPath;
}

function readPortableUpdateMarkerArg(argv = process.argv) {
  const value = argv.find((arg) => typeof arg === 'string' && arg.startsWith(PORTABLE_UPDATE_MARKER_ARG_PREFIX));
  return value ? value.slice(PORTABLE_UPDATE_MARKER_ARG_PREFIX.length) : '';
}

function markPortableUpdateHealthy({ appDir, markerPath = readPortableUpdateMarkerArg(), fsModule = fs }) {
  if (!markerPath) return false;
  const safeMarkerPath = assertMarkerPath(appDir, markerPath);
  const marker = JSON.parse(fsModule.readFileSync(safeMarkerPath, 'utf8'));
  if (!marker || marker.version !== 1 || marker.status !== 'pending') throw new Error('便携更新标记状态无效');
  fsModule.writeFileSync(safeMarkerPath, JSON.stringify({ ...marker, status: 'healthy', healthyAt: new Date().toISOString() }, null, 2));
  return true;
}

module.exports = {
  PORTABLE_UPDATE_MARKER_ARG_PREFIX,
  PORTABLE_UPDATE_MARKER_FILE,
  createPortableUpdateHealthMarker,
  markPortableUpdateHealthy,
  readPortableUpdateMarkerArg,
};
