# Requirements Document

## Introduction

O frontend do DenAI usa CSS vanilla (~2.486 linhas em 5 arquivos) e JS vanilla (~3.540 linhas em 12 arquivos), servidos como estáticos pelo FastAPI. Sem bundler, sem TypeScript, sem tree-shaking.

O principal problema: duplicação massiva de CSS. Classes utilitárias repetidas em múltiplos arquivos, valores hardcoded (`#0d1117`, `var(--accent)`, `#63b3ed`) misturados com classes compostas longas. Isso torna difícil manter consistência visual e iterar na UI.

**Tailwind CSS + Vite** resolve isso sem mudar a arquitetura: o FastAPI continua servindo os estáticos, o Vite apenas processa o CSS (e opcionalmente JS) durante o build.

Escopo deliberadamente conservador: **migrar CSS para Tailwind**. JS permanece vanilla por enquanto — a migração para TypeScript/React fica para uma fase futura.

## Glossary

| Term | Definition |
|------|------------|
| JIT | Just-in-time compilation — Tailwind gera apenas as classes usadas no HTML/JS |
| purge | Remoção de classes CSS não utilizadas no build de produção |
| design token | Variável CSS existente (ex: `--accent`, `--bg-secondary`) mapeada como cor Tailwind customizada |
| vite_build | Processo que compila `src/input.css` + escaneia HTML/JS → gera `dist/output.css` otimizado |

## Requirements

### REQ-1: Estrutura de build

1.1. THE system SHALL have a `frontend/` directory with: `package.json`, `vite.config.js`, `src/input.css`. _(Ubiquitous)_

1.2. THE build command `npm run build` in `frontend/` SHALL produce `denai/static/css/tailwind.css`. _(Ubiquitous)_

1.3. THE build SHALL run automatically in CI before tests (lint check only — não bloquear se Tailwind não estiver no path). _(Ubiquitous)_

1.4. `pip install denai` SHALL continue working without Node.js — o CSS compilado é commitado no repo. _(Ubiquitous)_

1.5. `python -m denai` em desenvolvimento SHALL NOT require running `npm run build` — usar o CSS commitado. _(Ubiquitous)_

### REQ-2: Tailwind config

2.1. THE Tailwind config SHALL map existing CSS variables as custom colors:
- `accent` → `var(--accent)` (#63b3ed)
- `bg-primary` → `var(--bg-primary)`
- `bg-secondary` → `var(--bg-secondary)`
- `bg-card` → `var(--bg-card)`
- `text-primary` → `var(--text-primary)`
- `text-muted` → `var(--text-muted)`
- `border` → `var(--border)`
- `danger` → `var(--danger)`
- `success` → `var(--success)` _(Event-driven)_

2.2. THE Tailwind content scan SHALL include `denai/static/**/*.{html,js}`. _(Ubiquitous)_

2.3. THE existing `@apply` pattern SHALL be used for complex components (não converter tudo para utility classes inline). _(Ubiquitous)_

### REQ-3: Migração CSS

3.1. `base.css` SHALL be replaced by Tailwind's `@tailwind base` + custom resets. _(Ubiquitous)_

3.2. `animations.css` SHALL be preserved as-is (keyframes não migráveis facilmente). _(Ubiquitous)_

3.3. `layout.css`, `chat.css`, `components.css` SHALL be converted to use Tailwind utilities via `@apply` where repetition exists. _(Ubiquitous)_

3.4. CSS custom properties (`:root` vars) SHALL be preserved — Tailwind usa-as como tokens. _(Ubiquitous)_

3.5. THE compiled `tailwind.css` SHALL be ≤ 50KB gzipped. _(Ubiquitous)_

### REQ-4: Developer experience

4.1. `npm run dev` in `frontend/` SHALL watch for changes and rebuild automatically. _(Ubiquitous)_

4.2. THE README SHALL document: como instalar deps do frontend, como buildar, como desenvolver. _(Ubiquitous)_
