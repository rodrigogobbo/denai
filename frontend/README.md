# DenAI Frontend

CSS compilado via [Tailwind CSS](https://tailwindcss.com/) + CLI.

## Setup

```bash
cd frontend
npm install
```

## Comandos

```bash
npm run build   # compila e minifica → denai/static/css/tailwind.css
npm run dev     # watch mode — recompila ao salvar
```

O arquivo `denai/static/css/tailwind.css` é **commitado no repo** — `pip install denai` funciona sem Node.js.

## Estrutura

```
frontend/
├── tailwind.config.js    ← design tokens (cores, radius, fonts)
├── src/
│   ├── input.css         ← entry point (@tailwind + imports)
│   └── custom/
│       ├── variables.css ← CSS vars dark/light + reset
│       ├── animations.css← @keyframes
│       ├── layout.css    ← sidebar, header, main, input area
│       ├── chat.css      ← mensagens, tool cards, markdown
│       └── components.css← modais, toasts, badges, wizard
```

## Modificar estilos

1. Editar arquivos em `src/custom/`
2. Rodar `npm run build` (ou `npm run dev` para watch)
3. Commitar `denai/static/css/tailwind.css`
