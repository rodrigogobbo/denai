"""Plugin marketplace — browse, install, uninstall plugins."""

from __future__ import annotations

import shutil

import httpx

from .config import DATA_DIR
from .logging_config import get_logger

log = get_logger("marketplace")

PLUGINS_DIR = DATA_DIR / "plugins"
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

# Built-in registry — can be fetched from GitHub later
REGISTRY_URL = "https://raw.githubusercontent.com/rodrigogobbo/denai/main/registry/plugins.json"

# Bundled registry as fallback
BUNDLED_REGISTRY: list[dict] = [
    {
        "id": "weather",
        "name": "Weather",
        "description": "Consulta previsão do tempo via Open-Meteo API (grátis, sem API key)",
        "version": "1.0.0",
        "author": "DenAI",
        "icon": "🌤️",
        "category": "utilities",
        "source": "bundled",
        "install_url": "",
        "code": '''"""Plugin Weather — previsão do tempo via Open-Meteo."""

import json
import urllib.request

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "weather",
            "description": "Consulta a previsão do tempo para uma cidade."
            " Retorna temperatura atual, condição e previsão.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Nome da cidade (ex: 'São Paulo', 'London')",
                    }
                },
                "required": ["city"],
            },
        },
    }
]


def weather(city: str) -> str:
    """Busca previsão do tempo para a cidade."""
    try:
        # Geocoding
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=pt"
        with urllib.request.urlopen(geo_url, timeout=10) as resp:
            geo = json.loads(resp.read())
        if not geo.get("results"):
            return json.dumps({"error": f"Cidade '{city}' não encontrada"})
        loc = geo["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        name = loc.get("name", city)
        country = loc.get("country", "")

        # Weather
        wx_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto&forecast_days=3"
        )
        with urllib.request.urlopen(wx_url, timeout=10) as resp:
            wx = json.loads(resp.read())

        current = wx.get("current", {})
        daily = wx.get("daily", {})

        # Weather code descriptions
        codes = {0: "Céu limpo", 1: "Parcialmente nublado", 2: "Nublado", 3: "Encoberto",
                 45: "Nevoeiro", 51: "Garoa leve", 53: "Garoa", 61: "Chuva leve",
                 63: "Chuva moderada", 65: "Chuva forte", 80: "Pancadas de chuva",
                 95: "Tempestade", 99: "Tempestade com granizo"}
        wc = current.get("weather_code", -1)
        condition = codes.get(wc, f"Código {wc}")

        return json.dumps({
            "city": f"{name}, {country}",
            "current": {
                "temperature": f"{current.get('temperature_2m', '?')}°C",
                "humidity": f"{current.get('relative_humidity_2m', '?')}%",
                "wind": f"{current.get('wind_speed_10m', '?')} km/h",
                "condition": condition,
            },
            "forecast": [
                {
                    "date": daily.get("time", ["?", "?", "?"])[i],
                    "max": f"{daily.get('temperature_2m_max', ['?'])[i]}°C",
                    "min": f"{daily.get('temperature_2m_min', ['?'])[i]}°C",
                    "condition": codes.get(daily.get("weather_code", [0])[i], "?"),
                }
                for i in range(min(3, len(daily.get("time", []))))
            ],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
''',
    },
    {
        "id": "translator",
        "name": "Translator",
        "description": "Tradução de texto via modelo LLM local — sem API externa",
        "version": "1.0.0",
        "author": "DenAI",
        "icon": "🌐",
        "category": "utilities",
        "source": "bundled",
        "install_url": "",
        "code": '''"""Plugin Translator — tradução via prompt LLM."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "translate",
            "description": "Traduz texto para o idioma especificado. Use o LLM para traduzir após receber o resultado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Texto a traduzir"},
                    "target_language": {
                        "type": "string",
                        "description": "Idioma destino (ex: inglês, espanhol)",
                    },
                },
                "required": ["text", "target_language"],
            },
        },
    }
]


def translate(text: str, target_language: str) -> str:
    """Retorna instrução para o LLM traduzir."""
    return (
        f"[TRADUÇÃO SOLICITADA]\\nTexto: {text}\\n"
        f"Idioma destino: {target_language}\\n\\n"
        f"Por favor, traduza o texto acima para {target_language}."
    )
''',
    },
    {
        "id": "pomodoro",
        "name": "Pomodoro Timer",
        "description": "Timer Pomodoro com notificações — foco de 25min + pausa de 5min",
        "version": "1.0.0",
        "author": "DenAI",
        "icon": "🍅",
        "category": "productivity",
        "source": "bundled",
        "install_url": "",
        "code": '''"""Plugin Pomodoro — timer de produtividade."""

import time
import json

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "pomodoro",
            "description": "Inicia um timer Pomodoro. Retorna quando deve terminar para o assistente avisar o usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {
                        "type": "integer",
                        "description": "Duração em minutos (padrão: 25)",
                    },
                    "task": {
                        "type": "string",
                        "description": "Descrição da tarefa (opcional)",
                    },
                },
            },
        },
    }
]


def pomodoro(minutes: int = 25, task: str = "") -> str:
    """Registra início de um Pomodoro."""
    start = time.time()
    end = start + (minutes * 60)
    return json.dumps({
        "status": "started",
        "minutes": minutes,
        "task": task or "Foco",
        "started_at": time.strftime("%H:%M:%S", time.localtime(start)),
        "ends_at": time.strftime("%H:%M:%S", time.localtime(end)),
        "message": (
            f"🍅 Pomodoro de {minutes}min iniciado! "
            f"Foco em: {task or 'tarefa atual'}. "
            f"Termina às {time.strftime('%H:%M', time.localtime(end))}."
        ),
    })
''',
    },
]


def get_registry() -> list[dict]:
    """Get the plugin registry (bundled + remote if available)."""
    registry = list(BUNDLED_REGISTRY)

    # Try to fetch remote registry
    try:
        resp = httpx.get(REGISTRY_URL, timeout=5)
        if resp.status_code == 200:
            remote = resp.json()
            # Merge remote plugins (don't duplicate by id)
            existing_ids = {p["id"] for p in registry}
            for p in remote:
                if p["id"] not in existing_ids:
                    registry.append(p)
    except Exception:
        pass  # Use bundled only

    # Mark installed status
    for plugin in registry:
        plugin["installed"] = _is_installed(plugin["id"])

    return registry


def _is_installed(plugin_id: str) -> bool:
    """Check if a plugin is installed."""
    plugin_dir = PLUGINS_DIR / plugin_id
    plugin_file = PLUGINS_DIR / f"{plugin_id}.py"
    return plugin_dir.exists() or plugin_file.exists()


def install_plugin(plugin_id: str) -> dict:
    """Install a plugin from the registry."""
    registry = get_registry()
    plugin = next((p for p in registry if p["id"] == plugin_id), None)

    if not plugin:
        return {"error": f"Plugin '{plugin_id}' não encontrado no registry"}

    if _is_installed(plugin_id):
        return {"error": f"Plugin '{plugin_id}' já está instalado"}

    try:
        if plugin.get("code"):
            # Bundled plugin — write code directly
            plugin_file = PLUGINS_DIR / f"{plugin_id}.py"
            plugin_file.write_text(plugin["code"], encoding="utf-8")
            log.info("Plugin '%s' instalado de bundled registry", plugin_id)
        elif plugin.get("install_url"):
            # Remote plugin — download
            resp = httpx.get(plugin["install_url"], timeout=30)
            resp.raise_for_status()
            plugin_file = PLUGINS_DIR / f"{plugin_id}.py"
            plugin_file.write_text(resp.text, encoding="utf-8")
            log.info("Plugin '%s' instalado de %s", plugin_id, plugin["install_url"])
        else:
            return {"error": "Plugin sem código ou URL de instalação"}

        return {
            "ok": True,
            "plugin": plugin_id,
            "message": f"Plugin '{plugin['name']}' instalado com sucesso! Reinicie o chat para ativar.",
        }
    except Exception as e:
        log.error("Erro instalando plugin '%s': %s", plugin_id, e)
        return {"error": str(e)}


def uninstall_plugin(plugin_id: str) -> dict:
    """Uninstall a plugin."""
    plugin_file = PLUGINS_DIR / f"{plugin_id}.py"
    plugin_dir = PLUGINS_DIR / plugin_id

    removed = False
    if plugin_file.exists():
        plugin_file.unlink()
        removed = True
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)
        removed = True

    if removed:
        log.info("Plugin '%s' removido", plugin_id)
        return {"ok": True, "message": f"Plugin '{plugin_id}' removido. Reinicie o chat para aplicar."}
    return {"error": f"Plugin '{plugin_id}' não está instalado"}
