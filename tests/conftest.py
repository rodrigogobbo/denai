"""Configurações compartilhadas dos testes do DenAI."""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Cria um event loop para testes async."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
