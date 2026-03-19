"""Testes para o módulo de context management (denai.llm.context)."""

from __future__ import annotations


class TestEstimateTokens:
    """Testes para estimate_tokens."""

    def test_empty_string(self):
        from denai.llm.context import estimate_tokens

        assert estimate_tokens("") == 1  # Mínimo 1

    def test_short_string(self):
        from denai.llm.context import estimate_tokens

        result = estimate_tokens("hello world")
        assert result > 0
        assert result < 20

    def test_long_string(self):
        from denai.llm.context import estimate_tokens

        text = "a" * 3000
        result = estimate_tokens(text)
        assert result == 1000  # 3000 / 3


class TestPickContextSize:
    """Testes para pick_context_size."""

    def test_small_conversation(self):
        from denai.llm.context import pick_context_size

        msgs = [{"role": "user", "content": "Oi"}]
        assert pick_context_size(msgs) == 8192

    def test_medium_conversation(self):
        from denai.llm.context import pick_context_size

        # ~5000 tokens → 15000 chars
        msgs = [{"role": "user", "content": "x" * 15000}]
        assert pick_context_size(msgs) == 16384

    def test_large_conversation(self):
        from denai.llm.context import pick_context_size

        # ~15000 tokens → 45000 chars
        msgs = [{"role": "user", "content": "x" * 45000}]
        assert pick_context_size(msgs) == 32768

    def test_very_large_conversation(self):
        from denai.llm.context import pick_context_size

        # ~25000 tokens → 75000 chars
        msgs = [{"role": "user", "content": "x" * 75000}]
        assert pick_context_size(msgs) == 65536

    def test_respects_max_context(self):
        from denai.llm.context import pick_context_size

        msgs = [{"role": "user", "content": "x" * 75000}]
        assert pick_context_size(msgs, max_context=16384) == 16384


class TestSummarizeOldMessages:
    """Testes para summarize_old_messages."""

    def test_short_history_unchanged(self):
        from denai.llm.context import summarize_old_messages

        msgs = [
            {"role": "system", "content": "Sou DenAI"},
            {"role": "user", "content": "Oi"},
            {"role": "assistant", "content": "Olá!"},
        ]
        result = summarize_old_messages(msgs, keep_recent=5)
        assert result == msgs  # Não muda nada

    def test_long_history_compressed(self):
        from denai.llm.context import summarize_old_messages

        msgs = [{"role": "system", "content": "Sou DenAI"}]
        for i in range(20):
            msgs.append({"role": "user", "content": f"Pergunta {i}"})
            msgs.append({"role": "assistant", "content": f"Resposta {i}"})

        result = summarize_old_messages(msgs, keep_recent=6)

        # Deve ter: system + resumo + 6 recentes = 8
        assert len(result) == 8
        # System prompt preservado
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "Sou DenAI"
        # Resumo inserido
        assert "Resumo do histórico" in result[1]["content"]
        # Últimas mensagens intactas
        assert "Pergunta 19" in result[-2]["content"]
        assert "Resposta 19" in result[-1]["content"]

    def test_tool_messages_summarized(self):
        from denai.llm.context import summarize_old_messages

        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "leia o arquivo"},
            {"role": "tool", "content": "✅ Conteúdo do arquivo:\nlinha1\nlinha2\nlinha3"},
            {"role": "assistant", "content": "Aqui está o conteúdo"},
        ]
        # Adicionar msgs recentes suficientes
        for i in range(15):
            msgs.append({"role": "user", "content": f"msg {i}"})
            msgs.append({"role": "assistant", "content": f"resp {i}"})

        result = summarize_old_messages(msgs, keep_recent=10)

        # Tool result deve estar resumido (só primeira linha)
        summary = result[1]["content"]
        assert "[tool]" in summary
        assert "linha2" not in summary  # Não inclui linhas extras

    def test_preserves_recent_count(self):
        from denai.llm.context import summarize_old_messages

        msgs = [{"role": "system", "content": "sys"}]
        for i in range(30):
            msgs.append({"role": "user", "content": f"Q{i}"})

        result = summarize_old_messages(msgs, keep_recent=5)

        # system + resumo + 5 recentes = 7
        assert len(result) == 7
        # Últimas 5 preservadas
        assert result[-1]["content"] == "Q29"
        assert result[-5]["content"] == "Q25"
