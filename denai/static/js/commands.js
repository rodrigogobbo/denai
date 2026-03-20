/**
 * Custom Commands — slash command autocomplete.
 * Type '/' in the message input to see available commands.
 */
(function () {
  "use strict";

  let commands = [];
  let popup = null;
  let selectedIndex = 0;

  // ── Fetch commands ─────────────────────────────────────────────
  async function loadCommands() {
    try {
      const res = await fetch("/api/commands");
      const data = await res.json();
      commands = data.commands || [];
    } catch {
      commands = [];
    }
  }

  // ── Inject styles ─────────────────────────────────────────────
  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      .cmd-popup {
        position: absolute;
        bottom: 100%;
        left: 0;
        right: 0;
        background: var(--bg-primary);
        border: 1px solid var(--border);
        border-radius: 10px;
        margin-bottom: 8px;
        max-height: 200px;
        overflow-y: auto;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.2);
        z-index: 100;
      }
      .cmd-item {
        padding: 10px 14px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
        border-bottom: 1px solid var(--border);
        transition: background 0.15s;
      }
      .cmd-item:last-child { border-bottom: none; }
      .cmd-item:hover, .cmd-item.selected {
        background: var(--bg-hover);
      }
      .cmd-item-name {
        font-weight: 600;
        font-size: 14px;
        color: var(--accent);
      }
      .cmd-item-desc {
        font-size: 12px;
        color: var(--text-secondary);
      }
    `;
    document.head.appendChild(style);
  }

  // ── Create/destroy popup ──────────────────────────────────────
  function showPopup(filtered) {
    hidePopup();
    if (filtered.length === 0) return;

    popup = document.createElement("div");
    popup.className = "cmd-popup";

    filtered.forEach((cmd, i) => {
      const item = document.createElement("div");
      item.className = "cmd-item" + (i === selectedIndex ? " selected" : "");
      item.innerHTML = `
        <span class="cmd-item-name">/${cmd.name}</span>
        <span class="cmd-item-desc">${cmd.description || ""}</span>
      `;
      item.addEventListener("click", () => selectCommand(cmd));
      popup.appendChild(item);
    });

    const inputArea = document.querySelector(".input-area");
    if (inputArea) {
      inputArea.style.position = "relative";
      inputArea.appendChild(popup);
    }
  }

  function hidePopup() {
    if (popup) {
      popup.remove();
      popup = null;
    }
    selectedIndex = 0;
  }

  function selectCommand(cmd) {
    const input = document.getElementById("messageInput");
    if (!input) return;
    input.value = "/" + cmd.name + " ";
    input.focus();
    hidePopup();
  }

  // ── Input handler ─────────────────────────────────────────────
  function handleInput(e) {
    const input = e.target;
    const value = input.value;

    // Only show popup when typing starts with /
    if (!value.startsWith("/")) {
      hidePopup();
      return;
    }

    // Extract the command name being typed (everything after / until first space)
    const afterSlash = value.slice(1);
    const spaceIdx = afterSlash.indexOf(" ");
    const typing = spaceIdx === -1 ? afterSlash : afterSlash.slice(0, spaceIdx);

    // If there's already a space, user is typing arguments — hide popup
    if (spaceIdx !== -1) {
      hidePopup();
      return;
    }

    // Filter commands
    const filtered = commands.filter((c) =>
      c.name.toLowerCase().startsWith(typing.toLowerCase())
    );
    selectedIndex = Math.min(selectedIndex, Math.max(0, filtered.length - 1));
    showPopup(filtered);
  }

  function handleKeydown(e) {
    if (!popup) return;

    const items = popup.querySelectorAll(".cmd-item");
    if (items.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = (selectedIndex + 1) % items.length;
      updateSelection(items);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex = (selectedIndex - 1 + items.length) % items.length;
      updateSelection(items);
    } else if (e.key === "Tab" || e.key === "Enter") {
      if (popup) {
        e.preventDefault();
        const filtered = commands.filter((c) => {
          const value = document.getElementById("messageInput")?.value || "";
          const typing = value.slice(1);
          return c.name.toLowerCase().startsWith(typing.toLowerCase());
        });
        if (filtered[selectedIndex]) {
          selectCommand(filtered[selectedIndex]);
        }
      }
    } else if (e.key === "Escape") {
      hidePopup();
    }
  }

  function updateSelection(items) {
    items.forEach((item, i) => {
      item.classList.toggle("selected", i === selectedIndex);
    });
  }

  // ── Intercept send to resolve commands ────────────────────────
  // We need to intercept the message before it's sent. We'll hook into
  // the send flow by checking if the message starts with / and resolving
  // the command first.
  window.resolveCommand = async function (message) {
    if (!message.startsWith("/")) return null;

    const parts = message.slice(1).split(" ");
    const cmdName = parts[0];
    const args = parts.slice(1).join(" ");

    try {
      const res = await fetch("/api/commands/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: cmdName, arguments: args }),
      });
      const data = await res.json();
      if (data.ok) {
        return { prompt: data.prompt, model: data.model };
      }
    } catch {
      // Not a valid command, send as-is
    }
    return null;
  };

  // ── Init ──────────────────────────────────────────────────────
  function init() {
    injectStyles();
    loadCommands();

    const input = document.getElementById("messageInput");
    if (input) {
      input.addEventListener("input", handleInput);
      input.addEventListener("keydown", handleKeydown);
    }

    // Reload commands periodically (in case user adds new ones)
    setInterval(loadCommands, 30000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
