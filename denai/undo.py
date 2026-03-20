"""Undo/Redo — revert file changes made by the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .logging_config import get_logger

log = get_logger("undo")


@dataclass
class FileSnapshot:
    """A snapshot of a file's state before a change."""

    path: str
    content: str | None  # None means file didn't exist
    existed: bool


@dataclass
class ChangeSet:
    """A group of file changes made in one turn."""

    snapshots: list[FileSnapshot] = field(default_factory=list)
    description: str = ""

    @property
    def file_count(self) -> int:
        return len(self.snapshots)

    @property
    def files(self) -> list[str]:
        return [s.path for s in self.snapshots]


# ── Global stacks ─────────────────────────────────────────────────

_undo_stack: list[ChangeSet] = []
_redo_stack: list[ChangeSet] = []
_current_changeset: ChangeSet | None = None

MAX_UNDO_STACK = 50  # Maximum number of undo levels


def start_changeset(description: str = "") -> None:
    """Start recording a new set of changes."""
    global _current_changeset
    _current_changeset = ChangeSet(description=description)


def save_snapshot(file_path: str) -> None:
    """Save a snapshot of a file before it's modified.

    Call this BEFORE modifying the file.
    """
    global _current_changeset

    if _current_changeset is None:
        _current_changeset = ChangeSet()

    # Don't save duplicate snapshots for the same file in the same changeset
    existing_paths = {s.path for s in _current_changeset.snapshots}
    if file_path in existing_paths:
        return

    path = Path(file_path)
    try:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            snapshot = FileSnapshot(path=file_path, content=content, existed=True)
        else:
            snapshot = FileSnapshot(path=file_path, content=None, existed=False)

        _current_changeset.snapshots.append(snapshot)
        log.debug("Snapshot salvo: %s (existed=%s)", file_path, path.exists())
    except Exception as e:
        log.warning("Erro salvando snapshot de %s: %s", file_path, e)


def commit_changeset() -> None:
    """Commit the current changeset to the undo stack."""
    global _current_changeset

    if _current_changeset is None or not _current_changeset.snapshots:
        _current_changeset = None
        return

    _undo_stack.append(_current_changeset)
    _redo_stack.clear()  # New changes invalidate redo

    # Trim stack
    while len(_undo_stack) > MAX_UNDO_STACK:
        _undo_stack.pop(0)

    log.info(
        "Changeset commitado: %d arquivos (%s)",
        _current_changeset.file_count,
        ", ".join(_current_changeset.files),
    )
    _current_changeset = None


def undo() -> dict:
    """Undo the last changeset. Returns info about what was undone."""
    if not _undo_stack:
        return {"error": "Nada para desfazer"}

    changeset = _undo_stack.pop()

    # Save current state for redo
    redo_changeset = ChangeSet(description=f"redo: {changeset.description}")
    for snapshot in changeset.snapshots:
        path = Path(snapshot.path)
        try:
            if path.exists():
                redo_changeset.snapshots.append(
                    FileSnapshot(
                        path=snapshot.path,
                        content=path.read_text(encoding="utf-8"),
                        existed=True,
                    )
                )
            else:
                redo_changeset.snapshots.append(FileSnapshot(path=snapshot.path, content=None, existed=False))
        except Exception:
            pass

    # Restore files
    restored = []
    for snapshot in changeset.snapshots:
        path = Path(snapshot.path)
        try:
            if snapshot.existed:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(snapshot.content or "", encoding="utf-8")
                restored.append({"path": snapshot.path, "action": "restored"})
            else:
                if path.exists():
                    path.unlink()
                    restored.append({"path": snapshot.path, "action": "deleted"})
        except Exception as e:
            restored.append({"path": snapshot.path, "action": "error", "error": str(e)})

    _redo_stack.append(redo_changeset)
    log.info("Undo: %d arquivos restaurados", len(restored))

    return {
        "ok": True,
        "files": restored,
        "remaining": len(_undo_stack),
    }


def redo() -> dict:
    """Redo the last undone changeset."""
    if not _redo_stack:
        return {"error": "Nada para refazer"}

    changeset = _redo_stack.pop()

    # Save current state for undo again
    undo_changeset = ChangeSet(description=f"undo: {changeset.description}")
    for snapshot in changeset.snapshots:
        path = Path(snapshot.path)
        try:
            if path.exists():
                undo_changeset.snapshots.append(
                    FileSnapshot(
                        path=snapshot.path,
                        content=path.read_text(encoding="utf-8"),
                        existed=True,
                    )
                )
            else:
                undo_changeset.snapshots.append(FileSnapshot(path=snapshot.path, content=None, existed=False))
        except Exception:
            pass

    # Apply redo
    applied = []
    for snapshot in changeset.snapshots:
        path = Path(snapshot.path)
        try:
            if snapshot.existed:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(snapshot.content or "", encoding="utf-8")
                applied.append({"path": snapshot.path, "action": "restored"})
            else:
                if path.exists():
                    path.unlink()
                    applied.append({"path": snapshot.path, "action": "deleted"})
        except Exception as e:
            applied.append({"path": snapshot.path, "action": "error", "error": str(e)})

    _undo_stack.append(undo_changeset)
    log.info("Redo: %d arquivos reaplicados", len(applied))

    return {
        "ok": True,
        "files": applied,
        "remaining_redo": len(_redo_stack),
    }


def get_status() -> dict:
    """Get current undo/redo status."""
    return {
        "undo_available": len(_undo_stack),
        "redo_available": len(_redo_stack),
        "current_changeset": _current_changeset.file_count if _current_changeset else 0,
    }


def clear() -> None:
    """Clear all undo/redo history."""
    global _current_changeset
    _undo_stack.clear()
    _redo_stack.clear()
    _current_changeset = None
