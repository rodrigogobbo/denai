"""Integração com Ollama — streaming chat com tool calling."""

import json
from typing import AsyncGenerator

import httpx

from ..config import DEFAULT_MODEL, OLLAMA_URL
from ..tools import TOOLS_SPEC, execute_tool
from .prompt import build_system_prompt


async def stream_chat(
    messages: list,
    model: str = DEFAULT_MODEL,
    use_tools: bool = True,
) -> AsyncGenerator[str, None]:
    """Stream de chat com Ollama, com suporte a tool calling iterativo."""

    system_msg = {"role": "system", "content": build_system_prompt()}
    full_messages = [system_msg] + messages

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        max_tool_rounds = 5

        for _ in range(max_tool_rounds):
            payload = {
                "model": model,
                "messages": full_messages,
                "stream": True,
                "options": {"temperature": 0.7, "num_ctx": 8192},
            }
            if use_tools and TOOLS_SPEC:
                payload["tools"] = TOOLS_SPEC

            accumulated = ""
            tool_calls = []

            async with client.stream(
                "POST", f"{OLLAMA_URL}/api/chat", json=payload
            ) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    err_msg = f"Ollama error {resp.status_code}: {error_text.decode()}"
                    yield f"data: {json.dumps({'error': err_msg})}\n\n"
                    return

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if "message" in chunk:
                        msg = chunk["message"]
                        if msg.get("content"):
                            accumulated += msg["content"]
                            yield f"data: {json.dumps({'content': msg['content']})}\n\n"
                        if msg.get("tool_calls"):
                            tool_calls.extend(msg["tool_calls"])

                    if chunk.get("done"):
                        break

            if not tool_calls:
                break

            # Executar tool calls
            full_messages.append({
                "role": "assistant",
                "content": accumulated,
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "unknown")
                tool_args = fn.get("arguments", {})

                yield f"data: {json.dumps({'tool_call': {'name': tool_name, 'args': tool_args}})}\n\n"

                result = await execute_tool(tool_name, tool_args)

                yield f"data: {json.dumps({'tool_result': {'name': tool_name, 'result': result[:2000]}})}\n\n"

                full_messages.append({"role": "tool", "content": result})

            tool_calls = []
            accumulated = ""

        yield 'data: {"done": true}\n\n'
