const { build: baseBuild } = require('./package.json');

const { target: _installerTarget, ...baseWindowsConfig } = baseBuild.win;

module.exports = {
  ...baseBuild,
  productName: '股票基金质量分析系统',
  win: {
    ...baseWindowsConfig,
    publish: [
      {
        provider: 'github',
        owner: 'hanchanqaq-source',
        repo: 'ai-stock-daily-report',
      },
    ],
  },
};
