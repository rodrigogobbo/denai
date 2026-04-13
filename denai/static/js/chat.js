/* ═══════════════════════════════════════════════════════════
   DENAI — CHAT: send message (SSE streaming), retry, tool counter
   ═══════════════════════════════════════════════════════════ */

// ─── Tool Call Counter ───
window.toolCallCounters = {}; // per-message tracking

function getToolCounterHtml(current, total) {
  return `<div class="tool-counter-badge">
    <span class="counter-spinner"></span>
    Executando ferramenta ${current} de ${total}...
  </div>`;
}

function updateToolCounter(bubbleEl, current, total) {
  let counterEl = bubbleEl.querySelector('.tool-counter-badge');
  if (total <= 1) {
    if (counterEl) counterEl.remove();
    return;
  }
  if (current > total) {
    // All done
    if (counterEl) counterEl.remove();
    return;
  }
  if (!counterEl) {
    bubbleEl.insertAdjacentHTML('beforeend', getToolCounterHtml(current, total));
  } else {
    counterEl.innerHTML = `<span class="counter-spinner"></span> Executando ferramenta ${current} de ${total}...`;
  }
}
window.updateToolCounter = updateToolCounter;

function markToolCardComplete(cardEl) {
  // Remove running class, add completion flash
  cardEl.classList.remove('running-card');
  cardEl.classList.add('completed-flash');
  // Update status
  const statusEl = cardEl.querySelector('.tool-call-status');
  if (statusEl) {
    statusEl.className = 'tool-call-status done';
    statusEl.textContent = '✓ concluído';
  }
}
window.markToolCardComplete = markToolCardComplete;


// ─── Send message ───
async function sendMessage() {
  let text = DOM.messageInput.value.trim();
  if (!text || window.isStreaming) return;
  if (!window.currentModel) {
    showToast('Selecione um modelo primeiro', 'error');
    return;
  }

  // Resolve custom commands
  if (text.startsWith("/")) {
    // Interceptar /context antes dos outros comandos
    const contextMatch = text.match(/^\/context\s+(.+)$/);
    const contextOff = text.trim() === '/context off';
    const contextStatus = text.trim() === '/context';

    if (contextMatch) {
      const path = contextMatch[1].trim();
      await _handleContextActivate(path);
      return;
    }
    if (contextOff) {
      await _handleContextDeactivate();
      return;
    }
    if (contextStatus) {
      _showContextStatus();
      return;
    }

    // Interceptar /specs
    const specsMatch = text.match(/^\/specs\s+(.+)$/);
    const specsList = text.trim() === '/specs';

    if (specsList) {
      await _handleSpecsList();
      return;
    }
    if (specsMatch) {
      await _handleSpecsRead(specsMatch[1].trim());
      return;
    }

    const resolved = await window.resolveCommand(text);
    if (resolved) {
      text = resolved.prompt;
    }
  }

  window.lastUserMessage = text;  // Save for retry

  // Create conversation if needed
  if (!window.currentConversationId) {
    try {
      const data = await apiPost('/api/conversations', {
        title: text.slice(0, 80),
      });
      window.currentConversationId = data.id || data.conversation_id;
      const newConv = {
        id: window.currentConversationId,
        title: text.slice(0, 80),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      window.conversations.unshift(newConv);
      renderConversationList();
      DOM.headerTitle.textContent = text.slice(0, 80);
    } catch (e) {
      showToast('Erro ao criar conversa', 'error');
      return;
    }
  }

  // Clear empty state and add user message
  const emptyEl = DOM.messagesInner.querySelector('.empty-state');
  if (emptyEl) emptyEl.remove();

  DOM.messagesInner.insertAdjacentHTML('beforeend', renderMessageBubble('user', text, new Date().toISOString()));
  scrollToBottom(true);

  // Clear input
  DOM.messageInput.value = '';
  DOM.messageInput.style.height = 'auto';

  // Start streaming
  window.isStreaming = true;
  updateSendButton();

  // Show typing indicator
  const typingId = 'typing-' + Date.now();
  DOM.messagesInner.insertAdjacentHTML('beforeend', `
    <div class="typing-indicator" id="${typingId}">
      <div class="message-avatar">🐺</div>
      <div class="typing-dots">
        <span></span><span></span><span></span>
      </div>
    </div>`);
  scrollToBottom(true);

  try {
    window.abortController = new AbortController();

    const response = await fetch(API_BASE + '/api/chat', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        conversation_id: window.currentConversationId,
        message: text,
        model: window.currentModel,
        mode: window.getCurrentMode ? window.getCurrentMode() : "build",
      }),
      signal: window.abortController.signal,
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    // Remove typing indicator
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    // Create assistant message element
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant';
    msgDiv.innerHTML = `
      <div class="message-avatar">🐺</div>
      <div class="message-content">
        <div class="message-bubble"></div>
      </div>`;
    DOM.messagesInner.appendChild(msgDiv);

    const bubbleEl = msgDiv.querySelector('.message-bubble');
    let fullContent = '';
    let pendingToolCalls = {};
    let toolCallCount = 0;
    let toolCallCompleted = 0;

    // Parse SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let streamDone = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        // Handle SSE format: "data: {...}"
        let jsonStr = trimmed;
        if (trimmed.startsWith('data: ')) {
          jsonStr = trimmed.slice(6);
        } else if (trimmed.startsWith('data:')) {
          jsonStr = trimmed.slice(5);
        }

        if (!jsonStr || jsonStr === '[DONE]') continue;

        try {
          const event = JSON.parse(jsonStr);

          // Handle conversation_id
          if (event.conversation_id && !window.currentConversationId) {
            window.currentConversationId = event.conversation_id;
          }

          // Handle text content
          if (event.content !== undefined && event.content !== null) {
            fullContent += event.content;
            bubbleEl.innerHTML = renderMarkdown(fullContent);
            scrollToBottom();
          }

          // Handle choices array (OpenAI compatible format)
          if (event.choices) {
            for (const choice of event.choices) {
              const delta = choice.delta || {};
              if (delta.content) {
                fullContent += delta.content;
                bubbleEl.innerHTML = renderMarkdown(fullContent);
                scrollToBottom();
              }
            }
          }

          // Handle message field (some APIs use this)
          if (event.message && typeof event.message === 'object') {
            if (event.message.content) {
              fullContent += event.message.content;
              bubbleEl.innerHTML = renderMarkdown(fullContent);
              scrollToBottom();
            }
          }

          // Handle response field (another format)
          if (event.response) {
            fullContent += event.response;
            bubbleEl.innerHTML = renderMarkdown(fullContent);
            scrollToBottom();
          }

          // Handle tool calls
          if (event.tool_call) {
            const tc = event.tool_call;
            const tcId = tc.id || generateId();
            pendingToolCalls[tcId] = tc;
            toolCallCount++;

            const cardHtml = renderToolCallCard(tc, null);
            bubbleEl.insertAdjacentHTML('beforeend', cardHtml);
            updateToolCounter(bubbleEl, toolCallCount - toolCallCompleted, toolCallCount);
            scrollToBottom();
          }

          // Handle question (interactive)
          if (event.question) {
            const q = event.question;
            const qId = q.id || generateId();
            let inner = `<div class="q-text">❓ ${escapeHtml(q.text)}</div>`;
            if (q.options && q.options.length) {
              inner += '<div class="q-options">' +
                q.options.map(o => `<button class="q-opt-btn" onclick="answerQuestion('${escapeAttr(qId)}', this, '${escapeAttr(o)}')">${escapeHtml(o)}</button>`).join('') +
                '</div>';
            } else {
              inner += `<div class="q-free">
                <input type="text" placeholder="Digite sua resposta..." onkeydown="if(event.key==='Enter'){event.preventDefault();this.nextElementSibling.click();}">
                <button onclick="answerQuestion('${escapeAttr(qId)}', this)">Responder</button>
              </div>`;
            }
            bubbleEl.insertAdjacentHTML('beforeend', `<div class="question-card" id="qcard-${escapeAttr(qId)}">${inner}</div>`);
            scrollToBottom(true);
          }

          // Handle suggestions (suggest_skill / suggest_plugin)
          if (event.suggestion) {
            const s = event.suggestion;
            const icon = s.type === 'skill' ? '🧠' : '🔌';
            const label = s.type === 'skill' ? 'Skill' : 'Plugin';
            const installLabel = s.type === 'skill' ? 'Instalar Skill' : 'Instalar Plugin';
            bubbleEl.insertAdjacentHTML('beforeend', `
              <div class="suggestion-card" id="scard-${escapeAttr(s.id)}">
                <div class="suggestion-header">
                  <span class="suggestion-icon">${icon}</span>
                  <span class="suggestion-label">${label}: <b>${escapeHtml(s.id)}</b></span>
                </div>
                <div class="suggestion-reason">${escapeHtml(s.reason)}</div>
                <div class="suggestion-actions">
                  <button class="suggestion-install-btn"
                    onclick="installSuggestion('${escapeAttr(s.type)}', '${escapeAttr(s.id)}', this)">
                    ${installLabel}
                  </button>
                  <button class="suggestion-dismiss-btn"
                    onclick="dismissSuggestion('${escapeAttr(s.id)}')">
                    Dispensar
                  </button>
                </div>
              </div>`);
            scrollToBottom();
          }

          // Handle tool results
          if (event.tool_result) {
            const tr = event.tool_result;
            const tcId = tr.tool_call_id || tr.id;
            toolCallCompleted++;

            // Find the matching running card
            const cards = bubbleEl.querySelectorAll('.tool-call-card.running-card');
            const targetCard = cards.length > 0 ? cards[0] : bubbleEl.querySelector('.tool-call-card:last-of-type');

            if (targetCard) {
              // Detect tool name from card for meta color
              const nameEl = targetCard.querySelector('.tool-call-name');
              const toolName = nameEl ? nameEl.textContent.trim() : '';
              const meta = getToolMeta(toolName);

              // Flash green + update status
              markToolCardComplete(targetCard);

              const bodyEl = targetCard.querySelector('.tool-call-body');
              if (bodyEl) {
                const resultContent = typeof tr.result === 'string' ? tr.result : JSON.stringify(tr.result, null, 2);
                const TRUNCATE = 2000;
                const needsTruncation = resultContent.length > TRUNCATE;
                const displayResult = needsTruncation ? resultContent.slice(0, TRUNCATE) : resultContent;

                bodyEl.insertAdjacentHTML('beforeend', `
                  <div class="tool-call-result-header">
                    <span class="tool-call-section-label" style="margin:0;">Resultado</span>
                    <button class="tool-copy-btn" onclick="copyToolResult(this)" title="Copiar resultado">📋</button>
                  </div>
                  <pre class="tool-result-pre">${escapeHtml(displayResult)}</pre>
                  ${needsTruncation ? `
                  <pre class="tool-result-full" style="display:none;">${escapeHtml(resultContent)}</pre>
                  <button class="tool-show-more-btn" style="color:${meta.color}; border-color:${meta.color}33;"
                    onclick="toggleToolResult(this)">mostrar mais (${formatBytes(resultContent.length)})</button>
                  ` : ''}`);
              }
            }

            // Update or remove counter
            if (toolCallCompleted >= toolCallCount) {
              updateToolCounter(bubbleEl, toolCallCount + 1, toolCallCount); // will remove
            } else {
              updateToolCounter(bubbleEl, toolCallCount - toolCallCompleted, toolCallCount);
            }
            scrollToBottom();
          }

          // Handle done
          if (event.done === true) {
            streamDone = true;
            break;
          }

          // Handle error
          if (event.error) {
            bubbleEl.innerHTML += `<p style="color: var(--danger);">Erro: ${escapeHtml(event.error)}</p>`;
            scrollToBottom();
          }

        } catch (parseError) {
          // Not JSON — might be raw text SSE
          if (jsonStr && jsonStr !== '[DONE]') {
            fullContent += jsonStr;
            bubbleEl.innerHTML = renderMarkdown(fullContent);
            scrollToBottom();
          }
        }
      }
      if (streamDone) break;
    }

    // If bubble is empty after stream, show a fallback
    if (!fullContent && bubbleEl.innerHTML.trim() === '') {
      bubbleEl.innerHTML = '<p style="color: var(--text-muted); font-style: italic;">Resposta vazia</p>';
    }

    // Add timestamp
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = formatTime(new Date().toISOString());
    msgDiv.querySelector('.message-content').appendChild(timeDiv);

    // Update conversation in sidebar
    const conv = window.conversations.find(c => (c.id || c.conversation_id) === window.currentConversationId);
    if (conv) {
      conv.updated_at = new Date().toISOString();
      renderConversationList();
    }

  } catch (e) {
    // Remove typing indicator if still present
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    if (e.name === 'AbortError') {
      // User cancelled
    } else {
      // Classify the error
      let title = 'Erro ao obter resposta';
      let detail = e.message;
      let showRetry = true;

      if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
        title = 'Sem conexão com o servidor';
        detail = 'Verifique se o DenAI está rodando. Execute: python -m denai';
      } else if (e.message.includes('401')) {
        title = 'Não autorizado';
        detail = 'API key inválida. Reinicie o servidor.';
        showRetry = false;
      } else if (e.message.includes('429')) {
        title = 'Muitas requisições';
        detail = 'Aguarde um momento e tente novamente.';
      } else if (e.message.includes('500') || e.message.includes('502') || e.message.includes('503')) {
        title = 'Erro no servidor';
        detail = 'O Ollama pode estar sobrecarregado ou o modelo não está carregado.';
      }

      DOM.messagesInner.insertAdjacentHTML('beforeend', `
        <div class="error-banner">
          <span class="error-banner-icon">⚠️</span>
          <div class="error-banner-text">
            <div class="error-banner-title">${escapeHtml(title)}</div>
            <div class="error-banner-detail">${escapeHtml(detail)}</div>
          </div>
          ${showRetry ? '<button class="error-banner-retry" onclick="retryLastMessage()">Tentar novamente</button>' : ''}
        </div>`);
      scrollToBottom(true);
    }
  } finally {
    window.isStreaming = false;
    window.abortController = null;
    updateSendButton();
    DOM.messageInput.focus();
  }
}
window.sendMessage = sendMessage;

function updateSendButton() {
  DOM.btnSend.disabled = window.isStreaming;
}
window.updateSendButton = updateSendButton;


// ─── Retry last message ───
window.retryLastMessage = function() {
  if (!window.lastUserMessage || window.isStreaming) return;
  // Remove error banner
  const banners = DOM.messagesInner.querySelectorAll('.error-banner');
  banners.forEach(b => b.remove());
  // Re-send
  DOM.messageInput.value = window.lastUserMessage;
  sendMessage();
};

// ─── Suggestion cards ───
window.installSuggestion = async function(type, id, btn) {
  btn.disabled = true;
  btn.textContent = 'Instalando...';
  try {
    const endpoint = type === 'skill' ? '/api/skills/install' : '/api/marketplace/install';
    const body = type === 'skill' ? { name: id } : { plugin_id: id };
    await apiPost(endpoint, body);
    const card = document.getElementById(`scard-${id}`);
    if (card) {
      card.classList.add('suggestion-installed');
      card.querySelector('.suggestion-actions').innerHTML =
        '<span class="suggestion-done">✅ Instalado com sucesso</span>';
    }
    showToast(`${type === 'skill' ? 'Skill' : 'Plugin'} "${id}" instalado!`, 'success');
  } catch (e) {
    btn.disabled = false;
    btn.textContent = type === 'skill' ? 'Instalar Skill' : 'Instalar Plugin';
    showToast(`Erro ao instalar: ${e.message}`, 'error');
  }
};

window.dismissSuggestion = function(id) {
  const card = document.getElementById(`scard-${id}`);
  if (card) {
    card.style.opacity = '0';
    card.style.transition = 'opacity 0.2s';
    setTimeout(() => card.remove(), 200);
  }
};

// ─── /context command handlers ───────────────────────────
window._activeContext = null;

async function _handleContextActivate(path) {
  if (!window.currentConversationId) {
    // Criar conversa primeiro
    try {
      const data = await apiPost('/api/conversations', { title: `/context ${path}` });
      window.currentConversationId = data.id || data.conversation_id;
      window.conversations = window.conversations || [];
      window.conversations.unshift({ id: window.currentConversationId, title: `/context ${path}` });
      if (typeof renderConversationList === 'function') renderConversationList();
    } catch (e) {
      showToast('Erro ao criar conversa', 'error');
      return;
    }
  }

  // Exibir mensagem do usuário no chat
  const emptyEl = DOM.messagesInner.querySelector('.empty-state');
  if (emptyEl) emptyEl.remove();
  DOM.messagesInner.insertAdjacentHTML('beforeend',
    renderMessageBubble('user', `/context ${path}`, new Date().toISOString()));
  scrollToBottom(true);

  // Mostrar loading
  const loadingId = 'ctx-loading-' + Date.now();
  DOM.messagesInner.insertAdjacentHTML('beforeend',
    `<div class="typing-indicator" id="${loadingId}">
      <div class="message-avatar">📁</div>
      <div class="typing-dots"><span></span><span></span><span></span></div>
    </div>`);
  scrollToBottom(true);

  try {
    const data = await apiPost('/api/context/activate', {
      path,
      conversation_id: window.currentConversationId,
    });
    document.getElementById(loadingId)?.remove();

    if (data.ok) {
      window._activeContext = { project_name: data.project_name, path };
      _updateContextBadge();
      DOM.messagesInner.insertAdjacentHTML('beforeend',
        renderMessageBubble('assistant',
          `✅ Contexto ativado: **${data.project_name}** — ${data.file_count} arquivo(s) indexado(s).\n\nAgora posso responder perguntas sobre este repositório. Use \`rag_search\` ou pergunte diretamente.`,
          new Date().toISOString()));
    } else {
      DOM.messagesInner.insertAdjacentHTML('beforeend',
        renderMessageBubble('assistant', `❌ ${data.error || 'Erro ao ativar contexto.'}`, new Date().toISOString()));
    }
  } catch (e) {
    document.getElementById(loadingId)?.remove();
    DOM.messagesInner.insertAdjacentHTML('beforeend',
      renderMessageBubble('assistant', `❌ Erro: ${e.message}`, new Date().toISOString()));
  }
  scrollToBottom(true);
}

async function _handleContextDeactivate() {
  if (!window.currentConversationId || !window._activeContext) {
    showToast('Nenhum contexto ativo.', 'info');
    return;
  }
  try {
    await fetch(API_BASE + `/api/context/${encodeURIComponent(window.currentConversationId)}`, {
      method: 'DELETE', headers: authHeaders(),
    });
    window._activeContext = null;
    _updateContextBadge();
    showToast('Contexto desativado.', 'success');
  } catch (e) {
    showToast('Erro ao desativar contexto.', 'error');
  }
}

function _showContextStatus() {
  if (window._activeContext) {
    showToast(`Contexto ativo: 📁 ${window._activeContext.project_name}`, 'info');
  } else {
    showToast('Nenhum contexto ativo. Use /context <caminho>', 'info');
  }
}

function _updateContextBadge() {
  const existing = document.getElementById('contextBadge');
  if (existing) existing.remove();
  if (window._activeContext && DOM.inputModelLabel) {
    const badge = document.createElement('span');
    badge.id = 'contextBadge';
    badge.className = 'context-badge';
    badge.title = `Contexto: ${window._activeContext.path}\nUse /context off para desativar`;
    badge.textContent = `📁 ${window._activeContext.project_name}`;
    badge.onclick = () => showToast(`Caminho: ${window._activeContext.path}\n/context off para desativar`, 'info');
    DOM.inputModelLabel.insertAdjacentElement('afterend', badge);
  }
}

// ─── /specs command handlers ─────────────────────────────
async function _handleSpecsList() {
  _ensureConversation('/specs');
  const emptyEl = DOM.messagesInner.querySelector('.empty-state');
  if (emptyEl) emptyEl.remove();
  DOM.messagesInner.insertAdjacentHTML('beforeend',
    renderMessageBubble('user', '/specs', new Date().toISOString()));
  scrollToBottom(true);

  try {
    const data = await apiPost('/api/specs/list', { conversation_id: window.currentConversationId });
    let msg;
    if (data.error) {
      msg = `❌ ${data.error}`;
    } else if (!data.specs || data.specs.length === 0) {
      msg = data.message || 'Nenhuma spec encontrada.';
    } else {
      const lines = data.specs.map((s, i) => `**[${i+1}]** \`${s}\``);
      msg = `📋 **Specs em ${escapeHtml(data.project || '')}:**\n\n${lines.join('\n')}\n\nUse \`/specs <slug>\` para ver o conteúdo.`;
    }
    DOM.messagesInner.insertAdjacentHTML('beforeend',
      renderMessageBubble('assistant', msg, new Date().toISOString()));
  } catch (e) {
    DOM.messagesInner.insertAdjacentHTML('beforeend',
      renderMessageBubble('assistant', `❌ Erro: ${e.message}`, new Date().toISOString()));
  }
  scrollToBottom(true);
}

async function _handleSpecsRead(slug) {
  _ensureConversation(`/specs ${slug}`);
  const emptyEl = DOM.messagesInner.querySelector('.empty-state');
  if (emptyEl) emptyEl.remove();
  DOM.messagesInner.insertAdjacentHTML('beforeend',
    renderMessageBubble('user', `/specs ${slug}`, new Date().toISOString()));
  scrollToBottom(true);

  const loadingId = 'specs-loading-' + Date.now();
  DOM.messagesInner.insertAdjacentHTML('beforeend',
    `<div class="typing-indicator" id="${loadingId}">
      <div class="message-avatar">📋</div>
      <div class="typing-dots"><span></span><span></span><span></span></div>
    </div>`);
  scrollToBottom(true);

  try {
    const data = await apiPost('/api/specs/read', {
      conversation_id: window.currentConversationId, slug,
    });
    document.getElementById(loadingId)?.remove();
    const msg = data.error
      ? `❌ ${data.error}`
      : `# Spec: \`${escapeHtml(data.slug)}\`\n\n${data.content}`;
    DOM.messagesInner.insertAdjacentHTML('beforeend',
      renderMessageBubble('assistant', msg, new Date().toISOString()));
  } catch (e) {
    document.getElementById(loadingId)?.remove();
    DOM.messagesInner.insertAdjacentHTML('beforeend',
      renderMessageBubble('assistant', `❌ Erro: ${e.message}`, new Date().toISOString()));
  }
  scrollToBottom(true);
}

function _ensureConversation(cmdText) {
  if (!window.currentConversationId) {
    // Criar conversa em background para ter um ID
    apiPost('/api/conversations', { title: cmdText }).then(data => {
      window.currentConversationId = data.id || data.conversation_id;
    }).catch(() => {});
  }
}
