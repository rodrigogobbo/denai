"""Pacote de rotas do DenAI."""

from .chat import router as chat_router
from .conversations import router as conversations_router
from .memories import router as memories_router
from .models import router as models_router
from .ui import router as ui_router

all_routers = [
    ui_router,
    chat_router,
    conversations_router,
    models_router,
    memories_router,
]

__all__ = ["all_routers"]
