"""Pacote de rotas do DenAI."""

from .agent import router as agent_router
from .chat import router as chat_router
from .commands import router as commands_router
from .conversations import router as conversations_router
from .diagnostics import router as diagnostics_router
from .marketplace import router as marketplace_router
from .mcp import router as mcp_router
from .memories import router as memories_router
from .models import router as models_router
from .permissions import router as permissions_router
from .plans import router as plans_router
from .plans_spec import router as plans_spec_router
from .plugins import router as plugins_router
from .project import router as project_router
from .questions import router as questions_router
from .rag import router as rag_router
from .skills import router as skills_router
from .todos import router as todos_router
from .ui import router as ui_router
from .undo import router as undo_router
from .update import router as update_router
from .voice import router as voice_router

all_routers = [
    ui_router,
    chat_router,
    agent_router,
    commands_router,
    conversations_router,
    models_router,
    memories_router,
    mcp_router,
    permissions_router,
    plans_router,
    plans_spec_router,
    todos_router,
    plugins_router,
    project_router,
    marketplace_router,
    rag_router,
    questions_router,
    skills_router,
    diagnostics_router,
    undo_router,
    update_router,
    voice_router,
]

__all__ = ["all_routers"]
