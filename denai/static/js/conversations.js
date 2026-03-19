/* ═══════════════════════════════════════════════════════════
   DENAI — CONVERSATIONS: list, select, load, render, search
   ═══════════════════════════════════════════════════════════ */

// ─── Conversations ───
async function loadConversations() {
  try {
    const data = await apiGet('/api/conversations');
    window.conversations = data.conversations || data || [];
    renderConversationList();
  } catch (e) {
    console.error('Failed to load conversations:', e);
  }
}
window.loadConversations = loadConversations;

function renderConversationList(filteredList) {
  const list = filteredList || window.conversations;
  const label = '<div class="sidebar-section-label">Conversas</div>';
  if (list.length === 0) {
    DOM.conversationList.innerHTML = label +
      '<div style="padding: 16px 12px; text-align: center; color: var(--text-muted); font-size: 13px;">Nenhuma conversa ainda</div>';
    return;
  }

  // Sort by updated_at desc
  const sorted = [...list].sort((a, b) => {
    const ta = new Date(a.updated_at || a.created_at || 0);
    const tb = new Date(b.updated_at || b.created_at || 0);
    return tb - ta;
  });

  let html = label;
  sorted.forEach(conv => {
    const id = conv.id || conv.conversation_id;
    const title = conv.title || 'Nova Conversa';
    const time = relativeTime(conv.updated_at || conv.created_at);
    const isActive = id === window.currentConversationId;

    html += `
      <div class="conversation-item ${isActive ? 'active' : ''}" data-id="${escapeAttr(id)}" onclick="selectConversation('${escapeAttr(id)}')">
        <span class="conv-icon">💬</span>
        <div class="conv-info">
          <div class="conv-title">${escapeHtml(title)}</div>
          <div class="conv-time">${escapeHtml(time)}</div>
        </div>
        <button class="conv-delete" onclick="event.stopPropagation(); deleteConversation('${escapeAttr(id)}', '${escapeAttr(title)}')" title="Excluir conversa">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>`;
  });

  DOM.conversationList.innerHTML = html;
}
window.renderConversationList = renderConversationList;


// ─── Select conversation ───
window.selectConversation = async function(id) {
  if (window.isStreaming) return;

  window.currentConversationId = id;
  renderConversationList();

  const conv = window.conversations.find(c => (c.id || c.conversation_id) === id);
  DOM.headerTitle.textContent = conv ? (conv.title || 'Nova Conversa') : 'Nova Conversa';

  // Close sidebar on mobile
  if (window.innerWidth <= 768) {
    window.sidebarOpen = false;
    DOM.sidebar.classList.add('collapsed');
    DOM.sidebarOverlay.classList.remove('visible');
  }

  await loadMessages(id);
};


// ─── Load messages ───
async function loadMessages(convId) {
  try {
    const data = await apiGet(`/api/conversations/${convId}/messages`);
    const messages = data.messages || data || [];
    renderMessages(messages);
    scrollToBottom(true);
  } catch (e) {
    showToast('Erro ao carregar mensagens', 'error');
  }
}
window.loadMessages = loadMessages;

function renderMessages(messages) {
  if (messages.length === 0) {
    showEmptyState();
    return;
  }

  let html = '';
  messages.forEach(msg => {
    const role = msg.role || 'assistant';
    if (role === 'system') return;

    if (role === 'tool' || msg.tool_calls) {
      // Tool calls and results are rendered inline with assistant messages
      if (msg.tool_calls) {
        msg.tool_calls.forEach(tc => {
          html += renderToolCallCard(tc, null);
        });
      }
      if (role === 'tool') {
        // This is a tool result — skip standalone render, it's folded into cards
        return;
      }
    }

    if (role === 'user' || role === 'assistant') {
      html += renderMessageBubble(role, msg.content || '', msg.created_at || msg.timestamp);
    }
  });

  DOM.messagesInner.innerHTML = html;
}
window.renderMessages = renderMessages;

function renderMessageBubble(role, content, timestamp) {
  const avatar = role === 'assistant' ? '🐺' : '👤';
  const timeStr = timestamp ? formatTime(timestamp) : '';
  const rendered = role === 'assistant' ? renderMarkdown(content) : escapeHtml(content);

  return `
    <div class="message ${role}">
      <div class="message-avatar">${avatar}</div>
      <div class="message-content">
        <div class="message-bubble">${rendered}</div>
        ${timeStr ? `<div class="message-time">${timeStr}</div>` : ''}
      </div>
    </div>`;
}
window.renderMessageBubble = renderMessageBubble;

function renderMarkdown(text) {
  if (!text) return '';
  try {
    return marked.parse(text);
  } catch (e) {
    return escapeHtml(text);
  }
}
window.renderMarkdown = renderMarkdown;

function formatTime(dateStr) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return '';
  }
}
window.formatTime = formatTime;

function renderToolCallCard(toolCall, result) {
  const name = toolCall.function?.name || toolCall.name || 'unknown_tool';
  const args = toolCall.function?.arguments || toolCall.arguments || toolCall.args || '';
  const argsStr = typeof args === 'string' ? args : JSON.stringify(args, null, 2);
  const resultStr = result ? (typeof result === 'string' ? result : JSON.stringify(result, null, 2)) : null;
  const meta = getToolMeta(name);
  const isThink = (name === 'think');
  const cardId = 'tc-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8);
  const TRUNCATE = 2000;

  // ── Think tool: inline, always visible, no collapse ──
  if (isThink) {
    const parsed = tryParseJSON(argsStr);
    const content = parsed ? (parsed.thought || parsed.content || argsStr) : argsStr;
    return `
      <div class="think-card">
        <div class="think-label">${meta.icon} Raciocínio interno</div>
        <div class="think-content">${escapeHtml(content)}</div>
      </div>`;
  }

  // ── Standard tool card ──
  const statusClass = resultStr ? 'done' : 'running';
  const cardClass = resultStr ? '' : ' running-card';
  const statusIcon = resultStr
    ? '✓ concluído'
    : '<span class="tool-call-spinner"></span> executando';
  const needsTruncation = resultStr && resultStr.length > TRUNCATE;
  const displayResult = needsTruncation ? resultStr.slice(0, TRUNCATE) : resultStr;

  return `
    <div class="tool-call-card${cardClass}" style="border-left: 3px solid ${meta.color};" data-card-id="${cardId}">
      <div class="tool-call-header" onclick="toggleToolCall(this)">
        <svg class="tool-call-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
        <span class="tool-call-icon">${meta.icon}</span>
        <span class="tool-call-name" style="color: ${meta.color};">${escapeHtml(name)}</span>
        <span class="tool-call-status ${statusClass}">${statusIcon}</span>
      </div>
      <div class="tool-call-body">
        <div class="tool-call-section-label">Argumentos</div>
        <pre>${escapeHtml(argsStr)}</pre>
        ${resultStr ? `
        <div class="tool-call-result-header">
          <span class="tool-call-section-label" style="margin:0;">Resultado</span>
          <button class="tool-copy-btn" onclick="copyToolResult(this)" title="Copiar resultado">📋</button>
        </div>
        <pre class="tool-result-pre">${escapeHtml(displayResult)}</pre>
        ${needsTruncation ? `
        <pre class="tool-result-full" style="display:none;">${escapeHtml(resultStr)}</pre>
        <button class="tool-show-more-btn" style="color:${meta.color}; border-color:${meta.color}33;"
          onclick="toggleToolResult(this)">mostrar mais (${formatBytes(resultStr.length)})</button>
        ` : ''}
        ` : ''}
      </div>
    </div>`;
}
window.renderToolCallCard = renderToolCallCard;


// ─── Empty state ───
function showEmptyState() {
  DOM.messagesInner.innerHTML = `
    <div class="empty-state">
      <div class="empty-wolf">🐺</div>
      <h2>Bem-vindo ao DenAI</h2>
      <p>Seu assistente IA local. Escolha um modelo na barra lateral e comece a conversar.</p>
      <div class="suggested-prompts">
        <button class="suggested-prompt" onclick="useSuggestion(this)">
          <span class="prompt-icon">💻</span>
          Explique como funciona um servidor HTTP em Python
        </button>
        <button class="suggested-prompt" onclick="useSuggestion(this)">
          <span class="prompt-icon">🧠</span>
          Quais são as diferenças entre REST e GraphQL?
        </button>
        <button class="suggested-prompt" onclick="useSuggestion(this)">
          <span class="prompt-icon">🐳</span>
          Crie um Dockerfile otimizado para uma app Node.js
        </button>
        <button class="suggested-prompt" onclick="useSuggestion(this)">
          <span class="prompt-icon">📊</span>
          Escreva um script bash que monitore uso de CPU e memória
        </button>
      </div>
    </div>`;
}
window.showEmptyState = showEmptyState;

window.useSuggestion = function(btn) {
  const text = btn.textContent.trim();
  // Remove the emoji prefix
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const prompt = lines.length > 1 ? lines[1] : lines[0];
  DOM.messageInput.value = prompt;
  DOM.messageInput.dispatchEvent(new Event('input'));
  DOM.messageInput.focus();
};


// ─── New chat ───
async function newChat() {
  if (window.isStreaming) return;

  window.currentConversationId = null;
  DOM.headerTitle.textContent = 'Nova Conversa';
  showEmptyState();
  renderConversationList();
  DOM.messageInput.focus();

  // Close sidebar on mobile
  if (window.innerWidth <= 768) {
    window.sidebarOpen = false;
    DOM.sidebar.classList.add('collapsed');
    DOM.sidebarOverlay.classList.remove('visible');
  }
}
window.newChat = newChat;

DOM.btnNewChat.addEventListener('click', newChat);


// ─── Search conversations ───
let searchTimeout = null;

DOM.searchInput.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  const query = DOM.searchInput.value.trim();

  if (!query) {
    // Reset to full list
    renderConversationList();
    return;
  }

  searchTimeout = setTimeout(async () => {
    try {
      const data = await apiGet(`/api/conversations/search?q=${encodeURIComponent(query)}`);
      const results = data.results || [];
      renderSearchResults(results, query);
    } catch (e) {
      // Fallback: local filter
      const filtered = window.conversations.filter(c => {
        const title = (c.title || '').toLowerCase();
        return title.includes(query.toLowerCase());
      });
      renderConversationList(filtered);
    }
  }, 300);
});

function renderSearchResults(results, query) {
  const label = `<div class="sidebar-section-label">Resultados para "${escapeHtml(query)}"</div>`;

  if (results.length === 0) {
    DOM.conversationList.innerHTML = label +
      '<div style="padding: 16px 12px; text-align: center; color: var(--text-muted); font-size: 13px;">Nenhum resultado</div>';
    return;
  }

  let html = label;
  results.forEach(r => {
    const id = r.id;
    const title = r.title || 'Nova Conversa';
    const snippet = r.snippet ? `<div style="font-size:11px;color:var(--text-muted);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(r.snippet)}</div>` : '';
    const isActive = id === window.currentConversationId;

    html += `
      <div class="conversation-item ${isActive ? 'active' : ''}" data-id="${escapeAttr(id)}" onclick="selectConversation('${escapeAttr(id)}')">
        <span class="conv-icon">🔍</span>
        <div class="conv-info">
          <div class="conv-title">${escapeHtml(title)}</div>
          ${snippet}
        </div>
      </div>`;
  });

  DOM.conversationList.innerHTML = html;
}
window.renderSearchResults = renderSearchResults;


// ─── Export conversation ───
DOM.btnExport.addEventListener('click', (e) => {
  e.stopPropagation();
  DOM.exportDropdown.classList.toggle('visible');
});

// Close dropdown on outside click
document.addEventListener('click', () => {
  DOM.exportDropdown.classList.remove('visible');
});

window.exportConversation = async function(format) {
  DOM.exportDropdown.classList.remove('visible');

  if (!window.currentConversationId) {
    showToast('Selecione uma conversa para exportar', 'error');
    return;
  }

  try {
    const url = `/api/conversations/${window.currentConversationId}/export?format=${format}`;
    const key = getApiKey();
    const fullUrl = url + (key ? `&key=${encodeURIComponent(key)}` : '');

    // Fetch and trigger download
    const resp = await fetch(fullUrl, { headers: authHeaders() });
    if (!resp.ok) throw new Error(`Erro: ${resp.status}`);

    const blob = await resp.blob();
    const filename = resp.headers.get('Content-Disposition')?.match(/filename="(.+)"/)?.[1]
      || `conversa.${format === 'markdown' ? 'md' : 'json'}`;

    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);

    showToast(`Conversa exportada como ${format.toUpperCase()}`, 'success');
  } catch (e) {
    showToast(`Erro ao exportar: ${e.message}`, 'error');
  }
};


// ─── Delete conversation ───
window.deleteConversation = async function(id, title) {
  const confirmed = await showConfirm(
    'Excluir conversa',
    `Tem certeza que quer excluir "${title}"? Essa ação não pode ser desfeita.`
  );
  if (!confirmed) return;

  try {
    await apiDelete(`/api/conversations/${id}`);
    window.conversations = window.conversations.filter(c => (c.id || c.conversation_id) !== id);
    renderConversationList();

    if (window.currentConversationId === id) {
      window.currentConversationId = null;
      DOM.headerTitle.textContent = 'Nova Conversa';
      showEmptyState();
    }

    showToast('Conversa excluída', 'success');
  } catch (e) {
    showToast('Erro ao excluir conversa', 'error');
  }
};
