const { build: baseBuild } = require('./package.json');

module.exports = {
  ...baseBuild,
  productName: '股票基金质量分析系统',
  win: {
    ...baseBuild.win,
    target: [
      {
        target: 'dir',
        arch: ['x64'],
      },
    ],
    publish: [
      {
        provider: 'github',
        owner: 'hanchanqaq-source',
        repo: 'ai-stock-daily-report',
      },
    ],
  },
};
