/**
 * Modes — Build vs Plan toggle.
 * Build = full agent with all tools.
 * Plan = read-only analysis mode.
 */
(function () {
  "use strict";

  // Current mode (persisted in sessionStorage)
  let currentMode = sessionStorage.getItem("denai-mode") || "build";

  // ── Inject styles ─────────────────────────────────────────────
  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      .mode-indicator {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        user-select: none;
        border: 1px solid transparent;
      }
      .mode-indicator.build {
        background: rgba(34, 197, 94, 0.1);
        color: #22c55e;
        border-color: rgba(34, 197, 94, 0.2);
      }
      .mode-indicator.plan {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
        border-color: rgba(59, 130, 246, 0.2);
      }
      .mode-indicator:hover {
        filter: brightness(1.2);
      }
      .mode-indicator .mode-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
      }
      .mode-hint {
        position: absolute;
        bottom: calc(100% + 4px);
        right: 0;
        background: var(--bg-primary);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 11px;
        color: var(--text-secondary);
        white-space: nowrap;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s;
        z-index: 50;
      }
      .mode-indicator:hover .mode-hint {
        opacity: 1;
      }
    `;
    document.head.appendChild(style);
  }

  // ── Create indicator ──────────────────────────────────────────
  function createIndicator() {
    const indicator = document.createElement("div");
    indicator.className = `mode-indicator ${currentMode}`;
    indicator.id = "modeIndicator";
    indicator.innerHTML = `
      <span class="mode-dot"></span>
      <span class="mode-label">${currentMode === "build" ? "Build" : "Plan"}</span>
      <span class="mode-hint">Tab para alternar modo</span>
    `;
    indicator.addEventListener("click", toggleMode);
    return indicator;
  }

  function updateIndicator() {
    const indicator = document.getElementById("modeIndicator");
    if (!indicator) return;
    indicator.className = `mode-indicator ${currentMode}`;
    indicator.querySelector(".mode-label").textContent =
      currentMode === "build" ? "Build" : "Plan";
  }

  // ── Toggle mode ───────────────────────────────────────────────
  function toggleMode() {
    currentMode = currentMode === "build" ? "plan" : "build";
    sessionStorage.setItem("denai-mode", currentMode);
    updateIndicator();

    // Show toast
    if (typeof showToast === "function") {
      const emoji = currentMode === "build" ? "🔨" : "📋";
      const label = currentMode === "build" ? "Build" : "Plan";
      showToast(`${emoji} Modo ${label} ativado`, "info");
    }
  }

  // ── Expose to other scripts ───────────────────────────────────
  window.getCurrentMode = function () {
    return currentMode;
  };

  window.toggleMode = toggleMode;

  // ── Tab key handler ───────────────────────────────────────────
  function handleTab(e) {
    // Only toggle on Tab when message input is focused and empty
    const input = document.getElementById("messageInput");
    if (document.activeElement === input && !input.value.trim()) {
      e.preventDefault();
      toggleMode();
    }
  }

  // ── Init ──────────────────────────────────────────────────────
  function init() {
    injectStyles();

    // Add indicator next to the send button area
    const inputActions = document.querySelector(".input-actions");
    const inputArea = document.querySelector(".input-area");
    const target = inputActions || inputArea;

    if (target) {
      const indicator = createIndicator();
      // Insert at the start of input actions area
      if (inputActions) {
        inputActions.prepend(indicator);
      } else {
        target.appendChild(indicator);
      }
    }

    document.addEventListener("keydown", handleTab);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
