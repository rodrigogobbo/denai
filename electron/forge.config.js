const path = require('path');

module.exports = {
  packagerConfig: {
    name: 'DenAI',
    executableName: 'denai',
    icon: path.join(__dirname, 'assets', 'icon'),
    appBundleId: 'dev.gobbo.denai',
    appCategoryType: 'public.app-category.productivity',
    // Empacotar binários uv para todos os targets
    extraResource: [path.join(__dirname, 'bin')],
    // Ignorar node_modules de dev e arquivos desnecessários
    ignore: [
      /^\/\.git/,
      /^\/scripts/,
      /node_modules\/\.cache/,
    ],
  },

  rebuildConfig: {},

  makers: [
    // Windows — NSIS installer
    {
      name: '@electron-forge/maker-squirrel',
      config: {
        name: 'DenAI',
        setupIcon: path.join(__dirname, 'assets', 'icon.ico'),
        loadingGif: path.join(__dirname, 'assets', 'install.gif'),
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

    // Linux — AppImage
    {
      name: '@electron-forge/maker-appimage',
      config: {
        name: 'DenAI',
        genericName: 'AI Assistant',
        icon: path.join(__dirname, 'assets', 'icon.png'),
        categories: ['Utility', 'Science'],
      },
      platforms: ['linux'],
    },
  ],

  plugins: [],
};
