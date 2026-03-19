/* ═══════════════════════════════════════════════════════════
   DENAI — UI: theme, sidebar, input, shortcuts, wizard, plans, init
   ═══════════════════════════════════════════════════════════ */

// ─── Sidebar ───
function toggleSidebar() {
  window.sidebarOpen = !window.sidebarOpen;
  DOM.sidebar.classList.toggle('collapsed', !window.sidebarOpen);

  if (window.innerWidth <= 768) {
    DOM.sidebarOverlay.classList.toggle('visible', window.sidebarOpen);
  }
}
window.toggleSidebar = toggleSidebar;

DOM.btnToggleSidebar.addEventListener('click', toggleSidebar);
DOM.sidebarOverlay.addEventListener('click', () => {
  window.sidebarOpen = false;
  DOM.sidebar.classList.add('collapsed');
  DOM.sidebarOverlay.classList.remove('visible');
});

// Initial state
if (!window.sidebarOpen) DOM.sidebar.classList.add('collapsed');


// ─── Textarea auto-grow ───
DOM.messageInput.addEventListener('input', () => {
  DOM.messageInput.style.height = 'auto';
  DOM.messageInput.style.height = Math.min(DOM.messageInput.scrollHeight, 120) + 'px';
});


// ─── Theme toggle ───
function setTheme(theme) {
  window.currentTheme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('denai-theme', theme);

  if (theme === 'light') {
    DOM.themeIconMoon.style.display = 'none';
    DOM.themeIconSun.style.display = 'block';
  } else {
    DOM.themeIconMoon.style.display = 'block';
    DOM.themeIconSun.style.display = 'none';
  }
}
window.setTheme = setTheme;

DOM.btnTheme.addEventListener('click', () => {
  setTheme(window.currentTheme === 'dark' ? 'light' : 'dark');
});

// Apply saved theme on load
setTheme(window.currentTheme);


// ─── Input handlers ───
DOM.btnSend.addEventListener('click', sendMessage);

DOM.messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});


// ─── Keyboard shortcuts ───
document.addEventListener('keydown', (e) => {
  // Ctrl+N — new chat
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
    e.preventDefault();
    newChat();
  }

  // Ctrl+/ — toggle sidebar
  if ((e.ctrlKey || e.metaKey) && e.key === '/') {
    e.preventDefault();
    toggleSidebar();
  }

  // Ctrl+T — toggle theme
  if ((e.ctrlKey || e.metaKey) && e.key === 't') {
    e.preventDefault();
    setTheme(window.currentTheme === 'dark' ? 'light' : 'dark');
  }

  // Ctrl+F — focus search
  if ((e.ctrlKey || e.metaKey) && e.key === 'f' && !e.shiftKey) {
    // Only intercept if not already in an input
    if (document.activeElement !== DOM.searchInput && document.activeElement !== DOM.messageInput) {
      e.preventDefault();
      if (!window.sidebarOpen) toggleSidebar();
      DOM.searchInput.focus();
    }
  }

  // Escape — close dialogs
  if (e.key === 'Escape') {
    if (DOM.wizardOverlay.classList.contains('visible')) {
      // Allow escape to dismiss wizard
      wizardFinish();
      return;
    }
    if (DOM.confirmOverlay.classList.contains('visible')) {
      DOM.confirmOverlay.classList.remove('visible');
      if (window.confirmResolve) { window.confirmResolve(false); window.confirmResolve = null; }
    }
    if (window.sidebarOpen && window.innerWidth <= 768) {
      window.sidebarOpen = false;
      DOM.sidebar.classList.add('collapsed');
      DOM.sidebarOverlay.classList.remove('visible');
    }
  }
});


// ─── Window resize handler ───
window.addEventListener('resize', () => {
  if (window.innerWidth > 768) {
    DOM.sidebarOverlay.classList.remove('visible');
    if (!window.sidebarOpen) {
      window.sidebarOpen = true;
      DOM.sidebar.classList.remove('collapsed');
    }
  }
});


// ─── First-Boot Wizard ───
function showWizard() {
  window.wizardCurrentStep = 1;
  // Reset all steps
  document.querySelectorAll('.wizard-step').forEach(s => s.classList.remove('active'));
  document.getElementById('wizardStep1').classList.add('active');
  DOM.wizardOverlay.classList.add('visible');
}
window.showWizard = showWizard;

window.wizardNext = function(step) {
  window.wizardCurrentStep = step;
  document.querySelectorAll('.wizard-step').forEach(s => s.classList.remove('active'));
  document.getElementById('wizardStep' + step).classList.add('active');

  // Auto-check Ollama on step 2
  if (step === 2) {
    wizardCheckOllama();
  }
};

window.wizardCheckOllama = async function() {
  const onlineEl = document.getElementById('wizardOllamaOnline');
  const offlineEl = document.getElementById('wizardOllamaOffline');
  const checkingEl = document.getElementById('wizardOllamaChecking');
  const recheckBtn = document.getElementById('wizardRecheckBtn');

  onlineEl.style.display = 'none';
  offlineEl.style.display = 'none';
  checkingEl.style.display = 'block';
  if (recheckBtn) recheckBtn.disabled = true;

  try {
    const data = await apiGet('/api/ollama/status');
    checkingEl.style.display = 'none';

    if (data.status === 'online') {
      onlineEl.style.display = 'block';
      const versionEl = document.getElementById('wizardOllamaVersion');
      if (versionEl && data.version) versionEl.textContent = `v${data.version}`;

      // Auto-advance after 1.5s
      setTimeout(() => {
        if (window.wizardCurrentStep === 2) {
          // If there are already models, skip to step 4
          if (data.models_count > 0) {
            wizardNext(4);
          } else {
            wizardNext(3);
          }
        }
      }, 1500);
    } else {
      offlineEl.style.display = 'block';
      if (recheckBtn) recheckBtn.disabled = false;
    }
  } catch (e) {
    checkingEl.style.display = 'none';
    offlineEl.style.display = 'block';
    if (recheckBtn) recheckBtn.disabled = false;
  }
};

window.wizardPullModel = async function(modelName, cardEl) {
  if (window.wizardPulling) return;
  window.wizardPulling = true;

  // Mark card as pulling
  document.querySelectorAll('.wizard-model-card').forEach(c => c.style.pointerEvents = 'none');
  if (cardEl) cardEl.classList.add('pulling');

  const progressContainer = document.getElementById('wizardPullProgress');
  const progressLabel = document.getElementById('wizardPullLabel');
  const progressFill = document.getElementById('wizardProgressFill');
  progressContainer.classList.add('active');
  progressLabel.textContent = `Baixando ${modelName}...`;
  progressFill.style.width = '0%';

  try {
    const res = await fetch(API_BASE + '/api/pull', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ model: modelName }),
    });

    if (!res.ok) throw new Error(`Erro: ${res.status}`);

    if (res.body) {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let lastStatus = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n').filter(l => l.trim());
        for (const line of lines) {
          try {
            const parsed = JSON.parse(line);
            lastStatus = parsed.status || lastStatus;
            if (parsed.total && parsed.completed) {
              const pct = Math.round((parsed.completed / parsed.total) * 100);
              progressLabel.textContent = `${lastStatus} ${pct}%`;
              progressFill.style.width = pct + '%';
            } else {
              progressLabel.textContent = lastStatus;
            }
          } catch (e) {
            progressLabel.textContent = line;
          }
        }
      }
    }

    progressLabel.textContent = `✓ ${modelName} pronto!`;
    progressFill.style.width = '100%';

    // Advance to ready step after a moment
    setTimeout(() => {
      wizardNext(4);
      window.wizardPulling = false;
    }, 1200);

  } catch (e) {
    progressLabel.textContent = `✗ Erro: ${e.message}`;
    progressFill.style.width = '0%';
    window.wizardPulling = false;
    document.querySelectorAll('.wizard-model-card').forEach(c => c.style.pointerEvents = '');
    if (cardEl) cardEl.classList.remove('pulling');
  }
};

window.wizardFinish = async function() {
  localStorage.setItem('denai-wizard-done', '1');
  DOM.wizardOverlay.classList.remove('visible');

  // Refresh models and ollama status
  await Promise.all([loadModels(), checkOllamaStatus()]);
  DOM.messageInput.focus();
};


// ─── Plans Panel ───
const $plansPanel = document.getElementById('plansPanel');
const $plansList = document.getElementById('plansList');
const $plansBadge = document.getElementById('plansBadge');
const $plansChevron = document.getElementById('plansChevron');
let plansOpen = false;

window.togglePlansPanel = function() {
  plansOpen = !plansOpen;
  $plansList.style.display = plansOpen ? 'block' : 'none';
  $plansChevron.classList.toggle('open', plansOpen);
  if (plansOpen) loadPlans();
};

async function loadPlans() {
  try {
    const plans = await apiGet('/api/plans');

    $plansBadge.textContent = plans.length;
    $plansBadge.style.display = plans.length > 0 ? 'inline' : 'none';

    if (plans.length === 0) {
      $plansList.innerHTML = '<div style="padding:8px 10px;font-size:12px;color:var(--text-muted);">Nenhum plano criado.</div>';
      return;
    }

    $plansList.innerHTML = plans.map(p => {
      const pct = p.step_count > 0 ? Math.round((p.done_count / p.step_count) * 100) : 0;
      const icon = pct === 100 ? '✅' : pct > 0 ? '🔄' : '⬜';
      return `
        <div class="plan-item" onclick="viewPlan(${p.id})">
          <div class="plan-item-goal">${icon} ${escapeHtml(p.goal)}</div>
          <div class="plan-item-meta">
            <span>${p.done_count}/${p.step_count}</span>
            <div class="plan-progress">
              <div class="plan-progress-bar" style="width:${pct}%;"></div>
            </div>
            <span>${pct}%</span>
          </div>
        </div>`;
    }).join('');
  } catch (e) {
    console.error('Error loading plans:', e);
  }
}
window.loadPlans = loadPlans;

window.viewPlan = async function(planId) {
  try {
    const plan = await apiGet('/api/plans/' + planId);

    const statusIcon = { pending: '⬜', in_progress: '🔄', done: '✅' };
    const stepsHtml = plan.steps.map((s, i) => `
      <div class="plan-modal-step">
        <span class="step-icon">${statusIcon[s.status] || '⬜'}</span>
        <div>
          <div class="step-text">${i + 1}. ${escapeHtml(s.text)}</div>
          ${s.result ? `<div class="step-result">→ ${escapeHtml(s.result)}</div>` : ''}
        </div>
      </div>
    `).join('');

    const overlay = document.createElement('div');
    overlay.className = 'plan-modal-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = `
      <div class="plan-modal">
        <h3>📋 ${escapeHtml(plan.goal)}</h3>
        ${stepsHtml}
        <button class="plan-modal-close" onclick="this.closest('.plan-modal-overlay').remove()">Fechar</button>
      </div>`;
    document.body.appendChild(overlay);
  } catch (e) {
    console.error('Error viewing plan:', e);
  }
};


// ─── Initialize ───
async function init() {
  showEmptyState();
  DOM.messageInput.focus();
  setTheme(window.currentTheme);

  const healthy = await checkHealth();
  if (healthy) {
    const [, , ollamaStatus] = await Promise.all([
      loadModels(),
      loadConversations(),
      checkOllamaStatus().then(async () => {
        try {
          return await apiGet('/api/ollama/status');
        } catch (e) {
          return { status: 'offline', models_count: 0 };
        }
      })
    ]);

    // Load plans badge count
    loadPlans();

    // Determine if wizard should show
    const wizardDone = localStorage.getItem('denai-wizard-done') === '1';
    const ollamaOffline = DOM.ollamaBadge.classList.contains('offline');
    const noModels = DOM.modelSelect.options.length === 0 ||
                     (DOM.modelSelect.options.length === 1 && DOM.modelSelect.options[0].value === '');

    if (!wizardDone && (ollamaOffline || noModels)) {
      showWizard();
    }
  } else {
    showToast('Servidor não encontrado. Verifique se o backend está rodando.', 'error');
    DOM.ollamaBadge.className = 'ollama-badge offline';
    DOM.ollamaLabel.textContent = 'Desconectado';

    // Show wizard if never completed
    const wizardDone = localStorage.getItem('denai-wizard-done') === '1';
    if (!wizardDone) {
      showWizard();
    }
  }

  // Periodic checks
  setInterval(checkHealth, 30000);
  setInterval(checkOllamaStatus, 15000);
}

// Start the app
init();
