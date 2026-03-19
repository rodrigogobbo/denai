"""Plugin de exemplo: calculadora."""

__version__ = "1.0.0"

SPEC = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Calcula expressões matemáticas simples (soma, subtração, multiplicação, divisão).",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expressão matemática (ex: '2 + 3 * 4')",
                },
            },
            "required": ["expression"],
        },
    },
}


async def calculator(args: dict) -> str:
    """Avalia uma expressão matemática com segurança."""
    expr = args.get("expression", "")
    if not expr:
        return "❌ Expressão vazia"

    # Whitelist de caracteres seguros
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expr):
        return "❌ Expressão contém caracteres não permitidos"

    try:
        result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
        return f"Resultado: {result}"
    except Exception as e:
        return f"❌ Erro ao calcular: {e}"


TOOLS = [(SPEC, "calculator")]
