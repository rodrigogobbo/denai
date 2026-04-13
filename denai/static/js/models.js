/* ═══════════════════════════════════════════════════════════
   DENAI — MODELS & PROVIDERS
   Multi-provider: Ollama, OpenAI-compat, Anthropic, Gemini...
   ═══════════════════════════════════════════════════════════ */

// ─── Health check + Ollama status ───
async function checkHealth() {
  try { await apiGet('/api/health'); return true; } catch (e) { return false; }
}
window.checkHealth = checkHealth;

async function checkOllamaStatus() {
  try {
    const data = await apiGet('/api/ollama/status');
    if (data.status === 'online') {
      DOM.ollamaBadge.className = 'ollama-badge online';
      const label = data.models_count > 0
        ? `Ollama ${data.version || ''} · ${data.models_count} modelo${data.models_count > 1 ? 's' : ''}`
        : `Ollama ${data.version || ''} · sem modelos`;
      DOM.ollamaLabel.textContent = label;
    } else {
      DOM.ollamaBadge.className = 'ollama-badge offline';
      DOM.ollamaLabel.textContent = 'Ollama offline';
    }
  } catch (e) {
    DOM.ollamaBadge.className = 'ollama-badge offline';
    DOM.ollamaLabel.textContent = 'Ollama offline';
  }
}
window.checkOllamaStatus = checkOllamaStatus;


// ─── Provider state ───
window._providers = [];
window._providerTemplates = [];
window._editingProvider = null; // name being edited


// ─── Load providers ───
async function loadProviders() {
  try {
    const data = await apiGet('/api/providers');
    window._providers = data.providers || [];
    _renderProvidersBadges();
  } catch (e) {
    window._providers = [];
  }
}
window.loadProviders = loadProviders;

async function loadProviderTemplates() {
  try {
    const data = await apiGet('/api/providers/templates');
    window._providerTemplates = data.templates || [];
    _populateTemplateSelect();
  } catch (e) {
    window._providerTemplates = [];
  }
}

function _populateTemplateSelect() {
  const sel = document.getElementById('pfTemplate');
  if (!sel) return;
  sel.innerHTML = '<option value="">— Personalizado —</option>';
  window._providerTemplates.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.id;
    opt.textContent = t.label;
    opt.title = t.description;
    sel.appendChild(opt);
  });
}


// ─── Sidebar badges ───
function _renderProvidersBadges() {
  const container = document.getElementById('providersList');
  if (!container) return;
  container.innerHTML = '';

  window._providers.forEach(p => {
    const badge = document.createElement('span');
    badge.className = 'provider-badge';
    badge.dataset.kind = p.kind;
    badge.textContent = p.name;
    badge.title = `${p.kind} — ${p.base_url || 'local'}`;
    container.appendChild(badge);
  });

  const manageBtn = document.createElement('button');
  manageBtn.className = 'provider-add-btn';
  manageBtn.textContent = '⚙';
  manageBtn.title = 'Gerenciar providers';
  manageBtn.addEventListener('click', openProviderModal);
  container.appendChild(manageBtn);
}


// ─── Modal open/close ───
function openProviderModal() {
  loadProviderTemplates();
  _renderModalProviderList();
  showProviderList();
  document.getElementById('providerModalOverlay').style.display = 'flex';
}
window.openProviderModal = openProviderModal;

function closeProviderModal(e) {
  if (e && e.target !== document.getElementById('providerModalOverlay')) return;
  document.getElementById('providerModalOverlay').style.display = 'none';
  window._editingProvider = null;
}
window.closeProviderModal = closeProviderModal;

function showProviderList() {
  document.getElementById('providerListSection').style.display = 'block';
  document.getElementById('providerFormSection').style.display = 'none';
  _renderModalProviderList();
}

function showAddProviderForm(editName) {
  window._editingProvider = editName || null;
  document.getElementById('providerListSection').style.display = 'none';
  document.getElementById('providerFormSection').style.display = 'block';
  document.getElementById('providerFormTitle').textContent = editName ? `Editar: ${editName}` : 'Novo provider';
  document.getElementById('pfTemplate').value = '';
  document.getElementById('pfTestResult').textContent = '';

  if (editName) {
    const p = window._providers.find(x => x.name === editName);
    if (p) {
      document.getElementById('pfName').value = p.name;
      document.getElementById('pfUrl').value = p.base_url;
      document.getElementById('pfKey').value = ''; // nunca preenche a key
      document.getElementById('pfModels').value = (p.models || []).join('\n');
    }
  } else {
    document.getElementById('pfName').value = '';
    document.getElementById('pfUrl').value = '';
    document.getElementById('pfKey').value = '';
    document.getElementById('pfModels').value = '';
  }
}
window.showAddProviderForm = showAddProviderForm;

function cancelProviderForm() {
  showProviderList();
  window._editingProvider = null;
}
window.cancelProviderForm = cancelProviderForm;


// ─── Modal provider list ───
function _renderModalProviderList() {
  const list = document.getElementById('providerModalList');
  if (!list) return;
  list.innerHTML = '';

  if (!window._providers.length) {
    list.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">Nenhum provider além do Ollama.</p>';
    return;
  }

  window._providers.forEach(p => {
    const row = document.createElement('div');
    row.className = 'provider-modal-row';
    const kindLabel = { ollama: '🦙 Ollama', openai: '🤖 OpenAI-compat', gpt4all: '💾 GPT4All' }[p.kind] || p.kind;
    row.innerHTML = `
      <div class="pmr-info">
        <span class="pmr-name">${escapeHtml(p.name)}</span>
        <span class="pmr-meta">${kindLabel} · ${escapeHtml(p.base_url || 'local')}</span>
        ${p.has_key ? '<span class="pmr-key-badge">🔑 key</span>' : ''}
      </div>
      <div class="pmr-actions">
        ${!p.is_default ? `
          <button class="pmr-btn-edit" onclick="showAddProviderForm('${escapeAttr(p.name)}')">Editar</button>
          <button class="pmr-btn-remove" onclick="removeProviderUI('${escapeAttr(p.name)}')">Remover</button>
        ` : '<span style="font-size:11px;color:var(--text-muted)">padrão</span>'}
      </div>`;
    list.appendChild(row);
  });
}


// ─── Template apply ───
function applyTemplate() {
  const sel = document.getElementById('pfTemplate');
  const tid = sel.value;
  if (!tid) return;
  const tpl = window._providerTemplates.find(t => t.id === tid);
  if (!tpl) return;
  document.getElementById('pfName').value = tpl.label;
  document.getElementById('pfUrl').value = tpl.base_url;
  document.getElementById('pfModels').value = (tpl.default_models || []).join('\n');
  document.getElementById('pfKey').value = '';
  document.getElementById('pfTestResult').textContent = '';
}
window.applyTemplate = applyTemplate;


// ─── Key visibility toggle ───
function toggleKeyVisibility() {
  const inp = document.getElementById('pfKey');
  inp.type = inp.type === 'password' ? 'text' : 'password';
}
window.toggleKeyVisibility = toggleKeyVisibility;


// ─── Test connection ───
async function testProviderConnection() {
  const url = document.getElementById('pfUrl').value.trim();
  const key = document.getElementById('pfKey').value.trim();
  const kind = _inferKind(url);
  const resultEl = document.getElementById('pfTestResult');
  const btn = document.getElementById('btnTestConn');

  if (!url) { resultEl.textContent = '⚠️ Informe a URL primeiro.'; return; }

  btn.disabled = true;
  btn.textContent = 'Testando...';
  resultEl.textContent = '';
  resultEl.className = 'pf-test-result';

  try {
    const data = await apiPost('/api/providers/test', { kind, base_url: url, api_key: key });
    if (data.ok) {
      const modelsInfo = data.models_found > 0
        ? ` · ${data.models_found} modelo${data.models_found > 1 ? 's' : ''} encontrado${data.models_found > 1 ? 's' : ''}`
        : '';
      resultEl.textContent = `✅ Conectado (${data.latency_ms}ms)${modelsInfo}`;
      resultEl.className = 'pf-test-result success';

      // Auto-fill models if found and field is empty
      const modelsField = document.getElementById('pfModels');
      if (data.models && data.models.length > 0 && !modelsField.value.trim()) {
        modelsField.value = data.models.join('\n');
      }
    } else {
      resultEl.textContent = `❌ ${data.error || 'Falha na conexão'}`;
      resultEl.className = 'pf-test-result error';
    }
  } catch (e) {
    resultEl.textContent = `❌ Erro: ${e.message}`;
    resultEl.className = 'pf-test-result error';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Testar conexão';
  }
}
window.testProviderConnection = testProviderConnection;

function _inferKind(url) {
  if (!url) return 'openai';
  if (url.includes('localhost:11434') || url.includes('/api/tags')) return 'ollama';
  return 'openai';
}


// ─── Save provider ───
async function saveProvider() {
  const name = document.getElementById('pfName').value.trim();
  const url = document.getElementById('pfUrl').value.trim();
  const key = document.getElementById('pfKey').value.trim();
  const modelsRaw = document.getElementById('pfModels').value.trim();
  const models = modelsRaw ? modelsRaw.split('\n').map(s => s.trim()).filter(Boolean) : [];
  const kind = _inferKind(url);

  if (!name) { showToast('Nome do provider é obrigatório.', 'error'); return; }
  if (!url)  { showToast('URL base é obrigatória.', 'error'); return; }

  const btn = document.getElementById('btnSaveProvider');
  btn.disabled = true;
  btn.textContent = 'Salvando...';

  try {
    const data = await apiPost('/api/providers', {
      name, kind, base_url: url, api_key: key, models,
      default_model: models[0] || '',
    });
    if (data.ok) {
      showToast(`Provider "${name}" salvo!`, 'success');
      await loadProviders();
      await loadModels();
      showProviderList();
      window._editingProvider = null;
    } else {
      showToast(`Erro: ${data.error}`, 'error');
    }
  } catch (e) {
    showToast(`Erro ao salvar: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Salvar';
  }
}
window.saveProvider = saveProvider;


// ─── Remove provider ───
async function removeProviderUI(name) {
  if (!confirm(`Remover o provider "${name}"?`)) return;
  try {
    const resp = await fetch(API_BASE + `/api/providers/${encodeURIComponent(name)}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    const data = await resp.json();
    if (data.ok) {
      showToast(`Provider "${name}" removido.`, 'success');
      await loadProviders();
      await loadModels();
      _renderModalProviderList();
    } else {
      showToast(`Erro: ${data.error}`, 'error');
    }
  } catch (e) {
    showToast(`Erro: ${e.message}`, 'error');
  }
}
window.removeProviderUI = removeProviderUI;


// ─── Models list ───
async function loadModels() {
  // Carregar perfil do sistema em background para badges de peso
  if (!window._systemProfile) {
    apiGet('/api/system/profile').then(p => { window._systemProfile = p; }).catch(() => {});
  }
  try {
    const data = await apiGet('/api/models');
    const models = data.models || [];
    DOM.modelSelect.innerHTML = '';

    if (models.length === 0) {
      DOM.modelSelect.innerHTML = '<option value="">Nenhum modelo</option>';
      return;
    }

    const byProvider = {};
    models.forEach(m => {
      const prov = m.provider || 'Ollama';
      if (!byProvider[prov]) byProvider[prov] = [];
      byProvider[prov].push(m);
    });

    const providerNames = Object.keys(byProvider);
    if (providerNames.length === 1) {
      models.forEach(m => {
        const name = typeof m === 'string' ? m : (m.name || m.model || '');
        if (!name) return;
        const opt = document.createElement('option');
        opt.value = name; opt.textContent = name;
        DOM.modelSelect.appendChild(opt);
      });
    } else {
      providerNames.forEach(provName => {
        const group = document.createElement('optgroup');
        group.label = provName;
        byProvider[provName].forEach(m => {
          const name = typeof m === 'string' ? m : (m.name || m.model || '');
          if (!name) return;
          const opt = document.createElement('option');
          opt.value = name; opt.textContent = name;
          opt.dataset.provider = provName;
          group.appendChild(opt);
        });
        DOM.modelSelect.appendChild(group);
      });
    }

    if (!window.currentModel && models.length > 0) {
      window.currentModel = typeof models[0] === 'string' ? models[0] : (models[0].name || models[0].model || '');
    }

    // Restaurar modelo salvo no perfil ativo (sobrescreve o padrão)
    try {
      const saved = await apiGet('/api/profiles/active/model');
      if (saved.model) {
        // Verificar se o modelo salvo ainda existe na lista
        const exists = models.some(m => {
          const n = typeof m === 'string' ? m : (m.name || m.model || '');
          return n === saved.model;
        });
        if (exists) window.currentModel = saved.model;
      }
    } catch (_) {}

    DOM.modelSelect.value = window.currentModel;
    updateModelLabel();
  } catch (e) {
    DOM.modelSelect.innerHTML = '<option value="">Erro ao carregar</option>';
  }
}
window.loadModels = loadModels;

DOM.modelSelect.addEventListener('change', () => {
  window.currentModel = DOM.modelSelect.value;
  updateModelLabel();
  // Persistir modelo no perfil ativo
  if (window.currentModel) {
    apiPost('/api/profiles/active/model', { model: window.currentModel }).catch(() => {});
  }
});

function updateModelLabel() {
  if (!window.currentModel) {
    DOM.inputModelLabel.textContent = '';
    return;
  }
  let label = `Modelo: ${window.currentModel}`;

  // Badge de peso baseado no perfil do sistema
  const profile = window._systemProfile;
  if (profile) {
    const entry = profile.model_catalog.find(
      m => window.currentModel.startsWith(m.name.split(':')[0])
    );
    if (entry) {
      const ramGb = profile.ram_gb;
      let badgeClass = 'ok';
      let badgeText = '';
      if (entry.ram_min_gb > ramGb) {
        badgeClass = 'heavy'; badgeText = '⚠️ pesado';
      } else if (entry.ram_min_gb > ramGb * 0.75) {
        badgeClass = 'medium'; badgeText = '〜 moderado';
      }
      if (badgeText) {
        label += ` <span class="model-weight-badge ${badgeClass}">${badgeText}</span>`;
        DOM.inputModelLabel.innerHTML = label;
        return;
      }
    }
  }
  DOM.inputModelLabel.textContent = label;
}
window.updateModelLabel = updateModelLabel;


// ─── Pull model ───
DOM.btnPull.addEventListener('click', async () => {
  const model = DOM.pullModelInput.value.trim();
  if (!model) return;

  DOM.pullStatus.textContent = `Baixando ${model}...`;
  DOM.pullStatus.className = 'pull-status';
  DOM.btnPull.disabled = true;

  try {
    const res = await fetch(API_BASE + '/api/pull', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ model }),
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
        text.split('\n').filter(l => l.trim()).forEach(line => {
          try {
            const parsed = JSON.parse(line);
            lastStatus = parsed.status || lastStatus;
            if (parsed.total && parsed.completed) {
              DOM.pullStatus.textContent = `${lastStatus} ${Math.round((parsed.completed / parsed.total) * 100)}%`;
            } else {
              DOM.pullStatus.textContent = lastStatus;
            }
          } catch (_) { DOM.pullStatus.textContent = line; }
        });
      }
    }

    DOM.pullStatus.textContent = `✓ ${model} baixado com sucesso!`;
    DOM.pullStatus.className = 'pull-status success';
    DOM.pullModelInput.value = '';
    await loadModels();
  } catch (e) {
    DOM.pullStatus.textContent = `✗ Erro: ${e.message}`;
    DOM.pullStatus.className = 'pull-status error';
  } finally {
    DOM.btnPull.disabled = false;
  }
});

DOM.pullModelInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); DOM.btnPull.click(); }
});
