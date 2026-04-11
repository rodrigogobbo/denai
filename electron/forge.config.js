const path = require('path');

module.exports = {
  packagerConfig: {
    name: 'DenAI',
    executableName: 'denai',
    icon: path.join(__dirname, 'assets', 'icon'),
    appBundleId: 'dev.gobbo.denai',
    appCategoryType: 'public.app-category.productivity',
    extraResource: [path.join(__dirname, 'bin')],
    ignore: [
      /^\/\.git/,
      /^\/scripts/,
      /node_modules\/\.cache/,
    ],
  },

  rebuildConfig: {},

  makers: [
    // Windows — Squirrel
    {
      name: '@electron-forge/maker-squirrel',
      config: {
        name: 'DenAI',
        setupIcon: path.join(__dirname, 'assets', 'icon.ico'),
      },
      platforms: ['win32'],
    },

    // macOS — DMG
    {
      name: '@electron-forge/maker-dmg',
      config: {
        name: 'DenAI',
        icon: path.join(__dirname, 'assets', 'icon.icns'),
        format: 'ULFO',
      },
      platforms: ['darwin'],
    },

    // Linux — ZIP (AppImage requer buildtools externos)
    {
      name: '@electron-forge/maker-zip',
      platforms: ['linux'],
    },
  ],

  plugins: [],
};
