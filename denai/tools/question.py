"""Tool de interação — pausar e perguntar ao usuário."""

from __future__ import annotations

import asyncio
from typing import Optional

# ─── Spec ──────────────────────────────────────────────────────────────────

QUESTION_SPEC = {
    "type": "function",
    "function": {
        "name": "question",
        "description": (
            "Faz uma pergunta ao usuário e aguarda a resposta. "
            "Use quando precisar de confirmação, escolha entre opções, "
            "ou informação que só o usuário pode fornecer. "
            "A resposta do usuário é retornada como texto."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "A pergunta a fazer ao usuário",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Opções para o usuário escolher (opcional). Ex: ['Sim', 'Não']",
                },
            },
            "required": ["question"],
        },
    },
}


# ─── Pending Questions Store ───────────────────────────────────────────────

# Armazena perguntas pendentes e suas respostas.
# Cada pergunta recebe um ID único. O frontend envia a resposta
# via POST /api/question/{id}/answer.

_pending: dict[str, asyncio.Future] = {}
_questions: dict[str, dict] = {}
_counter = 0


def _next_id() -> str:
    global _counter
    _counter += 1
    return f"q_{_counter}"


def get_pending_question(question_id: str) -> Optional[dict]:
    """Retorna dados da pergunta pendente (ou None)."""
    return _questions.get(question_id)


def answer_question(question_id: str, answer: str) -> bool:
    """Responde uma pergunta pendente. Retorna True se existia."""
    future = _pending.get(question_id)
    if future and not future.done():
        future.set_result(answer)
        return True
    return False


def list_pending() -> list[dict]:
    """Lista perguntas pendentes."""
    return [{"id": qid, **data} for qid, data in _questions.items() if qid in _pending and not _pending[qid].done()]


# ─── Executor ──────────────────────────────────────────────────────────────


async def question(args: dict) -> str:
    """Faz uma pergunta ao usuário e espera a resposta."""
    text = args.get("question", "").strip()
    if not text:
        return "❌ Parâmetro 'question' é obrigatório."

    options = args.get("options", [])
    qid = _next_id()

    # Criar future para esperar resposta
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    _pending[qid] = future
    _questions[qid] = {
        "question": text,
        "options": options,
    }

    # O SSE event será enviado pelo ollama.py quando detectar
    # que a tool retornou um "question_id" — o frontend mostra
    # o prompt e envia a resposta via API.
    #
    # Mas precisamos retornar algo especial para o ollama.py
    # saber que deve esperar. Usamos um prefixo mágico.

    try:
        # Timeout de 5 minutos
        answer_text = await asyncio.wait_for(future, timeout=300)
    except asyncio.TimeoutError:
        _pending.pop(qid, None)
        _questions.pop(qid, None)
        return "⏱️ Timeout — o usuário não respondeu em 5 minutos."
    finally:
        _pending.pop(qid, None)
        _questions.pop(qid, None)

    return f"Resposta do usuário: {answer_text}"


# ─── SSE Helper ────────────────────────────────────────────────────────────


def create_question_event(question_text: str, options: list) -> tuple[str, str]:
    """Cria um question ID e retorna (question_id, sse_data).

    Chamado pelo ollama.py ANTES de executar a tool,
    para enviar o evento SSE ao frontend.
    """
    qid = _next_id()
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    _pending[qid] = future
    _questions[qid] = {
        "question": question_text,
        "options": options,
    }
    return qid, future


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (QUESTION_SPEC, "question"),
]
