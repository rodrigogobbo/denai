#!/usr/bin/env node
/**
 * sync-version.js
 * Lê VERSION de denai/version.py e atualiza electron/package.json.
 * Executado antes de cada build.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
const VERSION_PY = path.join(ROOT, 'denai', 'version.py');
const PKG_JSON = path.join(__dirname, '..', 'package.json');

// Ler versão do Python
const versionPy = fs.readFileSync(VERSION_PY, 'utf-8');
const match = versionPy.match(/VERSION\s*=\s*["']([^"']+)["']/);
if (!match) {
  console.error('Erro: VERSION não encontrada em', VERSION_PY);
  process.exit(1);
}
const version = match[1];

// Atualizar package.json
const pkg = JSON.parse(fs.readFileSync(PKG_JSON, 'utf-8'));
const prev = pkg.version;
pkg.version = version;
fs.writeFileSync(PKG_JSON, JSON.stringify(pkg, null, 2) + '\n');

if (prev !== version) {
  console.log(`sync-version: ${prev} → ${version}`);
} else {
  console.log(`sync-version: já na versão ${version}`);
}
