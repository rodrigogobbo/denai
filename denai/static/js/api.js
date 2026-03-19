/* ═══════════════════════════════════════════════════════════
   DENAI — API: authentication & HTTP helpers
   ═══════════════════════════════════════════════════════════ */

const API_BASE = '';

// API key injetada pelo servidor via window.__DENAI_API_KEY__
function getApiKey() {
  return window.__DENAI_API_KEY__ || '';
}
window.getApiKey = getApiKey;

function authHeaders(extra = {}) {
  const h = { ...extra };
  const key = getApiKey();
  if (key) h['X-API-Key'] = key;
  return h;
}
window.authHeaders = authHeaders;
window.API_BASE = API_BASE;

async function apiGet(path) {
  const res = await fetch(API_BASE + path, { headers: authHeaders() });
  if (res.status === 401) { showAuthError(); throw new Error('Não autorizado'); }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
window.apiGet = apiGet;

async function apiPost(path, body) {
  const res = await fetch(API_BASE + path, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
  if (res.status === 401) { showAuthError(); throw new Error('Não autorizado'); }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
window.apiPost = apiPost;

async function apiDelete(path) {
  const res = await fetch(API_BASE + path, { method: 'DELETE', headers: authHeaders() });
  if (res.status === 401) { showAuthError(); throw new Error('Não autorizado'); }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
window.apiDelete = apiDelete;

function showAuthError() {
  const msg = document.createElement('div');
  msg.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#dc2626;color:#fff;padding:12px 24px;border-radius:8px;z-index:9999;font-size:14px;';
  msg.textContent = '🔒 API key inválida. Reinicie o servidor ou verifique ~/.denai/api.key';
  document.body.appendChild(msg);
  setTimeout(() => msg.remove(), 8000);
}
window.showAuthError = showAuthError;
