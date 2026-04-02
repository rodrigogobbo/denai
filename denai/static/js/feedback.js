/* ═══════════════════════════════════════════════════════════
   DENAI — FEEDBACK: reportar bugs e sugerir melhorias
   ═══════════════════════════════════════════════════════════ */

let _feedbackType = 'bug';

// ─── Abrir/fechar modal ───
window.openFeedbackModal = function() {
  resetFeedbackForm();
  document.getElementById('feedbackModalOverlay').style.display = 'flex';
  setTimeout(() => document.getElementById('fbTitle')?.focus(), 100);
};

window.closeFeedbackModal = function(e) {
  if (e && e.target !== document.getElementById('feedbackModalOverlay')) return;
  document.getElementById('feedbackModalOverlay').style.display = 'none';
};

// ─── Tipo de feedback ───
window.setFeedbackType = function(type) {
  _feedbackType = type;
  document.getElementById('tabBug').classList.toggle('active', type === 'bug');
  document.getElementById('tabImprovement').classList.toggle('active', type === 'improvement');

  const placeholder = type === 'bug'
    ? 'Descreva o bug: passos para reproduzir, comportamento esperado vs observado...'
    : 'Descreva a melhoria: contexto, motivação, como você esperaria que funcionasse...';
  document.getElementById('fbDescription').placeholder = placeholder;

  // Contexto só faz sentido para bugs
  document.getElementById('fbContextLabel').style.opacity = type === 'bug' ? '1' : '0.5';
  if (type === 'improvement') {
    document.getElementById('fbIncludeContext').checked = false;
  } else {
    document.getElementById('fbIncludeContext').checked = true;
  }
};

// ─── Enviar feedback ───
window.submitFeedback = async function() {
  const title = document.getElementById('fbTitle').value.trim();
  const description = document.getElementById('fbDescription').value.trim();
  const includeContext = document.getElementById('fbIncludeContext').checked;
  const statusEl = document.getElementById('feedbackStatus');
  const btn = document.getElementById('btnSubmitFeedback');

  // Validação
  if (title.length < 3) {
    statusEl.textContent = '⚠️ Título muito curto (mínimo 3 caracteres).';
    statusEl.className = 'feedback-status error';
    document.getElementById('fbTitle').focus();
    return;
  }
  if (description.length < 10) {
    statusEl.textContent = '⚠️ Descrição muito curta (mínimo 10 caracteres).';
    statusEl.className = 'feedback-status error';
    document.getElementById('fbDescription').focus();
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Enviando…';
  statusEl.textContent = '';
  statusEl.className = 'feedback-status';

  try {
    const data = await apiPost('/api/feedback', {
      type: _feedbackType,
      title,
      description,
      include_context: includeContext,
    });

    // Sucesso
    document.getElementById('feedbackForm').style.display = 'none';
    document.getElementById('feedbackSuccess').style.display = 'block';

    const msgEl = document.getElementById('feedbackSuccessMsg');
    const linkEl = document.getElementById('feedbackIssueLink');

    msgEl.textContent = data.message || 'Feedback enviado!';

    if (data.issue_url) {
      linkEl.href = data.issue_url;
      linkEl.style.display = 'block';
      linkEl.textContent = `Ver issue #${data.issue_number} no GitHub →`;
    } else if (data.method === 'local') {
      linkEl.style.display = 'none';
    }

  } catch (e) {
    statusEl.textContent = `❌ Erro ao enviar: ${e.message}`;
    statusEl.className = 'feedback-status error';
    btn.disabled = false;
    btn.textContent = 'Enviar →';
  }
};

// ─── Reset ───
window.resetFeedbackForm = function() {
  _feedbackType = 'bug';
  document.getElementById('feedbackForm').style.display = 'block';
  document.getElementById('feedbackSuccess').style.display = 'none';
  document.getElementById('fbTitle').value = '';
  document.getElementById('fbDescription').value = '';
  document.getElementById('fbIncludeContext').checked = true;
  document.getElementById('feedbackStatus').textContent = '';
  document.getElementById('feedbackStatus').className = 'feedback-status';
  const btn = document.getElementById('btnSubmitFeedback');
  if (btn) { btn.disabled = false; btn.textContent = 'Enviar →'; }
  setFeedbackType('bug');
};

// ─── Atalho de teclado ───
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.shiftKey && e.key === 'F') {
    e.preventDefault();
    openFeedbackModal();
  }
});
