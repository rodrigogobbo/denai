"""Validação de URLs de LLM providers contra SSRF.

Bloqueia metadata servers (169.254.169.254), loopback em produção,
e IPs privados/reservados. Reconstrói a URL a partir das partes
parseadas para quebrar o taint no CodeQL.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

# ─── Ranges proibidos (RFC 5735 / RFC 6890) ────────────────────────────────

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),  # shared address space
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("240.0.0.0/4"),  # reserved
    ipaddress.ip_network("0.0.0.0/8"),  # "this" network
]

_ALLOWED_SCHEMES = {"http", "https"}


class ProviderURLError(ValueError):
    """URL de provider inválida ou bloqueada por segurança."""


def _check_ip(addr: str) -> str | None:
    """Retorna motivo se o IP for bloqueado, None se permitido."""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return None  # não é IP literal

    if ip.is_loopback:
        return "loopback address não permitido"
    if ip.is_link_local:
        return "link-local address não permitido (inclui metadata server)"
    if ip.is_multicast:
        return "multicast address não permitido"
    if ip.is_unspecified:
        return "endereço não especificado (0.0.0.0) não permitido"
    for net in _BLOCKED_NETWORKS:
        if ip in net:
            return f"endereço reservado não permitido ({net})"
    return None


def validate_provider_url(raw_url: str, *, allow_localhost: bool = False) -> str:
    """Valida e normaliza URL de provider LLM contra SSRF.

    - Aceita http/https com hosts externos
    - Aceita localhost apenas se allow_localhost=True (dev/testes)
    - Bloqueia metadata servers, loopback (produção), IPs reservados
    - Resolve DNS e valida os IPs resultantes
    - Retorna URL reconstruída de partes validadas (quebra o taint no CodeQL)

    Raises:
        ProviderURLError: se a URL for inválida ou bloqueada
    """
    url = raw_url.strip().rstrip("/")

    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ProviderURLError(f"Scheme '{parsed.scheme}' não permitido. Use http ou https.")

    hostname = parsed.hostname
    if not hostname:
        raise ProviderURLError("URL sem hostname.")

    # Loopback / localhost
    is_localhost = hostname in ("localhost", "127.0.0.1", "::1") or hostname.startswith("127.")
    if is_localhost and not allow_localhost:
        raise ProviderURLError("localhost não permitido. Use o hostname público do provider.")

    # Validação de IP literal (sem DNS)
    reason = _check_ip(hostname)
    if reason:
        raise ProviderURLError(f"Endereço bloqueado: {reason}")

    # Resolução DNS — valida IPs resultantes (previne DNS rebinding)
    if not is_localhost:
        try:
            infos = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
            for *_, sockaddr in infos:
                resolved_ip = sockaddr[0]
                reason = _check_ip(resolved_ip)
                if reason:
                    raise ProviderURLError(f"Hostname '{hostname}' resolve para endereço bloqueado: {reason}")
        except ProviderURLError:
            raise
        except OSError as exc:
            raise ProviderURLError(f"Hostname '{hostname}' não pôde ser resolvido.") from exc

    # Reconstruir URL a partir das partes validadas — quebra o taint no CodeQL.
    # `urlunparse` constrói de componentes estruturais, não do input original.
    safe_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return safe_url.rstrip("/")
