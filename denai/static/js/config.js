/* ═══════════════════════════════════════════════════════════
   DENAI — CONFIG: marked.js, TOOL_META, state, DOM refs
   ═══════════════════════════════════════════════════════════ */

// ─── Configure marked.js ───
marked.setOptions({
  breaks: true,
  gfm: true,
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try { return hljs.highlight(code, { language: lang }).value; }
      catch (e) { /* fall through */ }
    }
    try { return hljs.highlightAuto(code).value; }
    catch (e) { /* fall through */ }
    return code;
  }
});

// Custom renderer for code blocks
const renderer = new marked.Renderer();
const originalCodeRenderer = renderer.code;

renderer.code = function(code, language, escaped) {
  // marked v5+ passes an object
  let codeText = code;
  let lang = language || '';
  if (typeof code === 'object') {
    lang = code.lang || '';
    codeText = code.text || '';
  }
  const langLabel = lang || 'text';
  const highlighted = lang && hljs.getLanguage(lang)
    ? hljs.highlight(codeText, { language: lang }).value
    : hljs.highlightAuto(codeText).value;

  return `<div class="code-block-wrapper">
    <div class="code-block-header">
      <span class="lang-label">${escapeHtml(langLabel)}</span>
      <button class="btn-copy-code" onclick="copyCode(this)" data-code="${escapeAttr(codeText)}">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        Copiar
      </button>
    </div>
    <pre><code class="hljs language-${escapeAttr(langLabel)}">${highlighted}</code></pre>
  </div>`;
};

marked.setOptions({ renderer });


// ─── State ───
window.currentConversationId = null;
window.currentModel = '';
window.conversations = [];
window.isStreaming = false;
window.abortController = null;
window.sidebarOpen = window.innerWidth > 768;
window.lastUserMessage = '';  // For retry
window.currentTheme = localStorage.getItem('denai-theme') || 'dark';


// ─── DOM refs ───
window.$ = window.$ || {};
const $ = {
  sidebar: document.getElementById('sidebar'),
  sidebarOverlay: document.getElementById('sidebarOverlay'),
  conversationList: document.getElementById('conversationList'),
  messagesContainer: document.getElementById('messagesContainer'),
  messagesInner: document.getElementById('messagesInner'),
  messageInput: document.getElementById('messageInput'),
  btnSend: document.getElementById('btnSend'),
  btnNewChat: document.getElementById('btnNewChat'),
  btnToggleSidebar: document.getElementById('btnToggleSidebar'),
  modelSelect: document.getElementById('modelSelect'),
  headerTitle: document.getElementById('headerTitle'),
  inputModelLabel: document.getElementById('inputModelLabel'),
  confirmOverlay: document.getElementById('confirmOverlay'),
  confirmTitle: document.getElementById('confirmTitle'),
  confirmMessage: document.getElementById('confirmMessage'),
  btnConfirmCancel: document.getElementById('btnConfirmCancel'),
  btnConfirmOk: document.getElementById('btnConfirmOk'),
  toastContainer: document.getElementById('toastContainer'),
  pullModelInput: document.getElementById('pullModelInput'),
  btnPull: document.getElementById('btnPull'),
  pullStatus: document.getElementById('pullStatus'),
  searchInput: document.getElementById('searchInput'),
  ollamaBadge: document.getElementById('ollamaBadge'),
  ollamaLabel: document.getElementById('ollamaLabel'),
  btnExport: document.getElementById('btnExport'),
  exportDropdown: document.getElementById('exportDropdown'),
  btnTheme: document.getElementById('btnTheme'),
  themeIconMoon: document.getElementById('themeIconMoon'),
  themeIconSun: document.getElementById('themeIconSun'),
  wizardOverlay: document.getElementById('wizardOverlay'),
};
window.DOM = $;


// ─── Wizard State ───
window.wizardCurrentStep = 1;
window.wizardPulling = false;


// ─── Tool Metadata ───
window.TOOL_META = {
  file_read:     { icon: '📄', color: '#60a5fa' },
  file_write:    { icon: '✏️', color: '#34d399' },
  file_edit:     { icon: '🔧', color: '#fbbf24' },
  list_files:    { icon: '📁', color: '#a78bfa' },
  command_exec:  { icon: '⚡', color: '#f97316' },
  grep:          { icon: '🔍', color: '#2dd4bf' },
  think:         { icon: '🧠', color: '#c084fc' },
  memory_save:   { icon: '💾', color: '#fb7185' },
  memory_search: { icon: '🔎', color: '#fb7185' },
  web_search:    { icon: '🌐', color: '#38bdf8' },
  rag_search:    { icon: '📚', color: '#818cf8' },
  rag_index:     { icon: '📑', color: '#818cf8' },
  rag_stats:     { icon: '📊', color: '#818cf8' },
  question:      { icon: '❓', color: '#fbbf24' },
  plan_create:   { icon: '📋', color: '#4ade80' },
  plan_update:   { icon: '📝', color: '#4ade80' },
  _default:      { icon: '🔹', color: '#94a3b8' },
};
