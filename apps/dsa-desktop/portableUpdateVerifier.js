const crypto = require('crypto');
const fs = require('fs');

function readSha256File(filePath) {
  const match = fs.readFileSync(filePath, 'utf8').match(/\b([a-fA-F0-9]{64})\b/);
  if (!match) throw new Error('SHA-256 文件格式无效');
  return match[1].toLowerCase();
}

function hashFile(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function verifyPortableArchive(zipPath, sha256Path) {
  if (!zipPath.toLowerCase().endsWith('.zip')) throw new Error('请选择 Portable ZIP 文件');
  const expected = readSha256File(sha256Path);
  const actual = hashFile(zipPath);
  return { valid: actual === expected, expected, actual };
}

module.exports = { verifyPortableArchive };
