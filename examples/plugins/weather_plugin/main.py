"""Plugin de exemplo: clima (demonstra plugin com diretório)."""

SPEC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Retorna informações sobre o clima de uma cidade (exemplo simulado).",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Nome da cidade"},
            },
            "required": ["city"],
        },
    },
}


async def get_weather(args: dict) -> str:
    """Retorna clima simulado (plugin de exemplo)."""
    city = args.get("city", "desconhecida")
    return f"☀️ Clima em {city}: 25°C, ensolarado (dados simulados — este é um plugin de exemplo)"


TOOLS = [(SPEC, "get_weather")]
