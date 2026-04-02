"""Testes para o módulo de sandbox de segurança (denai.security.sandbox).

Valida que o sistema de sandboxing restringe corretamente o acesso
a caminhos no filesystem, protegendo arquivos sensíveis e prevenindo
ataques de path traversal.

is_path_allowed() retorna (bool, str) — (allowed, reason).
"""

from unittest.mock import patch

import pytest

from denai.security.sandbox import is_path_allowed


@pytest.fixture
def fake_home(tmp_path):
    """Cria um diretório home falso para os testes."""
    home = tmp_path / "fakehome"
    home.mkdir()
    return home


def _patch_home(fake_home):
    """Contexto que substitui o home do sistema pelo fake_home nos dois lugares."""
    home_str = str(fake_home)
    return patch("denai.security.sandbox.os.path.expanduser", side_effect=lambda p: home_str if p == "~" else p)


class TestIsPathAllowed:
    """Testes para a função is_path_allowed."""

    def test_allowed_path_within_home(self, fake_home):
        """Caminho dentro do home deve ser permitido."""
        target = fake_home / "projects" / "meu_projeto" / "main.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()

        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(str(target))
            assert allowed is True, f"Caminho dentro do home deveria ser permitido: {reason}"

    def test_blocked_etc_passwd(self, fake_home):
        """Acesso a /etc/passwd deve ser bloqueado."""
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed("/etc/passwd")
            assert allowed is False, "Acesso a /etc/passwd deveria ser bloqueado"

    def test_blocked_tmp_directory(self, fake_home):
        """Acesso a /tmp/algo_aleatorio deve ser bloqueado."""
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed("/tmp/something_random")
            assert allowed is False

    def test_blocked_ssh_directory(self, fake_home):
        """Acesso ao diretório .ssh deve ser bloqueado."""
        ssh_dir = fake_home / ".ssh" / "id_rsa"
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(str(ssh_dir))
            assert allowed is False, f".ssh deveria ser bloqueado: {reason}"

    def test_blocked_aws_credentials(self, fake_home):
        """Acesso ao diretório .aws deve ser bloqueado."""
        aws_path = fake_home / ".aws" / "credentials"
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(str(aws_path))
            assert allowed is False

    def test_blocked_gnupg_directory(self, fake_home):
        """Acesso ao diretório .gnupg deve ser bloqueado."""
        gnupg_path = fake_home / ".gnupg" / "secring.gpg"
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(str(gnupg_path))
            assert allowed is False

    def test_blocked_denai_api_key(self, fake_home):
        """Acesso ao arquivo de API key do DenAI deve ser bloqueado."""
        api_key_path = fake_home / ".denai" / "api.key"
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(str(api_key_path))
            assert allowed is False

    def test_blocked_path_traversal_etc(self, fake_home):
        """Tentativa de path traversal para /etc/passwd deve ser bloqueada."""
        traversal = str(fake_home / "projects" / ".." / ".." / ".." / "etc" / "passwd")
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(traversal)
            assert allowed is False

    def test_blocked_path_traversal_double_dot(self, fake_home):
        """Path traversal com ../../ deve ser bloqueado."""
        traversal = str(fake_home / ".." / ".." / "etc" / "shadow")
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(traversal)
            assert allowed is False

    def test_home_dir_itself_allowed(self, fake_home):
        """O diretório home em si deve ser permitido."""
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(str(fake_home))
            assert allowed is True

    def test_creating_paths_inside_home(self, fake_home):
        """Caminhos novos dentro do home devem ser permitidos (mesmo não existindo ainda)."""
        new_path = fake_home / "novo_projeto" / "src" / "app.py"
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed(str(new_path))
            assert allowed is True

    def test_blocked_root_path(self, fake_home):
        """Acesso direto à raiz deve ser bloqueado."""
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed("/")
            assert allowed is False

    def test_blocked_var_log(self, fake_home):
        """Acesso a /var/log deve ser bloqueado."""
        with _patch_home(fake_home):
            allowed, reason = is_path_allowed("/var/log/syslog")
            assert allowed is False
