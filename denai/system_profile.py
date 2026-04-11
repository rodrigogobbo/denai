"""Detecção de hardware e recomendação de modelo LLM.

Detecta RAM, VRAM, disco, arquitetura e modelos instalados no Ollama.
Retorna um tier de hardware e recomendação de modelo com explicação.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass

import httpx

from .config import DATA_DIR, OLLAMA_URL
from .logging_config import get_logger

log = get_logger("system_profile")

# ─── Tiers e modelos recomendados ──────────────────────────────────────────


@dataclass
class ModelOption:
    name: str
    size_gb: float
    ram_min_gb: float
    description: str
    emoji: str = "🤖"


# Modelos em ordem crescente de peso
MODEL_CATALOG: list[ModelOption] = [
    ModelOption("llama3.2:1b", 0.8, 4, "Ultraleve — para máquinas com pouca RAM", "⚡"),
    ModelOption("llama3.2:3b", 2.0, 6, "Leve e rápido — ótimo pra começar", "🚀"),
    ModelOption("llama3.1:8b", 4.7, 10, "Equilíbrio ideal — qualidade e velocidade", "🧠"),
    ModelOption("qwen2.5-coder:7b", 4.4, 10, "Especialista em código — ferramenta calling ok", "💻"),
    ModelOption("qwen2.5-coder:14b", 9.0, 20, "Código avançado — tool calling confiável", "🏆"),
    ModelOption("qwen2.5-coder:32b", 18.0, 36, "Melhor qualidade disponível", "🎯"),
]

TIERS: list[tuple[float, str]] = [
    (6, "minimal"),
    (10, "light"),
    (20, "mid"),
    (36, "high"),
    (999, "ultra"),
]

TIER_DEFAULTS = {
    "minimal": "llama3.2:1b",
    "light": "llama3.2:3b",
    "mid": "llama3.1:8b",
    "high": "qwen2.5-coder:14b",
    "ultra": "qwen2.5-coder:32b",
}

TIER_REASONS = {
    "minimal": "sua máquina tem pouca RAM — usaremos o modelo mais leve disponível",
    "light": "RAM limitada — modelo leve que funciona bem para conversas",
    "mid": "RAM suficiente para boa qualidade com velocidade razoável",
    "high": "RAM abundante — modelo poderoso com tool calling confiável",
    "ultra": "máquina potente — melhor modelo disponível",
}


# ─── Detecção de hardware ──────────────────────────────────────────────────


def _get_ram_gb() -> float:
    """RAM total em GB. Retorna 8.0 como fallback conservador."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return round(int(line.split()[1]) / (1024 * 1024), 1)
    except Exception:
        pass
    try:
        out = subprocess.check_output(  # noqa: S603
            ["sysctl", "-n", "hw.memsize"],  # noqa: S607
            text=True,
            timeout=3,
        )
        return round(int(out.strip()) / (1024**3), 1)
    except Exception:
        pass
    try:
        import ctypes

        if hasattr(ctypes, "windll"):

            class _MEMSTATUS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    *[
                        (f, ctypes.c_ulonglong)
                        for f in (
                            "ullAvailPhys",
                            "ullTotalPageFile",
                            "ullAvailPageFile",
                            "ullTotalVirtual",
                            "ullAvailVirtual",
                            "sullAvailExtendedVirtual",
                        )
                    ],
                ]

            stat = _MEMSTATUS()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return round(stat.ullTotalPhys / (1024**3), 1)
    except Exception:
        pass
    return 8.0  # fallback conservador


def _get_vram_gb() -> float | None:
    """VRAM da GPU em GB. Retorna None se não detectado."""
    # nvidia-smi (Linux/Windows)
    try:
        out = subprocess.check_output(  # noqa: S603
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],  # noqa: S607
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        mb = int(out.strip().splitlines()[0])
        return round(mb / 1024, 1)
    except Exception:
        pass
    # macOS — unified memory (Apple Silicon usa RAM como VRAM)
    try:
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            out = subprocess.check_output(  # noqa: S603
                ["system_profiler", "SPHardwareDataType"],  # noqa: S607
                text=True,
                timeout=5,
            )
            for line in out.splitlines():
                if "Memory:" in line:
                    parts = line.split()
                    for _i, p in enumerate(parts):
                        if p.isdigit():
                            gb = int(p)
                            # Apple Silicon: unified memory — GPU usa a RAM toda
                            return float(gb)
    except Exception:
        pass
    return None


def _get_disk_free_gb() -> float:
    """Espaço livre em disco no diretório de dados."""
    try:
        usage = shutil.disk_usage(DATA_DIR)
        return round(usage.free / (1024**3), 1)
    except Exception:
        return 0.0


def _get_cpu_cores() -> int:
    """Número de cores lógicos."""
    try:
        import os

        return os.cpu_count() or 4
    except Exception:
        return 4


async def _get_installed_models() -> list[str]:
    """Modelos disponíveis no Ollama local."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass
    return []


# ─── Lógica de recomendação ────────────────────────────────────────────────


def _get_tier(ram_gb: float, vram_gb: float | None) -> str:
    """Determina o tier baseado em RAM (e VRAM como boost)."""
    effective_ram = ram_gb
    # Apple Silicon: unified memory — VRAM = RAM, sem boost extra
    # Nvidia/AMD: VRAM como boost parcial
    if vram_gb and platform.machine() != "arm64":
        effective_ram = max(ram_gb, vram_gb * 1.5)

    for threshold, tier in TIERS:
        if effective_ram < threshold:
            return tier
    return "ultra"


def _best_installed(installed: list[str], tier: str, ram_gb: float) -> str | None:
    """Melhor modelo já instalado compatível com a máquina."""
    # Filtrar modelos do catálogo que estão instalados e cabem na RAM
    compatible = [
        m
        for m in MODEL_CATALOG
        if any(inst.startswith(m.name.split(":")[0]) for inst in installed) and m.ram_min_gb <= ram_gb
    ]
    if not compatible:
        return None
    # Retornar o mais pesado compatível (melhor qualidade que cabe)
    best = max(compatible, key=lambda m: m.ram_min_gb)
    # Verificar nome exato instalado
    for inst in installed:
        if inst.startswith(best.name.split(":")[0]):
            return inst
    return None


def _recommend(tier: str, ram_gb: float, installed: list[str]) -> dict:
    """Gera recomendação de modelo com explicação."""
    # Se já tem bom modelo instalado, priorizar
    best_inst = _best_installed(installed, tier, ram_gb)
    if best_inst:
        reason = "você já tem este modelo — sem necessidade de download"
        return {
            "model": best_inst,
            "reason": reason,
            "already_installed": True,
            "alternatives": _alternatives(best_inst, ram_gb),
        }

    # Recomendar baseado no tier
    model = TIER_DEFAULTS[tier]
    reason = TIER_REASONS[tier]

    # Verificar se tem disco para baixar
    disk_free = _get_disk_free_gb()
    catalog_entry = next((m for m in MODEL_CATALOG if m.name == model), None)
    if catalog_entry and disk_free < catalog_entry.size_gb + 1:
        # Sem disco: descer um tier
        lighter_tiers = ["minimal", "light", "mid", "high", "ultra"]
        idx = lighter_tiers.index(tier)
        if idx > 0:
            tier = lighter_tiers[idx - 1]
            model = TIER_DEFAULTS[tier]
            reason = f"espaço em disco limitado ({disk_free:.0f}GB) — usando modelo menor"

    return {
        "model": model,
        "reason": reason,
        "already_installed": model in installed or any(inst.startswith(model.split(":")[0]) for inst in installed),
        "alternatives": _alternatives(model, ram_gb),
    }


def _alternatives(current: str, ram_gb: float) -> list[dict]:
    """Modelos alternativos compatíveis com a RAM."""
    alts = []
    for m in MODEL_CATALOG:
        if m.name == current:
            continue
        if m.ram_min_gb > ram_gb * 1.1:  # 10% margem
            continue
        alts.append(
            {
                "name": m.name,
                "size_gb": m.size_gb,
                "ram_min_gb": m.ram_min_gb,
                "description": m.description,
                "emoji": m.emoji,
            }
        )
    # Retornar até 4 alternativas (as mais próximas do atual)
    return sorted(alts, key=lambda x: abs(x["ram_min_gb"] - ram_gb))[:4]


# ─── Profile completo ──────────────────────────────────────────────────────


async def get_system_profile() -> dict:
    """Perfil completo do sistema com recomendação de modelo."""
    ram_gb = _get_ram_gb()
    vram_gb = _get_vram_gb()
    disk_free_gb = _get_disk_free_gb()
    cpu_cores = _get_cpu_cores()
    installed = await _get_installed_models()

    tier = _get_tier(ram_gb, vram_gb)
    recommendation = _recommend(tier, ram_gb, installed)

    # Aviso de compatibilidade para cada modelo do catálogo
    model_list = []
    for m in MODEL_CATALOG:
        compatible = m.ram_min_gb <= ram_gb
        warning = None
        if not compatible:
            warning = f"requer ~{m.ram_min_gb}GB RAM (você tem {ram_gb}GB)"
        elif m.ram_min_gb > ram_gb * 0.8:
            warning = f"pode ficar lento — usa {m.ram_min_gb}GB dos seus {ram_gb}GB"
        model_list.append(
            {
                "name": m.name,
                "size_gb": m.size_gb,
                "ram_min_gb": m.ram_min_gb,
                "description": m.description,
                "emoji": m.emoji,
                "compatible": compatible,
                "warning": warning,
                "installed": any(inst.startswith(m.name.split(":")[0]) for inst in installed),
            }
        )

    return {
        "ram_gb": ram_gb,
        "vram_gb": vram_gb,
        "disk_free_gb": disk_free_gb,
        "cpu_cores": cpu_cores,
        "os": platform.system().lower(),
        "arch": platform.machine(),
        "tier": tier,
        "recommendation": recommendation,
        "installed_models": installed,
        "model_catalog": model_list,
    }
