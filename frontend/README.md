# DenAI Frontend

CSS compilado via [Tailwind CSS](https://tailwindcss.com/) + CLI.

O único arquivo CSS servido pelo app é `denai/static/css/tailwind.css` — gerado a partir dos fontes em `frontend/src/`.

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

`denai/static/css/tailwind.css` é **commitado no repo** — `pip install denai` funciona sem Node.js. O `package-lock.json` **não** é commitado.

## Estrutura

```
frontend/
├── tailwind.config.js    ← design tokens (cores, radius, fonts)
├── src/
│   ├── input.css         ← entry point (@tailwind + imports)
│   └── custom/           ← fontes CSS — editados aqui
│       ├── variables.css ← CSS vars dark/light + reset
│       ├── animations.css← @keyframes
│       ├── layout.css    ← sidebar, header, main, input area
│       ├── chat.css      ← mensagens, tool cards, markdown
│       └── components.css← modais, toasts, badges, wizard
└── .gitignore            ← node_modules/ e package-lock.json ignorados
```

## Modificar estilos

1. Editar arquivos em `src/custom/`
2. Rodar `npm run build` (ou `npm run dev` para watch)
3. Commitar `denai/static/css/tailwind.css`

## Nota histórica

Antes da v0.23.0, o app servia 5 arquivos CSS individuais (`base.css`, `animations.css`, `layout.css`, `chat.css`, `components.css`). A partir da v0.23.0, esses arquivos foram consolidados no pipeline Tailwind. Os arquivos legacy foram removidos na v0.24.0.
