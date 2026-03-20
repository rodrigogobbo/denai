/**
 * Plugin Marketplace — browse, install, and manage plugins.
 */
(function () {
  "use strict";

  const CATEGORIES = {
    utilities: { label: "Utilitários", icon: "🔧" },
    productivity: { label: "Produtividade", icon: "⚡" },
    development: { label: "Desenvolvimento", icon: "💻" },
    data: { label: "Dados", icon: "📊" },
    fun: { label: "Diversão", icon: "🎮" },
  };

  // ── Inject styles ─────────────────────────────────────────────
  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      .marketplace-overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.5);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.2s ease;
      }
      @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
      .marketplace-panel {
        background: var(--bg-primary);
        border: 1px solid var(--border);
        border-radius: 12px;
        width: min(700px, 90vw);
        max-height: 80vh;
        display: flex;
        flex-direction: column;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      }
      .marketplace-header {
        padding: 20px 24px;
        border-bottom: 1px solid var(--border);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .marketplace-header h2 {
        margin: 0;
        font-size: 18px;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .marketplace-close {
        background: none;
        border: none;
        font-size: 20px;
        cursor: pointer;
        color: var(--text-secondary);
        padding: 4px 8px;
        border-radius: 6px;
      }
      .marketplace-close:hover { background: var(--bg-hover); }
      .marketplace-body {
        padding: 16px 24px;
        overflow-y: auto;
        flex: 1;
      }
      .marketplace-search {
        width: 100%;
        padding: 10px 14px;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--bg-secondary);
        color: var(--text-primary);
        font-size: 14px;
        margin-bottom: 16px;
      }
      .marketplace-search:focus {
        outline: none;
        border-color: var(--accent);
      }
      .marketplace-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 12px;
      }
      .marketplace-card {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 16px;
        background: var(--bg-secondary);
        transition: border-color 0.2s;
      }
      .marketplace-card:hover { border-color: var(--accent); }
      .marketplace-card-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
      }
      .marketplace-card-icon {
        font-size: 28px;
        line-height: 1;
      }
      .marketplace-card-info h3 {
        margin: 0;
        font-size: 15px;
        font-weight: 600;
      }
      .marketplace-card-info .version {
        font-size: 11px;
        color: var(--text-secondary);
      }
      .marketplace-card p {
        font-size: 13px;
        color: var(--text-secondary);
        margin: 0 0 12px;
        line-height: 1.4;
      }
      .marketplace-card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .marketplace-card .category-tag {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 10px;
        background: var(--bg-hover);
        color: var(--text-secondary);
      }
      .marketplace-btn {
        padding: 6px 16px;
        border-radius: 6px;
        border: none;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
      }
      .marketplace-btn.install {
        background: var(--accent);
        color: #fff;
      }
      .marketplace-btn.install:hover { filter: brightness(1.1); }
      .marketplace-btn.uninstall {
        background: transparent;
        border: 1px solid var(--border);
        color: var(--text-secondary);
      }
      .marketplace-btn.uninstall:hover {
        border-color: #ef4444;
        color: #ef4444;
      }
      .marketplace-btn:disabled {
        opacity: 0.5;
        cursor: wait;
      }
      .marketplace-empty {
        text-align: center;
        padding: 40px;
        color: var(--text-secondary);
      }
      .sidebar-marketplace-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        padding: 8px 12px;
        background: none;
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text-secondary);
        font-size: 13px;
        cursor: pointer;
        transition: all 0.2s;
        margin-top: 8px;
      }
      .sidebar-marketplace-btn:hover {
        background: var(--bg-hover);
        color: var(--text-primary);
        border-color: var(--accent);
      }
    `;
    document.head.appendChild(style);
  }

  // ── Fetch plugins ─────────────────────────────────────────────
  async function fetchPlugins() {
    try {
      const res = await fetch("/api/marketplace");
      const data = await res.json();
      return data.plugins || [];
    } catch {
      return [];
    }
  }

  // ── Install / Uninstall ───────────────────────────────────────
  async function installPlugin(pluginId, btn) {
    btn.disabled = true;
    btn.textContent = "Instalando...";
    try {
      const res = await fetch("/api/marketplace/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_id: pluginId }),
      });
      const data = await res.json();
      if (data.ok) {
        btn.textContent = "Instalado ✓";
        btn.className = "marketplace-btn uninstall";
        btn.textContent = "Remover";
        btn.disabled = false;
        btn.onclick = () => uninstallPlugin(pluginId, btn);
        if (typeof showToast === "function") showToast(data.message, "success");
      } else {
        btn.textContent = "Instalar";
        btn.disabled = false;
        if (typeof showToast === "function") showToast(data.error, "error");
      }
    } catch (err) {
      btn.textContent = "Instalar";
      btn.disabled = false;
      if (typeof showToast === "function") showToast("Erro ao instalar plugin", "error");
    }
  }

  async function uninstallPlugin(pluginId, btn) {
    btn.disabled = true;
    btn.textContent = "Removendo...";
    try {
      const res = await fetch("/api/marketplace/uninstall", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_id: pluginId }),
      });
      const data = await res.json();
      if (data.ok) {
        btn.className = "marketplace-btn install";
        btn.textContent = "Instalar";
        btn.disabled = false;
        btn.onclick = () => installPlugin(pluginId, btn);
        if (typeof showToast === "function") showToast(data.message, "success");
      } else {
        btn.textContent = "Remover";
        btn.disabled = false;
        if (typeof showToast === "function") showToast(data.error, "error");
      }
    } catch {
      btn.textContent = "Remover";
      btn.disabled = false;
    }
  }

  // ── Render ────────────────────────────────────────────────────
  function renderCard(plugin) {
    const cat = CATEGORIES[plugin.category] || { label: plugin.category, icon: "📦" };
    const card = document.createElement("div");
    card.className = "marketplace-card";
    card.dataset.name = (plugin.name + " " + plugin.description).toLowerCase();

    const btn = document.createElement("button");
    if (plugin.installed) {
      btn.className = "marketplace-btn uninstall";
      btn.textContent = "Remover";
      btn.onclick = () => uninstallPlugin(plugin.id, btn);
    } else {
      btn.className = "marketplace-btn install";
      btn.textContent = "Instalar";
      btn.onclick = () => installPlugin(plugin.id, btn);
    }

    card.innerHTML = `
      <div class="marketplace-card-header">
        <span class="marketplace-card-icon">${plugin.icon || "📦"}</span>
        <div class="marketplace-card-info">
          <h3>${plugin.name}</h3>
          <span class="version">v${plugin.version} · ${plugin.author}</span>
        </div>
      </div>
      <p>${plugin.description}</p>
      <div class="marketplace-card-footer">
        <span class="category-tag">${cat.icon} ${cat.label}</span>
      </div>
    `;
    card.querySelector(".marketplace-card-footer").appendChild(btn);
    return card;
  }

  async function openMarketplace() {
    const plugins = await fetchPlugins();

    // Create overlay
    const overlay = document.createElement("div");
    overlay.className = "marketplace-overlay";
    overlay.onclick = (e) => {
      if (e.target === overlay) overlay.remove();
    };

    const panel = document.createElement("div");
    panel.className = "marketplace-panel";
    panel.innerHTML = `
      <div class="marketplace-header">
        <h2>🏪 Plugin Marketplace</h2>
        <button class="marketplace-close" title="Fechar">✕</button>
      </div>
      <div class="marketplace-body">
        <input class="marketplace-search" placeholder="Buscar plugins..." type="text">
        <div class="marketplace-grid"></div>
      </div>
    `;

    const grid = panel.querySelector(".marketplace-grid");
    const search = panel.querySelector(".marketplace-search");
    const closeBtn = panel.querySelector(".marketplace-close");

    if (plugins.length === 0) {
      grid.innerHTML = '<div class="marketplace-empty">Nenhum plugin disponível</div>';
    } else {
      plugins.forEach((p) => grid.appendChild(renderCard(p)));
    }

    // Search filter
    search.addEventListener("input", () => {
      const q = search.value.toLowerCase();
      grid.querySelectorAll(".marketplace-card").forEach((card) => {
        card.style.display = card.dataset.name.includes(q) ? "" : "none";
      });
    });

    closeBtn.onclick = () => overlay.remove();

    // Escape to close
    const escHandler = (e) => {
      if (e.key === "Escape") {
        overlay.remove();
        document.removeEventListener("keydown", escHandler);
      }
    };
    document.addEventListener("keydown", escHandler);

    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    search.focus();
  }

  // ── Sidebar button ────────────────────────────────────────────
  function addSidebarButton() {
    const sidebar = document.querySelector(".sidebar-footer") || document.querySelector(".sidebar");
    if (!sidebar) return;

    const btn = document.createElement("button");
    btn.className = "sidebar-marketplace-btn";
    btn.innerHTML = "🏪 Marketplace";
    btn.onclick = openMarketplace;

    // Insert before the model selector if it exists
    const modelSection = sidebar.querySelector(".model-section");
    if (modelSection) {
      sidebar.insertBefore(btn, modelSection);
    } else {
      sidebar.appendChild(btn);
    }
  }

  // ── Global access ─────────────────────────────────────────────
  window.openMarketplace = openMarketplace;

  // ── Init ──────────────────────────────────────────────────────
  function init() {
    injectStyles();
    addSidebarButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
