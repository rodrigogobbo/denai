"""Testes do sistema de modos (Build vs Plan)."""

from __future__ import annotations

from denai.modes import (
    MODES,
    PLAN_MODE_TOOLS,
    filter_tools_for_mode,
    get_system_prompt_prefix,
)

# ── Tool filtering ───────────────────────────────────────────────

SAMPLE_TOOLS = [
    {"function": {"name": "file_read", "description": "Read a file"}},
    {"function": {"name": "file_edit", "description": "Edit a file"}},
    {"function": {"name": "file_write", "description": "Write a file"}},
    {"function": {"name": "command_exec", "description": "Execute a command"}},
    {"function": {"name": "grep", "description": "Search in files"}},
    {"function": {"name": "list_files", "description": "List files"}},
    {"function": {"name": "think", "description": "Think step by step"}},
    {"function": {"name": "web_search", "description": "Search the web"}},
]


def test_build_mode_returns_all_tools():
    result = filter_tools_for_mode(SAMPLE_TOOLS, "build")
    assert len(result) == len(SAMPLE_TOOLS)


def test_plan_mode_filters_write_tools():
    result = filter_tools_for_mode(SAMPLE_TOOLS, "plan")
    names = {t["function"]["name"] for t in result}
    assert "file_read" in names
    assert "grep" in names
    assert "list_files" in names
    assert "think" in names
    assert "web_search" in names
    # Write tools should be excluded
    assert "file_edit" not in names
    assert "file_write" not in names
    assert "command_exec" not in names


def test_plan_mode_tools_are_readonly():
    """All plan mode tools should be genuinely read-only."""
    write_tools = {
        "file_edit",
        "file_write",
        "file_delete",
        "command_exec",
        "create_document",
        "create_spreadsheet",
    }
    assert PLAN_MODE_TOOLS.isdisjoint(write_tools)


def test_unknown_mode_returns_all_tools():
    result = filter_tools_for_mode(SAMPLE_TOOLS, "whatever")
    assert len(result) == len(SAMPLE_TOOLS)


# ── System prompt ────────────────────────────────────────────────


def test_plan_mode_prompt_prefix():
    prefix = get_system_prompt_prefix("plan")
    assert "MODO PLANO" in prefix
    assert "NÃO modifique" in prefix


def test_build_mode_no_prefix():
    assert get_system_prompt_prefix("build") == ""


# ── Constants ────────────────────────────────────────────────────


def test_modes_set():
    assert "build" in MODES
    assert "plan" in MODES


def test_plan_tools_not_empty():
    assert len(PLAN_MODE_TOOLS) >= 5
