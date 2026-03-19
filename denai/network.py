"""Utilidades de rede."""

import socket


def get_local_ip() -> str:
    """Descobre o IP local na rede WiFi/Ethernet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "?.?.?.?"


LOCAL_IP = get_local_ip()
