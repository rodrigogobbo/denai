/**
 * Voice Input — gravação de áudio e transcrição via Whisper.
 * Se Whisper não estiver instalado, o botão de mic fica oculto.
 */
(function () {
  "use strict";

  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let micBtn = null;

  // ── Check availability ──────────────────────────────────────────
  async function checkVoiceAvailable() {
    try {
      const res = await fetch("/api/voice/status");
      const data = await res.json();
      return data.available === true;
    } catch {
      return false;
    }
  }

  // ── Create mic button ───────────────────────────────────────────
  function createMicButton() {
    const btn = document.createElement("button");
    btn.className = "mic-btn";
    btn.id = "btnMic";
    btn.title = "Gravar áudio (Whisper)";
    btn.type = "button";
    btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="22"/>
    </svg>`;
    return btn;
  }

  // ── Inject CSS ──────────────────────────────────────────────────
  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      .mic-btn {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 1px solid var(--border);
        background: var(--bg-secondary);
        color: var(--text-secondary);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
        flex-shrink: 0;
      }
      .mic-btn:hover {
        background: var(--bg-hover);
        color: var(--text-primary);
      }
      .mic-btn.recording {
        background: #ef4444;
        border-color: #ef4444;
        color: #fff;
        animation: mic-pulse 1.5s ease-in-out infinite;
      }
      @keyframes mic-pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        50% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
      }
      .mic-btn.transcribing {
        opacity: 0.6;
        cursor: wait;
      }
    `;
    document.head.appendChild(style);
  }

  // ── Recording logic ─────────────────────────────────────────────
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunks, { type: "audio/webm" });
        await sendForTranscription(blob);
      };

      mediaRecorder.start();
      isRecording = true;
      micBtn.classList.add("recording");
      micBtn.title = "Parar gravação";
    } catch (err) {
      console.error("Erro ao acessar microfone:", err);
      if (typeof showToast === "function") {
        showToast("Erro ao acessar microfone. Verifique as permissões.", "error");
      }
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    isRecording = false;
    micBtn.classList.remove("recording");
    micBtn.title = "Gravar áudio (Whisper)";
  }

  function toggleRecording() {
    if (micBtn.classList.contains("transcribing")) return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  // ── Send audio for transcription ───────────────────────────────
  async function sendForTranscription(blob) {
    micBtn.classList.add("transcribing");
    micBtn.title = "Transcrevendo...";

    try {
      const form = new FormData();
      form.append("audio", blob, "recording.webm");

      const res = await fetch("/api/voice/transcribe", {
        method: "POST",
        body: form,
      });
      const data = await res.json();

      if (data.error) {
        if (typeof showToast === "function") {
          showToast(data.error, "error");
        }
        return;
      }

      if (data.text) {
        const input = document.getElementById("messageInput");
        if (input) {
          input.value = (input.value ? input.value + " " : "") + data.text;
          input.focus();
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }
      }
    } catch (err) {
      console.error("Erro na transcrição:", err);
      if (typeof showToast === "function") {
        showToast("Erro ao transcrever áudio", "error");
      }
    } finally {
      micBtn.classList.remove("transcribing");
      micBtn.title = "Gravar áudio (Whisper)";
    }
  }

  // ── Init ────────────────────────────────────────────────────────
  async function init() {
    const available = await checkVoiceAvailable();
    if (!available) return;

    injectStyles();
    micBtn = createMicButton();

    // Insert before send button
    const sendBtn = document.getElementById("btnSend");
    if (sendBtn && sendBtn.parentElement) {
      sendBtn.parentElement.insertBefore(micBtn, sendBtn);
    }

    micBtn.addEventListener("click", toggleRecording);

    // Keyboard shortcut: Ctrl+Shift+M to toggle recording
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === "M") {
        e.preventDefault();
        toggleRecording();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
