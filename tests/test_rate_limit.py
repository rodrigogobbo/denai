"""Testes para o rate limiter (denai.security.rate_limit).

Valida que o sistema de rate limiting controla corretamente o número
de requisições por IP dentro de uma janela de tempo, evitando abuso
da API.
"""

import time
from unittest.mock import patch

from denai.security.rate_limit import RateLimiter


class TestRateLimiterBasic:
    """Testes básicos do rate limiter."""

    def test_allows_requests_under_limit(self):
        """Requisições dentro do limite devem ser permitidas."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        ip = "192.168.1.1"

        for i in range(5):
            assert limiter.is_allowed(ip) is True, (
                f"Requisição {i + 1} deveria ser permitida (limite: 5)"
            )

    def test_blocks_after_exceeding_limit(self):
        """Requisições acima do limite devem ser bloqueadas."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        ip = "10.0.0.1"

        # Usa as 3 permitidas
        for _ in range(3):
            assert limiter.is_allowed(ip) is True

        # A 4ª deve ser bloqueada
        assert limiter.is_allowed(ip) is False
        # A 5ª também
        assert limiter.is_allowed(ip) is False

    def test_single_request_allowed(self):
        """Uma única requisição deve sempre ser permitida."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("1.1.1.1") is True

    def test_single_request_second_blocked(self):
        """Com limite 1, a segunda requisição deve ser bloqueada."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        ip = "1.1.1.1"
        limiter.is_allowed(ip)
        assert limiter.is_allowed(ip) is False


class TestRateLimiterIsolation:
    """Testes de isolamento entre IPs diferentes."""

    def test_different_ips_independent_limits(self):
        """IPs diferentes devem ter contadores independentes."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        ip_a = "192.168.1.1"
        ip_b = "192.168.1.2"

        # IP A usa as 2 requisições
        assert limiter.is_allowed(ip_a) is True
        assert limiter.is_allowed(ip_a) is True
        assert limiter.is_allowed(ip_a) is False  # bloqueado

        # IP B ainda tem suas próprias requisições
        assert limiter.is_allowed(ip_b) is True
        assert limiter.is_allowed(ip_b) is True
        assert limiter.is_allowed(ip_b) is False  # agora bloqueado

    def test_many_ips_independent(self):
        """Múltiplos IPs devem funcionar independentemente."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        for i in range(100):
            ip = f"10.0.0.{i}"
            assert limiter.is_allowed(ip) is True, (
                f"Primeiro request do IP {ip} deveria ser permitido"
            )


class TestRateLimiterWindowExpiry:
    """Testes de expiração da janela de tempo."""

    def test_window_expiry_allows_new_requests(self):
        """Após a janela expirar, novas requisições devem ser permitidas."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        ip = "172.16.0.1"

        # Usa as 2 permitidas
        assert limiter.is_allowed(ip) is True
        assert limiter.is_allowed(ip) is True
        assert limiter.is_allowed(ip) is False

        # Espera a janela expirar
        time.sleep(1.1)

        # Agora deve ser permitido novamente
        assert limiter.is_allowed(ip) is True

    def test_window_expiry_with_mock_time(self):
        """Expiração da janela usando mock de tempo (sem sleep real)."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        ip = "10.10.10.10"

        base_time = 1000000.0

        with patch("denai.security.rate_limit.time.time", return_value=base_time):
            for _ in range(3):
                limiter.is_allowed(ip)
            assert limiter.is_allowed(ip) is False

        # Avança 61 segundos
        with patch(
            "denai.security.rate_limit.time.time", return_value=base_time + 61
        ):
            assert limiter.is_allowed(ip) is True


class TestRateLimiterReset:
    """Testes do método reset."""

    def test_reset_clears_specific_ip(self):
        """Reset de um IP específico deve liberar suas requisições."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        ip = "192.168.0.100"

        assert limiter.is_allowed(ip) is True
        assert limiter.is_allowed(ip) is False

        limiter.reset(ip)

        assert limiter.is_allowed(ip) is True

    def test_reset_does_not_affect_other_ips(self):
        """Reset de um IP não deve afetar outros IPs."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        ip_a = "10.0.0.1"
        ip_b = "10.0.0.2"

        limiter.is_allowed(ip_a)
        limiter.is_allowed(ip_b)

        # Ambos bloqueados
        assert limiter.is_allowed(ip_a) is False
        assert limiter.is_allowed(ip_b) is False

        # Reset só do IP A
        limiter.reset(ip_a)

        assert limiter.is_allowed(ip_a) is True  # liberado
        assert limiter.is_allowed(ip_b) is False  # ainda bloqueado

    def test_reset_all(self):
        """Reset geral deve limpar todos os contadores."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        for i in range(5):
            ip = f"10.0.0.{i}"
            limiter.is_allowed(ip)
            assert limiter.is_allowed(ip) is False

        limiter.reset()  # reset global

        for i in range(5):
            ip = f"10.0.0.{i}"
            assert limiter.is_allowed(ip) is True
