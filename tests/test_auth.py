"""Testes para o módulo de autenticação (denai.security.auth).

Valida a criação, leitura e verificação de API keys usadas para
autenticar requisições ao DenAI.
"""

from unittest.mock import patch

from denai.security.auth import get_or_create_api_key, verify_api_key


class TestGetOrCreateApiKey:
    """Testes para criação e leitura de API keys."""

    def test_creates_key_file_when_missing(self, tmp_path):
        """Deve criar o arquivo de API key quando ele não existe."""
        key_file = tmp_path / ".denai" / "api.key"
        key_file.parent.mkdir(parents=True, exist_ok=True)

        with patch("denai.security.auth.API_KEY_PATH", key_file):
            key = get_or_create_api_key()

        assert key_file.exists(), "Arquivo de API key deveria ter sido criado"
        assert len(key) > 0, "API key não pode ser vazia"
        assert key == key_file.read_text().strip()

    def test_creates_parent_directory(self, tmp_path):
        """Deve criar o diretório pai (.denai/) se não existir."""
        denai_dir = tmp_path / ".denai"
        key_file = denai_dir / "api.key"
        denai_dir.mkdir(parents=True, exist_ok=True)

        assert denai_dir.exists()

        with patch("denai.security.auth.API_KEY_PATH", key_file):
            get_or_create_api_key()

        assert key_file.exists(), "Arquivo api.key deveria ter sido criado"

    def test_reads_existing_key(self, tmp_path):
        """Deve ler a key existente sem criar uma nova."""
        key_file = tmp_path / ".denai" / "api.key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        existing_key = "my-super-secret-key-that-is-at-least-32-chars-long!"
        key_file.write_text(existing_key)

        with patch("denai.security.auth.API_KEY_PATH", key_file):
            key = get_or_create_api_key()

        assert key == existing_key, "Deveria retornar a key existente"

    def test_reads_existing_key_strips_whitespace(self, tmp_path):
        """Deve fazer strip de whitespace da key existente."""
        key_file = tmp_path / ".denai" / "api.key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        raw_key = "my-key-with-spaces-that-is-at-least-32-chars!!"
        key_file.write_text(f"  {raw_key}  \n")

        with patch("denai.security.auth.API_KEY_PATH", key_file):
            key = get_or_create_api_key()

        assert key == raw_key, "Deveria fazer strip do whitespace"

    def test_generated_key_is_unique(self, tmp_path):
        """Cada key gerada deve ser única."""
        keys = []
        for i in range(5):
            key_file = tmp_path / f".denai_{i}" / "api.key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            with patch("denai.security.auth.API_KEY_PATH", key_file):
                keys.append(get_or_create_api_key())

        assert len(set(keys)) == 5, "Todas as keys geradas deveriam ser únicas"

    def test_generated_key_has_reasonable_length(self, tmp_path):
        """A key gerada deve ter tamanho razoável (mín. 32 chars)."""
        key_file = tmp_path / ".denai" / "api.key"
        key_file.parent.mkdir(parents=True, exist_ok=True)

        with patch("denai.security.auth.API_KEY_PATH", key_file):
            key = get_or_create_api_key()

        assert len(key) >= 32, (
            f"API key muito curta: {len(key)} chars (mínimo: 32)"
        )


class TestVerifyApiKey:
    """Testes para verificação de API keys."""

    def test_correct_key_accepted(self):
        """Key correta deve ser aceita."""
        real_key = "correct-api-key-abc123-long-enough"

        with patch("denai.security.auth.API_KEY", real_key):
            assert verify_api_key(real_key) is True

    def test_wrong_key_rejected(self):
        """Key incorreta deve ser rejeitada."""
        with patch("denai.security.auth.API_KEY", "correct-api-key-abc123"):
            assert verify_api_key("wrong-key-xyz789") is False

    def test_none_key_rejected(self):
        """Key None deve ser rejeitada."""
        with patch("denai.security.auth.API_KEY", "any-valid-key"):
            assert verify_api_key(None) is False

    def test_empty_string_rejected(self):
        """Key vazia deve ser rejeitada."""
        with patch("denai.security.auth.API_KEY", "any-valid-key"):
            assert verify_api_key("") is False

    def test_whitespace_only_rejected(self):
        """Key com apenas espaços deve ser rejeitada."""
        with patch("denai.security.auth.API_KEY", "any-valid-key"):
            assert verify_api_key("   ") is False

    def test_key_comparison_is_exact(self):
        """Comparação de key deve ser exata (sem substring match)."""
        real_key = "my-api-key"

        with patch("denai.security.auth.API_KEY", real_key):
            assert verify_api_key("my-api-key-extra") is False
            assert verify_api_key("my-api") is False
            assert verify_api_key("MY-API-KEY") is False  # case matters
