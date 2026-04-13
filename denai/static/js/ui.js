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
  // Load system profile on step 3
  if (step === 3) {
    wizardLoadSystemProfile();
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

// ─── Wizard Step 3: Smart model selection ───
window._systemProfile = null;

window.wizardLoadSystemProfile = async function() {
  const cardsEl = document.getElementById('wizardModelCards');
  if (!cardsEl) return;

  // Show loading state
  cardsEl.innerHTML = `
    <div class="wizard-profile-loading">
      <span class="counter-spinner"></span>
      Analisando sua máquina…
    </div>`;

  try {
    const profile = await apiGet('/api/system/profile');
    window._systemProfile = profile;
    _renderWizardModelCards(profile);
  } catch (e) {
    // Fallback: show static cards
    cardsEl.innerHTML = `
      <div class="wizard-model-card" onclick="wizardSelectModel('llama3.2:3b', this)">
        <span class="model-emoji">🚀</span>
        <div class="model-info">
          <div class="model-name">llama3.2:3b</div>
          <div class="model-desc">Rápido e leve — ótimo pra começar</div>
        </div>
        <span class="model-size">~2 GB</span>
      </div>
      <div class="wizard-model-card" onclick="wizardSelectModel('llama3.1:8b', this)">
        <span class="model-emoji">🧠</span>
        <div class="model-info">
          <div class="model-name">llama3.1:8b</div>
          <div class="model-desc">Mais inteligente — melhor qualidade</div>
        </div>
        <span class="model-size">~4.7 GB</span>
      </div>`;
  }
};

function _renderWizardModelCards(profile) {
  const cardsEl = document.getElementById('wizardModelCards');
  if (!cardsEl) return;

  const rec = profile.recommendation;
  const ramGb = profile.ram_gb;

  // Header com info da máquina
  let headerHtml = `<div class="wizard-machine-info">
    💻 <b>${ramGb}GB RAM</b>`;
  if (profile.vram_gb) headerHtml += ` · GPU ${profile.vram_gb}GB VRAM`;
  if (profile.disk_free_gb < 10) {
    headerHtml += ` · ⚠️ ${profile.disk_free_gb.toFixed(0)}GB livre em disco`;
  }
  headerHtml += `</div>`;

  // Card de recomendação
  const recModel = profile.model_catalog.find(m => m.name === rec.model) || {
    name: rec.model, emoji: '✅', description: rec.reason, size_gb: 0
  };

  let recBadge = rec.already_installed
    ? `<span class="wizard-badge installed">⚡ Já instalado</span>`
    : `<span class="wizard-badge recommended">✅ Recomendado</span>`;

  let recCard = `
    <div class="wizard-model-card recommended-card" onclick="wizardSelectModel('${escapeAttr(rec.model)}', this)">
      <span class="model-emoji">${recModel.emoji || '🤖'}</span>
      <div class="model-info">
        <div class="model-name">${escapeHtml(rec.model)} ${recBadge}</div>
        <div class="model-desc">${escapeHtml(rec.reason)}</div>
      </div>
      ${recModel.size_gb ? `<span class="model-size">~${recModel.size_gb}GB</span>` : ''}
    </div>`;

  // Cards alternativos (compatíveis, exceto o recomendado)
  const altCards = (rec.alternatives || [])
    .filter(a => a.name !== rec.model)
    .slice(0, 3)
    .map(alt => {
      const installed = profile.installed_models.some(i => i.startsWith(alt.name.split(':')[0]));
      const warning = alt.ram_min_gb > ramGb;
      const warnHtml = warning
        ? `<div class="wizard-model-warning">⚠️ Requer ~${alt.ram_min_gb}GB RAM</div>` : '';
      const instBadge = installed ? `<span class="wizard-badge installed" style="font-size:10px;">instalado</span>` : '';
      return `
        <div class="wizard-model-card ${warning ? 'compat-warning' : ''}"
             onclick="wizardSelectModel('${escapeAttr(alt.name)}', this)">
          <span class="model-emoji">${alt.emoji}</span>
          <div class="model-info">
            <div class="model-name">${escapeHtml(alt.name)} ${instBadge}</div>
            <div class="model-desc">${escapeHtml(alt.description)}</div>
            ${warnHtml}
          </div>
          <span class="model-size">~${alt.size_gb}GB</span>
        </div>`;
    }).join('');

  cardsEl.innerHTML = headerHtml + recCard + altCards;
}

window.wizardSelectedModel = null;

window.wizardSelectModel = function(modelName, cardEl) {
  // Destacar card selecionado
  document.querySelectorAll('#wizardModelCards .wizard-model-card')
    .forEach(c => c.classList.remove('selected-card'));
  if (cardEl) cardEl.classList.add('selected-card');
  window.wizardSelectedModel = modelName;

  // Se já instalado, mostrar botão "Usar agora"
  const profile = window._systemProfile;
  const isInstalled = profile && profile.installed_models.some(
    i => i === modelName || i.startsWith(modelName.split(':')[0])
  );

  const actionEl = document.getElementById('wizardModelAction');
  if (actionEl) {
    if (isInstalled) {
      actionEl.innerHTML = `<button class="wizard-btn" onclick="wizardUseModel('${escapeAttr(modelName)}')">
        ⚡ Usar ${escapeHtml(modelName)} agora →
      </button>`;
    } else {
      actionEl.innerHTML = `<button class="wizard-btn" onclick="wizardPullModel('${escapeAttr(modelName)}', null)">
        ⬇️ Baixar e usar ${escapeHtml(modelName)} →
      </button>`;
    }
  }
};

window.wizardUseModel = function(modelName) {
  window.currentModel = modelName;
  if (DOM.modelSelect) DOM.modelSelect.value = modelName;
  updateModelLabel();
  wizardNext(4);
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
    // Load providers after models (non-blocking)
    loadProviders().catch(() => {});

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

// ─── Auto-Update Check ───
let _pendingUpdateVersion = null;
let _lastCheckedVersion = null;
let _pendingReleaseNotes = null;

async function checkForUpdates() {
  try {
    const data = await apiGet('/api/update/check');
    if (data.update_available && data.latest_version !== _lastCheckedVersion) {
      _pendingUpdateVersion = data.latest_version;
      _lastCheckedVersion = data.latest_version;
      _pendingReleaseNotes = data.release_notes || null;

      // Toast não-intrusivo com botão para abrir modal
      const existingToast = document.querySelector('.toast.update-toast');
      if (existingToast) existingToast.remove();

      const toast = document.createElement('div');
      toast.className = 'toast info update-toast';
      toast.style.cssText = 'cursor:pointer;display:flex;align-items:center;gap:8px;';
      toast.innerHTML = `🆕 DenAI <b>${data.latest_version}</b> disponível
        <button onclick="openUpdateModal('${escapeAttr(data.current_version)}','${escapeAttr(data.latest_version)}', window._pendingReleaseNotes)"
          style="background:var(--accent);color:#0a0e1a;border:none;border-radius:4px;padding:4px 10px;cursor:pointer;font-size:12px;font-weight:600;">
          Ver e instalar
        </button>`;
      DOM.toastContainer.appendChild(toast);
    }
  } catch (e) {
    console.debug('Update check failed:', e);
  }
}
window.checkForUpdates = checkForUpdates;

// ─── Update Modal ───
window.openUpdateModal = function(currentVersion, newVersion, releaseNotes) {
  document.getElementById('updateCurrentVersion').textContent = `v${currentVersion}`;
  document.getElementById('updateNewVersion').textContent = `v${newVersion}`;
  document.getElementById('updateLog').style.display = 'none';
  document.getElementById('updateLogInner').textContent = '';
  document.getElementById('updateStatus').textContent = '';
  document.getElementById('updateStatus').className = 'update-status';
  document.getElementById('updateActions').innerHTML = `
    <button class="pf-btn-cancel" onclick="closeUpdateModal()">Cancelar</button>
    <button class="pf-btn-save" id="btnInstallUpdate" onclick="startInstallUpdate()">Instalar atualização</button>`;

  // Exibir changelog se disponível
  const changelogEl = document.getElementById('updateChangelog');
  const changelogBody = document.getElementById('updateChangelogBody');
  if (releaseNotes && changelogEl && changelogBody) {
    // Simplificar markdown: remover headers pesados, manter bullets e texto
    const simplified = releaseNotes
      .replace(/^## .+$/m, '')           // remover título da seção
      .replace(/\*\*(.+?)\*\*/g, '$1')   // remover bold
      .replace(/`(.+?)`/g, '$1')         // remover inline code
      .replace(/^\s*[-*]\s+/gm, '• ')    // normalizar bullets
      .replace(/\n{3,}/g, '\n\n')        // colapsar linhas em branco
      .trim();
    changelogBody.textContent = simplified.slice(0, 800) + (simplified.length > 800 ? '…' : '');
    changelogEl.style.display = 'block';
  } else if (changelogEl) {
    changelogEl.style.display = 'none';
  }

  document.getElementById('updateModalOverlay').style.display = 'flex';
  const toast = document.querySelector('.toast.update-toast');
  if (toast) toast.remove();
};

window.closeUpdateModal = function() {
  document.getElementById('updateModalOverlay').style.display = 'none';
};

window.startInstallUpdate = async function() {
  const btn = document.getElementById('btnInstallUpdate');
  if (btn) { btn.disabled = true; btn.textContent = 'Instalando…'; }

  const logEl = document.getElementById('updateLogInner');
  const logContainer = document.getElementById('updateLog');
  const statusEl = document.getElementById('updateStatus');

  logContainer.style.display = 'block';
  logEl.textContent = '';
  statusEl.textContent = 'Instalando…';
  statusEl.className = 'update-status';

  try {
    const resp = await fetch(API_BASE + '/api/update/install', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(trimmed.slice(6));

          if (event.type === 'progress') {
            logEl.textContent += event.line + '\n';
            logContainer.scrollTop = logContainer.scrollHeight;

          } else if (event.type === 'success') {
            statusEl.textContent = `✅ ${event.message}`;
            statusEl.className = 'update-status success';
            // Substituir botões por Reiniciar agora / Reiniciar depois
            document.getElementById('updateActions').innerHTML = `
              <button class="pf-btn-cancel" onclick="closeUpdateModal()">Reiniciar depois</button>
              <button class="btn-restart-now" onclick="restartServer()">🔄 Reiniciar agora</button>`;

          } else if (event.type === 'error') {
            statusEl.textContent = `❌ ${event.message}`;
            statusEl.className = 'update-status error';
            if (btn) { btn.disabled = false; btn.textContent = 'Tentar novamente'; }
          }
        } catch (_) {}
      }
    }
  } catch (e) {
    statusEl.textContent = `❌ Erro: ${e.message}`;
    statusEl.className = 'update-status error';
    if (btn) { btn.disabled = false; btn.textContent = 'Tentar novamente'; }
  }
};

window.restartServer = async function() {
  const btn = document.querySelector('.btn-restart-now');
  if (btn) { btn.disabled = true; btn.textContent = 'Reiniciando…'; }

  const statusEl = document.getElementById('updateStatus');
  statusEl.textContent = 'Reiniciando servidor…';
  statusEl.className = 'update-status';

  try {
    await apiPost('/api/update/restart', {});
    statusEl.textContent = '🔄 Reconectando em instantes…';

    // Aguardar e tentar reconectar
    setTimeout(() => _waitForReconnect(0), 3000);
  } catch (e) {
    statusEl.textContent = '⚠️ Reinicie manualmente: pare e inicie o DenAI novamente.';
    statusEl.className = 'update-status error';
  }
};

function _waitForReconnect(attempts) {
  const maxAttempts = 20;
  const statusEl = document.getElementById('updateStatus');
  if (attempts >= maxAttempts) {
    if (statusEl) statusEl.textContent = '⚠️ Servidor não respondeu. Reinicie manualmente.';
    return;
  }
  fetch(API_BASE + '/api/health')
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(() => {
      // Reconectou — recarregar a página
      window.location.reload();
    })
    .catch(() => {
      if (statusEl) statusEl.textContent = `🔄 Reconectando… (${attempts + 1}/${maxAttempts})`;
      setTimeout(() => _waitForReconnect(attempts + 1), 1500);
    });
}


// Start the app
init();

// Check for updates 5s after startup (non-blocking)
setTimeout(checkForUpdates, 5000);

// Check periodically every 6h
setInterval(checkForUpdates, 6 * 60 * 60 * 1000);
