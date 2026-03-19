"""Rota /api/question — responder perguntas pendentes da tool question."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..tools.question import answer_question, list_pending

router = APIRouter()


@router.get("/api/questions/pending")
async def get_pending_questions():
    """Lista perguntas pendentes aguardando resposta do usuário."""
    return {"questions": list_pending()}


@router.post("/api/questions/{question_id}/answer")
async def post_answer(question_id: str, request_body: dict = {}):
    """Responde uma pergunta pendente."""
    answer = request_body.get("answer", "")
    if not answer.strip():
        return JSONResponse({"error": "Resposta vazia"}, status_code=400)

    found = answer_question(question_id, answer)
    if not found:
        return JSONResponse(
            {"error": f"Pergunta '{question_id}' não encontrada ou já respondida"},
            status_code=404,
        )

    return {"ok": True, "question_id": question_id}
