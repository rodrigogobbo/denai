/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../denai/static/**/*.{html,js}',
  ],
  theme: {
    extend: {
      colors: {
        accent:          'var(--accent)',
        'bg-primary':    'var(--bg-primary)',
        'bg-secondary':  'var(--bg-secondary)',
        'bg-card':       'var(--bg-card)',
        'bg-card-hover': 'var(--bg-card-hover)',
        'bg-tool':       'var(--bg-tool)',
        'text-primary':  'var(--text-primary)',
        'text-muted':    'var(--text-muted)',
        'border-color':  'var(--border)',
        danger:          'var(--danger)',
        success:         '#48bb78',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
    },
  },
  plugins: [],
}
