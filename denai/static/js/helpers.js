/* ═══════════════════════════════════════════════════════════
   DENAI — HELPERS: utility functions
   ═══════════════════════════════════════════════════════════ */

function getToolMeta(name) {
  return window.TOOL_META[name] || window.TOOL_META._default;
}
window.getToolMeta = getToolMeta;

function tryParseJSON(str) {
  try { return JSON.parse(str); } catch { return null; }
}
window.tryParseJSON = tryParseJSON;

function formatBytes(len) {
  if (len < 1024) return len + ' chars';
  return (len / 1024).toFixed(1) + 'k chars';
}
window.formatBytes = formatBytes;

// ─── Helpers ───
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
window.escapeHtml = escapeHtml;

function escapeAttr(str) {
  return str.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
window.escapeAttr = escapeAttr;

function relativeTime(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'agora';
  if (diffMin < 60) return `${diffMin}min atrás`;
  if (diffHr < 24) return `${diffHr}h atrás`;
  if (diffDay < 7) return `${diffDay}d atrás`;
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
}
window.relativeTime = relativeTime;

function scrollToBottom(force = false) {
  const el = DOM.messagesContainer;
  const isNearBottom = (el.scrollHeight - el.scrollTop - el.clientHeight) < 200;
  if (force || isNearBottom) {
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }
}
window.scrollToBottom = scrollToBottom;

function generateId() {
  return 'id_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2,8);
}
window.generateId = generateId;


// ─── Toast ───
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  DOM.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = '0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
window.showToast = showToast;


// ─── Confirm Dialog ───
window.confirmResolve = null;

function showConfirm(title, message) {
  return new Promise(resolve => {
    window.confirmResolve = resolve;
    DOM.confirmTitle.textContent = title;
    DOM.confirmMessage.textContent = message;
    DOM.confirmOverlay.classList.add('visible');
  });
}
window.showConfirm = showConfirm;

DOM.btnConfirmCancel.addEventListener('click', () => {
  DOM.confirmOverlay.classList.remove('visible');
  if (window.confirmResolve) { window.confirmResolve(false); window.confirmResolve = null; }
});

DOM.btnConfirmOk.addEventListener('click', () => {
  DOM.confirmOverlay.classList.remove('visible');
  if (window.confirmResolve) { window.confirmResolve(true); window.confirmResolve = null; }
});

DOM.confirmOverlay.addEventListener('click', (e) => {
  if (e.target === DOM.confirmOverlay) {
    DOM.confirmOverlay.classList.remove('visible');
    if (window.confirmResolve) { window.confirmResolve(false); window.confirmResolve = null; }
  }
});


// ─── Copy code ───
window.copyCode = function(btn) {
  const code = btn.getAttribute('data-code');
  navigator.clipboard.writeText(code).then(() => {
    btn.classList.add('copied');
    const origText = btn.innerHTML;
    btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Copiado!`;
    setTimeout(() => {
      btn.classList.remove('copied');
      btn.innerHTML = origText;
    }, 2000);
  }).catch(() => {
    showToast('Falha ao copiar', 'error');
  });
};


// ─── Tool call toggle ───
window.toggleToolCall = function(el) {
  el.closest('.tool-call-card').classList.toggle('expanded');
};

// ─── Copy tool result ───
window.copyToolResult = function(btn) {
  const card = btn.closest('.tool-call-body');
  const fullPre = card.querySelector('.tool-result-full');
  const shortPre = card.querySelector('.tool-result-pre');
  const text = (fullPre ? fullPre.textContent : shortPre?.textContent) || '';
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '✓';
    setTimeout(() => { btn.textContent = '📋'; }, 1500);
  });
};

// ─── Toggle truncated tool result ───
window.toggleToolResult = function(btn) {
  const card = btn.closest('.tool-call-body');
  const shortPre = card.querySelector('.tool-result-pre');
  const fullPre = card.querySelector('.tool-result-full');
  if (!shortPre || !fullPre) return;
  const isExpanded = btn.dataset.expanded === '1';
  if (isExpanded) {
    shortPre.textContent = fullPre.textContent.slice(0, 2000);
    btn.textContent = 'mostrar mais (' + formatBytes(fullPre.textContent.length) + ')';
    btn.dataset.expanded = '0';
  } else {
    shortPre.textContent = fullPre.textContent;
    btn.textContent = 'mostrar menos';
    btn.dataset.expanded = '1';
  }
};


// ─── Answer question card ───
window.answerQuestion = async function(qId, btnEl, optionText) {
  const card = document.getElementById('qcard-' + qId);
  if (!card || card.classList.contains('answered')) return;

  let answer = optionText;
  if (!answer) {
    // Free-form: grab sibling input
    const input = card.querySelector('.q-free input');
    answer = input ? input.value.trim() : '';
    if (!answer) return;
  }

  // Disable immediately
  card.classList.add('answered');
  card.insertAdjacentHTML('beforeend', `<div class="q-answer">✓ ${escapeHtml(answer)}</div>`);

  try {
    await apiPost(`/api/questions/${qId}/answer`, { answer });
  } catch (e) {
    card.classList.remove('answered');
    card.querySelector('.q-answer')?.remove();
    showToast('Erro ao enviar resposta', 'error');
  }
};
