const path = require('path');

function selectPortableReleaseAssets(release) {
  const assets = Array.isArray(release?.assets) ? release.assets : [];
  const zip = assets.find((asset) => typeof asset?.name === 'string' && /Portable.*\.zip$/i.test(asset.name));
  if (!zip || typeof zip.browser_download_url !== 'string') throw new Error('GitHub Release 未包含 Portable ZIP');
  const checksum = assets.find((asset) => asset?.name === `${zip.name}.sha256`);
  if (!checksum || typeof checksum.browser_download_url !== 'string') throw new Error('GitHub Release 未包含对应 SHA-256 文件');
  return { zipName: zip.name, zipUrl: zip.browser_download_url, sha256Name: checksum.name, sha256Url: checksum.browser_download_url };
}

function buildPortableDownloadPaths(tempDir, assets) {
  if (!path.isAbsolute(tempDir)) throw new Error('临时下载目录必须是绝对路径');
  return { zipPath: path.join(tempDir, assets.zipName), sha256Path: path.join(tempDir, assets.sha256Name) };
}

module.exports = { buildPortableDownloadPaths, selectPortableReleaseAssets };
