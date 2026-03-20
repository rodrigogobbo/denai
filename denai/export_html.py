"""Export conversation as standalone HTML file."""

from __future__ import annotations

import html
import re
from datetime import datetime


def conversation_to_html(conv: dict, messages: list[dict]) -> str:
    """Generate a beautiful standalone HTML file from a conversation."""
    title = html.escape(conv.get("title", "Conversa DenAI"))
    model = html.escape(conv.get("model", ""))
    created = conv.get("created_at", "")
    created_fmt = _fmt_date(created)
    msg_count = len(messages)

    messages_html = "\n".join(_render_message(m) for m in messages if m.get("content"))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — DenAI</title>
<style>
:root {{
  --bg: #0d1117;
  --bg-card: #161b22;
  --bg-user: #1a3a2a;
  --border: #30363d;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --accent: #58a6ff;
  --accent-green: #3fb950;
  --accent-orange: #d29922;
  --code-bg: #0d1117;
  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  --font-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}
.container {{
  max-width: 820px;
  margin: 0 auto;
  padding: 20px;
}}
header {{
  text-align: center;
  padding: 40px 20px 30px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 30px;
}}
header h1 {{
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 8px;
}}
header .meta {{
  color: var(--text-muted);
  font-size: 0.85rem;
}}
header .meta span {{
  margin: 0 8px;
}}
.message {{
  margin-bottom: 24px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}}
.message.user {{
  flex-direction: row-reverse;
}}
.avatar {{
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: var(--bg-card);
  border: 1px solid var(--border);
}}
.bubble {{
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  font-size: 0.95rem;
  overflow-wrap: break-word;
}}
.message.user .bubble {{
  background: var(--bg-user);
  border-color: #2a5a3a;
  border-radius: 12px 12px 4px 12px;
}}
.message.assistant .bubble {{
  border-radius: 12px 12px 12px 4px;
}}
.bubble p {{ margin-bottom: 0.6em; }}
.bubble p:last-child {{ margin-bottom: 0; }}
.bubble h1, .bubble h2, .bubble h3, .bubble h4 {{
  margin: 1em 0 0.4em;
  font-weight: 600;
}}
.bubble h1 {{ font-size: 1.3em; }}
.bubble h2 {{ font-size: 1.15em; }}
.bubble h3 {{ font-size: 1.05em; }}
.bubble ul, .bubble ol {{
  padding-left: 1.5em;
  margin-bottom: 0.6em;
}}
.bubble li {{ margin-bottom: 0.3em; }}
.bubble strong {{ font-weight: 600; }}
.bubble em {{ font-style: italic; color: var(--text-muted); }}
.bubble a {{ color: var(--accent); text-decoration: none; }}
.bubble a:hover {{ text-decoration: underline; }}
.bubble blockquote {{
  border-left: 3px solid var(--accent);
  padding-left: 12px;
  margin: 0.6em 0;
  color: var(--text-muted);
}}
pre {{
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  overflow-x: auto;
  margin: 0.6em 0;
  font-family: var(--font-mono);
  font-size: 0.85em;
  line-height: 1.5;
  position: relative;
}}
code {{
  font-family: var(--font-mono);
  font-size: 0.88em;
}}
:not(pre) > code {{
  background: rgba(110,118,129,0.2);
  padding: 2px 6px;
  border-radius: 4px;
}}
.tool-card {{
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin: 8px 0;
  overflow: hidden;
}}
.tool-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--accent-orange);
}}
.tool-header:hover {{ background: rgba(255,255,255,0.03); }}
.tool-header .arrow {{ transition: transform 0.2s; }}
.tool-header .arrow.open {{ transform: rotate(90deg); }}
.tool-body {{
  display: none;
  padding: 8px 12px;
  border-top: 1px solid var(--border);
  font-size: 0.8rem;
}}
.tool-body.open {{ display: block; }}
.tool-body pre {{
  margin: 4px 0;
  font-size: 0.8em;
  max-height: 300px;
  overflow-y: auto;
}}
.label {{
  font-weight: 600; color: var(--text-muted);
  font-size: 0.75rem; text-transform: uppercase;
  margin-bottom: 2px;
}}
.time {{
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-top: 4px;
}}
footer {{
  text-align: center;
  padding: 30px 20px;
  margin-top: 30px;
  border-top: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 0.8rem;
}}
footer a {{ color: var(--accent); text-decoration: none; }}
@media (max-width: 600px) {{
  .bubble {{ max-width: 90%; }}
  .container {{ padding: 12px; }}
  header h1 {{ font-size: 1.2rem; }}
}}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🐺 {title}</h1>
    <div class="meta">
      {f"<span>📅 {created_fmt}</span>" if created_fmt else ""}
      {f"<span>🤖 {model}</span>" if model else ""}
      <span>💬 {msg_count} mensagens</span>
    </div>
  </header>

  <div class="messages">
    {messages_html}
  </div>

  <footer>
    Exportado por <a href="https://github.com/rodrigogobbo/denai">DenAI</a> 🐺
    em {datetime.now().strftime("%d/%m/%Y %H:%M")}
  </footer>
</div>

<script>
function toggleTool(el) {{
  const body = el.nextElementSibling;
  const arrow = el.querySelector('.arrow');
  body.classList.toggle('open');
  arrow.classList.toggle('open');
}}
</script>
</body>
</html>"""


def _render_message(msg: dict) -> str:
    """Render a single message as HTML."""
    role = msg.get("role", "unknown")
    content = msg.get("content", "")
    created = msg.get("created_at", "")
    time_str = _fmt_time(created)

    if role == "user":
        return f"""<div class="message user">
  <div class="avatar">👤</div>
  <div class="bubble">
    {_render_content(content)}
    <div class="time">{time_str}</div>
  </div>
</div>"""

    if role == "assistant":
        return f"""<div class="message assistant">
  <div class="avatar">🐺</div>
  <div class="bubble">
    {_render_content(content)}
    <div class="time">{time_str}</div>
  </div>
</div>"""

    if role == "tool":
        # Tool results are usually JSON or text
        tool_name = _extract_tool_name(content)
        escaped = html.escape(content[:3000])
        return f"""<div class="message assistant">
  <div class="avatar">🔧</div>
  <div class="bubble">
    <div class="tool-card">
      <div class="tool-header" onclick="toggleTool(this)">
        <span class="arrow">▶</span>
        🔧 {html.escape(tool_name)}
      </div>
      <div class="tool-body">
        <pre>{escaped}</pre>
      </div>
    </div>
    <div class="time">{time_str}</div>
  </div>
</div>"""

    # system or unknown
    return ""


def _render_content(text: str) -> str:
    """Simple markdown-to-HTML conversion (no external deps)."""
    if not text:
        return ""

    # Escape HTML first
    text = html.escape(text)

    # Code blocks (```...```)
    def _code_block(m):
        lang = m.group(1) or ""  # noqa: F841
        code = m.group(2)
        # Unescape inside code blocks (was double-escaped)
        return f"<pre><code>{code}</code></pre>"

    text = re.sub(r"```(\w*)\n(.*?)```", _code_block, text, flags=re.DOTALL)

    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    # Headers
    text = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", text, flags=re.MULTILINE)
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)

    # Blockquotes
    text = re.sub(r"^&gt; (.+)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)

    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', text)

    # Unordered lists
    text = re.sub(r"^- (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
    text = re.sub(r"(<li>.*?</li>\n?)+", r"<ul>\g<0></ul>", text)

    # Paragraphs (double newline)
    text = re.sub(r"\n{2,}", "</p><p>", text)

    # Single newlines to <br> (but not inside tags)
    text = re.sub(r"(?<!</p>)\n(?!<)", "<br>", text)

    # Wrap in paragraph if not starting with block element
    if not text.startswith(("<h", "<ul", "<pre", "<blockquote")):
        text = f"<p>{text}</p>"

    # Clean up empty paragraphs
    text = text.replace("<p></p>", "")

    return text


def _extract_tool_name(content: str) -> str:
    """Try to extract tool name from tool message content."""
    # Tool messages often start with the tool name or have it in a structured format
    if content.startswith("{"):
        try:
            import json

            data = json.loads(content)
            return data.get("name", data.get("tool", "Tool"))
        except Exception:
            pass
    # Fallback: first line or first word
    first_line = content.split("\n")[0][:50]
    return first_line if first_line else "Tool"


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%H:%M")
    except Exception:
        return ""


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ""
