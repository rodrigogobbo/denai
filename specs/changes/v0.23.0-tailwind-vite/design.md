# Design Document

## Overview
### Change Type: refactor (CSS) + new tooling

### Design Goals
1. Tailwind como camada de CSS — JS permanece vanilla
2. CSS commitado no repo (zero deps Node em produção)
3. Migração incremental — não quebrar nada existente
4. Build < 1s em desenvolvimento

### References
- REQ-1: Estrutura de build
- REQ-2: Tailwind config
- REQ-3: Migração CSS
- REQ-4: Developer experience

---

## DES-1: Estrutura de arquivos

```
frontend/                    ← NOVO
  package.json
  vite.config.js
  tailwind.config.js
  src/
    input.css               ← entrada do Tailwind
    custom/
      variables.css         ← :root vars (movidas do base.css)
      animations.css        ← cópia das animações existentes
      components.css        ← classes customizadas via @apply
      chat.css              ← classes de chat via @apply
      layout.css            ← layout via @apply

denai/static/css/
  tailwind.css              ← OUTPUT commitado (substituí todos os .css)
  [remover: base.css, layout.css, chat.css, components.css, animations.css]
```

### DES-2: frontend/package.json

```json
{
  "name": "denai-frontend",
  "private": true,
  "scripts": {
    "build": "vite build",
    "dev": "vite build --watch"
  },
  "devDependencies": {
    "vite": "6.2.4",
    "tailwindcss": "3.4.17",
    "@tailwindcss/vite": "4.0.15"
  }
}
```

Usar Tailwind v3 (estável, ampla adoção) + Vite para build.

### DES-3: tailwind.config.js

```js
module.exports = {
  content: ['../denai/static/**/*.{html,js}'],
  theme: {
    extend: {
      colors: {
        accent:       'var(--accent)',
        'bg-primary':  'var(--bg-primary)',
        'bg-secondary':'var(--bg-secondary)',
        'bg-card':     'var(--bg-card)',
        'bg-card-hover':'var(--bg-card-hover)',
        'text-primary':'var(--text-primary)',
        'text-muted':  'var(--text-muted)',
        border:        'var(--border)',
        danger:        'var(--danger)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
      },
    },
  },
  plugins: [],
}
```

### DES-4: src/input.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Preservar CSS variables existentes */
@import './custom/variables.css';

/* Animações (keyframes não migráveis) */
@import './custom/animations.css';

/* Componentes complexos via @apply */
@layer components {
  @import './custom/components.css';
  @import './custom/chat.css';
  @import './custom/layout.css';
}
```

### DES-5: Estratégia de migração

**Fase 1 (esta versão):** Setup + migração de `base.css` e duplicações óbvias.

Exemplo antes:
```css
.btn-primary {
  padding: 8px 16px;
  background: var(--accent);
  color: #0a0e1a;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
```

Exemplo depois (via @apply):
```css
@layer components {
  .btn-primary {
    @apply px-4 py-2 text-[#0a0e1a] border-0 rounded-sm text-[13px] font-semibold cursor-pointer;
    background: var(--accent);
  }
}
```

**Fase 2 (futuro):** Converter classes compostas para utility classes inline no HTML.

### DES-6: ui.html — atualizar link CSS

```html
<!-- Remover os 5 links CSS individuais -->
<!-- Adicionar apenas: -->
<link rel="stylesheet" href="/static/css/tailwind.css">
```

### DES-7: CI — não bloquear

O `tailwind.css` é commitado. CI não precisa rodar npm build — apenas verifica se o arquivo existe.
