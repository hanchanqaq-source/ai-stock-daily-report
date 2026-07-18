const crypto = require('crypto');
const fs = require('fs');

const PORTABLE_ROOT = '股票基金质量分析系统/';
const REQUIRED_PORTABLE_ENTRIES = [
  `${PORTABLE_ROOT}股票基金质量分析系统.exe`,
  `${PORTABLE_ROOT}resources/backend/stock_analysis/stock_analysis.exe`,
];
const REQUIRED_PORTABLE_DIRECTORIES = ['data', 'logs', 'config', 'plugins'].map(
  (name) => `${PORTABLE_ROOT}${name}/`
);

function readSha256File(filePath) {
  const match = fs.readFileSync(filePath, 'utf8').match(/\b([a-fA-F0-9]{64})\b/);
  if (!match) throw new Error('SHA-256 文件格式无效');
  return match[1].toLowerCase();
}

function hashFile(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function readZipEntryNames(zipPath) {
  const archive = fs.readFileSync(zipPath);
  const minimumEocdSize = 22;
  const earliestEocdOffset = Math.max(0, archive.length - minimumEocdSize - 0xffff);
  let eocdOffset = -1;

  for (let offset = archive.length - minimumEocdSize; offset >= earliestEocdOffset; offset -= 1) {
    if (archive.readUInt32LE(offset) === 0x06054b50) {
      eocdOffset = offset;
      break;
    }
  }

  if (eocdOffset < 0) {
    throw new Error('ZIP 文件结构无效');
  }

  const entryCount = archive.readUInt16LE(eocdOffset + 10);
  let offset = archive.readUInt32LE(eocdOffset + 16);
  const entries = [];

  for (let index = 0; index < entryCount; index += 1) {
    if (offset + 46 > archive.length || archive.readUInt32LE(offset) !== 0x02014b50) {
      throw new Error('ZIP 目录结构无效');
    }
    const nameLength = archive.readUInt16LE(offset + 28);
    const extraLength = archive.readUInt16LE(offset + 30);
    const commentLength = archive.readUInt16LE(offset + 32);
    const nameEnd = offset + 46 + nameLength;
    if (nameEnd > archive.length) {
      throw new Error('ZIP 条目名称无效');
    }
    entries.push(archive.subarray(offset + 46, nameEnd).toString('utf8').replaceAll('\\', '/'));
    offset = nameEnd + extraLength + commentLength;
  }

  return entries;
}

function inspectPortableArchive(zipPath) {
  const entries = readZipEntryNames(zipPath);
  const missingEntries = REQUIRED_PORTABLE_ENTRIES.filter((entry) => !entries.includes(entry));
  const missingDirectories = REQUIRED_PORTABLE_DIRECTORIES.filter(
    (directory) => !entries.some((entry) => entry.startsWith(directory))
  );
  const missing = [...missingEntries, ...missingDirectories];
  return { valid: missing.length === 0, missing };
}

function verifyPortableArchive(zipPath, sha256Path) {
  if (!zipPath.toLowerCase().endsWith('.zip')) throw new Error('请选择 Portable ZIP 文件');
  const expected = readSha256File(sha256Path);
  const actual = hashFile(zipPath);
  const checksumValid = actual === expected;
  const structure = inspectPortableArchive(zipPath);
  return {
    valid: checksumValid && structure.valid,
    expected,
    actual,
    checksumValid,
    structureValid: structure.valid,
    missingEntries: structure.missing,
  };
}

module.exports = { inspectPortableArchive, readZipEntryNames, verifyPortableArchive };
