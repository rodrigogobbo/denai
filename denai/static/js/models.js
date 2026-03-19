/* ═══════════════════════════════════════════════════════════
   DENAI — MODELS: health check, ollama status, load & pull
   ═══════════════════════════════════════════════════════════ */

// ─── Health check + Ollama status ───
async function checkHealth() {
  try {
    await apiGet('/api/health');
    return true;
  } catch (e) {
    return false;
  }
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


// ─── Models ───
async function loadModels() {
  try {
    const data = await apiGet('/api/models');
    const models = data.models || data || [];
    DOM.modelSelect.innerHTML = '';

    if (models.length === 0) {
      DOM.modelSelect.innerHTML = '<option value="">Nenhum modelo</option>';
      return;
    }

    models.forEach(m => {
      const name = typeof m === 'string' ? m : (m.name || m.model || '');
      if (!name) return;
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      DOM.modelSelect.appendChild(opt);
    });

    if (!window.currentModel && models.length > 0) {
      window.currentModel = typeof models[0] === 'string' ? models[0] : (models[0].name || models[0].model || '');
    }

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
});

function updateModelLabel() {
  DOM.inputModelLabel.textContent = window.currentModel ? `Modelo: ${window.currentModel}` : '';
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

    // Try to read streaming progress
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
              DOM.pullStatus.textContent = `${lastStatus} ${pct}%`;
            } else {
              DOM.pullStatus.textContent = lastStatus;
            }
          } catch (e) {
            // Not JSON, just show as text
            DOM.pullStatus.textContent = line;
          }
        }
      }
    }

    DOM.pullStatus.textContent = `✓ ${model} baixado com sucesso!`;
    DOM.pullStatus.className = 'pull-status success';
    DOM.pullModelInput.value = '';
    await loadModels();
  } catch (e) {
    DOM.pullStatus.textContent = `✗ Erro ao baixar: ${e.message}`;
    DOM.pullStatus.className = 'pull-status error';
  } finally {
    DOM.btnPull.disabled = false;
  }
});

DOM.pullModelInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    DOM.btnPull.click();
  }
});
