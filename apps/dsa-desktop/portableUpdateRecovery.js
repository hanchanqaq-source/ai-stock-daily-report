const fs = require('fs');
const path = require('path');

const PRESERVED_PORTABLE_DIRECTORIES = new Set([
  'data',
  'config',
  'logs',
  'plugins',
  '.portable-update-backups',
]);

function listReplaceableProgramEntries(appDir, fsModule = fs) {
  return fsModule.readdirSync(appDir, { withFileTypes: true })
    .map((entry) => entry.name)
    .filter((name) => !PRESERVED_PORTABLE_DIRECTORIES.has(name));
}

function createPortableUpdateRecoveryPoint({ appDir, backupRoot, fsModule = fs }) {
  if (!path.isAbsolute(appDir) || !path.isAbsolute(backupRoot)) {
    throw new Error('便携更新恢复点路径必须是绝对路径');
  }
  if (path.resolve(backupRoot).startsWith(`${path.resolve(appDir)}${path.sep}`) === false) {
    throw new Error('便携更新恢复点必须保存在程序目录内');
  }

  const entries = listReplaceableProgramEntries(appDir, fsModule);
  fsModule.mkdirSync(backupRoot, { recursive: true });
  for (const name of entries) {
    fsModule.cpSync(path.join(appDir, name), path.join(backupRoot, name), {
      recursive: true,
      force: true,
      errorOnExist: false,
    });
  }
  const manifest = { version: 1, entries, preservedDirectories: [...PRESERVED_PORTABLE_DIRECTORIES] };
  fsModule.writeFileSync(path.join(backupRoot, 'portable-update-recovery.json'), JSON.stringify(manifest, null, 2));
  return manifest;
}

function restorePortableUpdateRecoveryPoint({ appDir, backupRoot, fsModule = fs }) {
  const manifestPath = path.join(backupRoot, 'portable-update-recovery.json');
  const manifest = JSON.parse(fsModule.readFileSync(manifestPath, 'utf8'));
  if (!Array.isArray(manifest.entries) || manifest.entries.some((name) => typeof name !== 'string' || !name || name.includes('/') || name.includes('\\'))) {
    throw new Error('便携更新恢复点清单无效');
  }
  for (const name of manifest.entries) {
    fsModule.cpSync(path.join(backupRoot, name), path.join(appDir, name), {
      recursive: true,
      force: true,
      errorOnExist: false,
    });
  }
  return manifest;
}

function replacePortableProgramFiles({ appDir, extractedAppDir, backupRoot, fsModule = fs }) {
  if (!path.isAbsolute(appDir) || !path.isAbsolute(extractedAppDir)) {
    throw new Error('便携更新替换路径必须是绝对路径');
  }
  const stagedEntries = listReplaceableProgramEntries(extractedAppDir, fsModule);
  if (stagedEntries.length === 0) {
    throw new Error('临时解压目录不含可替换程序文件');
  }
  createPortableUpdateRecoveryPoint({ appDir, backupRoot, fsModule });
  try {
    for (const name of listReplaceableProgramEntries(appDir, fsModule)) {
      fsModule.rmSync(path.join(appDir, name), { recursive: true, force: true });
    }
    for (const name of stagedEntries) {
      fsModule.cpSync(path.join(extractedAppDir, name), path.join(appDir, name), {
        recursive: true, force: true, errorOnExist: false,
      });
    }
    return { replacedEntries: stagedEntries };
  } catch (error) {
    restorePortableUpdateRecoveryPoint({ appDir, backupRoot, fsModule });
    throw error;
  }
}

module.exports = {
  PRESERVED_PORTABLE_DIRECTORIES,
  createPortableUpdateRecoveryPoint,
  listReplaceableProgramEntries,
  replacePortableProgramFiles,
  restorePortableUpdateRecoveryPoint,
};
