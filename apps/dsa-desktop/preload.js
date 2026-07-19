const { contextBridge, ipcRenderer } = require('electron');

const DESKTOP_VERSION_ARG_PREFIX = '--dsa-desktop-version=';
const DESKTOP_PORTABLE_ARG_PREFIX = '--dsa-desktop-portable=';
const DESKTOP_GET_UPDATE_STATE_CHANNEL = 'desktop:get-update-state';
const DESKTOP_CHECK_FOR_UPDATES_CHANNEL = 'desktop:check-for-updates';
const DESKTOP_INSTALL_DOWNLOADED_UPDATE_CHANNEL = 'desktop:install-downloaded-update';
const DESKTOP_OPEN_RELEASE_PAGE_CHANNEL = 'desktop:open-release-page';
const DESKTOP_VERIFY_PORTABLE_UPDATE_CHANNEL = 'desktop:verify-portable-update';
const DESKTOP_APPLY_PORTABLE_UPDATE_CHANNEL = 'desktop:apply-portable-update';
const DESKTOP_DOWNLOAD_PORTABLE_UPDATE_CHANNEL = 'desktop:download-portable-update';
const DESKTOP_APPLY_DOWNLOADED_PORTABLE_UPDATE_CHANNEL = 'desktop:apply-downloaded-portable-update';
const DESKTOP_UPDATE_STATE_EVENT = 'desktop:update-state';
const DESKTOP_CREDENTIAL_STATUS_CHANNEL = 'desktop:credential-status';
const DESKTOP_SET_CREDENTIAL_CHANNEL = 'desktop:set-credential';
const DESKTOP_CLEAR_CREDENTIAL_CHANNEL = 'desktop:clear-credential';

function readDesktopVersion(argv = process.argv) {
  const versionArg = argv.find(
    (value) => typeof value === 'string' && value.startsWith(DESKTOP_VERSION_ARG_PREFIX)
  );
  return versionArg ? versionArg.slice(DESKTOP_VERSION_ARG_PREFIX.length) : '';
}

function readPortableBuildFlag(argv = process.argv) {
  return argv.some((value) => value === `${DESKTOP_PORTABLE_ARG_PREFIX}true`);
}

function createDesktopBridge({
  version = readDesktopVersion(),
  renderer = ipcRenderer,
} = {}) {
  return {
    version,
    isPortableBuild: readPortableBuildFlag(),
    getUpdateState() {
      return renderer.invoke(DESKTOP_GET_UPDATE_STATE_CHANNEL);
    },
    checkForUpdates() {
      return renderer.invoke(DESKTOP_CHECK_FOR_UPDATES_CHANNEL);
    },
    installDownloadedUpdate() {
      return renderer.invoke(DESKTOP_INSTALL_DOWNLOADED_UPDATE_CHANNEL);
    },
    openReleasePage(releaseUrl) {
      return renderer.invoke(DESKTOP_OPEN_RELEASE_PAGE_CHANNEL, releaseUrl);
    },
    verifyPortableUpdate() {
      return renderer.invoke(DESKTOP_VERIFY_PORTABLE_UPDATE_CHANNEL);
    },
    applyPortableUpdate() {
      return renderer.invoke(DESKTOP_APPLY_PORTABLE_UPDATE_CHANNEL);
    },
    downloadPortableUpdate() { return renderer.invoke(DESKTOP_DOWNLOAD_PORTABLE_UPDATE_CHANNEL); },
    applyDownloadedPortableUpdate() { return renderer.invoke(DESKTOP_APPLY_DOWNLOADED_PORTABLE_UPDATE_CHANNEL); },
    getCredentialStatus(key) {
      return renderer.invoke(DESKTOP_CREDENTIAL_STATUS_CHANNEL, { key });
    },
    setCredential(key, value) {
      return renderer.invoke(DESKTOP_SET_CREDENTIAL_CHANNEL, { key, value });
    },
    clearCredential(key) {
      return renderer.invoke(DESKTOP_CLEAR_CREDENTIAL_CHANNEL, { key });
    },
    onUpdateStateChange(listener) {
      if (typeof listener !== 'function') {
        return () => undefined;
      }

      const handler = (_event, payload) => {
        listener(payload);
      };
      renderer.on(DESKTOP_UPDATE_STATE_EVENT, handler);
      return () => {
        renderer.removeListener(DESKTOP_UPDATE_STATE_EVENT, handler);
      };
    },
  };
}

contextBridge.exposeInMainWorld('dsaDesktop', createDesktopBridge());

module.exports = {
  DESKTOP_CLEAR_CREDENTIAL_CHANNEL,
  DESKTOP_CHECK_FOR_UPDATES_CHANNEL,
  DESKTOP_CREDENTIAL_STATUS_CHANNEL,
  DESKTOP_GET_UPDATE_STATE_CHANNEL,
  DESKTOP_SET_CREDENTIAL_CHANNEL,
  DESKTOP_INSTALL_DOWNLOADED_UPDATE_CHANNEL,
  DESKTOP_OPEN_RELEASE_PAGE_CHANNEL,
  DESKTOP_PORTABLE_ARG_PREFIX,
  DESKTOP_VERIFY_PORTABLE_UPDATE_CHANNEL,
  DESKTOP_UPDATE_STATE_EVENT,
  DESKTOP_VERSION_ARG_PREFIX,
  DESKTOP_APPLY_PORTABLE_UPDATE_CHANNEL,
  DESKTOP_DOWNLOAD_PORTABLE_UPDATE_CHANNEL,
  DESKTOP_APPLY_DOWNLOADED_PORTABLE_UPDATE_CHANNEL,
  createDesktopBridge,
  readPortableBuildFlag,
  readDesktopVersion,
};
