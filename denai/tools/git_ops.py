"""Git operations tool — structured wrappers for git CLI."""

from __future__ import annotations

import asyncio
import json

from ..logging_config import get_logger
from ..permissions import check_permission
from ..security.sandbox import is_path_allowed

log = get_logger("git_ops")

# ─── Constants ───────────────────────────────────────────────────────────

_GIT_TIMEOUT = 30
_DEFAULT_LOG_LIMIT = 10

_WRITE_OPS = {"add", "commit", "checkout", "stash", "branch"}


# ─── Response Helpers ────────────────────────────────────────────────────


def _ok(data: dict) -> str:
    """Return a successful JSON response."""
    return json.dumps(data)


def _err(msg: str, *, suggestion: str = "") -> str:
    """Return an error JSON response with optional suggestion."""
    result: dict = {"error": msg}
    if suggestion:
        result["suggestion"] = suggestion
    return json.dumps(result)


# ─── Git Runner ──────────────────────────────────────────────────────────


async def _run_git(args: list[str], cwd: str | None = None) -> tuple[bool, str, str]:
    """Run a git command asynchronously and return (success, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=_GIT_TIMEOUT,
        )
        stdout = stdout_bytes.decode() if stdout_bytes else ""
        stderr = stderr_bytes.decode() if stderr_bytes else ""
        return proc.returncode == 0, stdout, stderr
    except (TimeoutError, asyncio.TimeoutError):
        return False, "", f"Git command timed out after {_GIT_TIMEOUT} seconds"
    except FileNotFoundError:
        return False, "", "Git is not installed or not in PATH"


async def _validate_repo(cwd: str | None = None) -> str | None:
    """Check if cwd is inside a git repo. Returns error message or None."""
    ok, _, _ = await _run_git(["rev-parse", "--git-dir"], cwd=cwd)
    if not ok:
        return "Not a git repository. Navigate to a git repo first."
    return None


# ─── Parsers ─────────────────────────────────────────────────────────────


def _parse_status(stdout: str) -> dict:
    """Parse git status --porcelain=v2 --branch output."""
    staged = []
    unstaged = []
    untracked = []
    branch = ""
    ahead = 0
    behind = 0

    for line in stdout.splitlines():
        if line.startswith("# branch.head "):
            branch = line.split(" ", 2)[2]
        elif line.startswith("# branch.ab "):
            parts = line.split(" ")
            for p in parts[2:]:
                if p.startswith("+"):
                    ahead = int(p[1:])
                elif p.startswith("-"):
                    behind = int(p[1:])
        elif line.startswith("1 ") or line.startswith("2 "):
            parts = line.split(" ")
            xy = parts[1]
            filename = parts[-1]
            if xy[0] != ".":
                staged.append(filename)
            if xy[1] != ".":
                unstaged.append(filename)
        elif line.startswith("? "):
            untracked.append(line[2:])

    return {
        "branch": branch,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "ahead": ahead,
        "behind": behind,
    }


def _parse_diff(stdout: str) -> dict:
    """Parse git diff output into structured files."""
    files = []
    current_file = None

    for line in stdout.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                files.append(current_file)
            parts = line.split(" b/", 1)
            name = parts[1] if len(parts) > 1 else ""
            current_file = {"name": name, "added": 0, "removed": 0, "patch": []}
        elif current_file is not None:
            current_file["patch"].append(line)
            if line.startswith("+") and not line.startswith("+++"):
                current_file["added"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                current_file["removed"] += 1

    if current_file:
        files.append(current_file)

    # Convert patch lists to strings for readability
    for f in files:
        f["patch"] = "\n".join(f["patch"])

    return {"files": files}


def _parse_log(stdout: str) -> dict:
    """Parse git log output."""
    commits = []
    for line in stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t", 3)
        if len(parts) >= 4:
            commits.append(
                {
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                }
            )
    return {"commits": commits}


def _parse_branches(stdout: str) -> dict:
    """Parse git branch output."""
    branches = []
    current = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("* "):
            name = line[2:].strip()
            current = name
            branches.append(name)
        else:
            branches.append(line)
    return {"branches": branches, "current": current}


# ─── Operations (dispatch targets) ──────────────────────────────────────


async def _op_status(args: dict, cwd: str | None) -> str:
    """Handle git status."""
    ok, stdout, stderr = await _run_git(["status", "--porcelain=v2", "--branch"], cwd=cwd)
    if not ok:
        return _err(f"git status failed: {stderr}")
    return _ok(_parse_status(stdout))


async def _op_diff(args: dict, cwd: str | None) -> str:
    """Handle git diff."""
    cmd = ["diff"]
    if args.get("ref"):
        cmd.append(args["ref"])
    if args.get("path"):
        cmd.extend(["--", args["path"]])
    ok, stdout, stderr = await _run_git(cmd, cwd=cwd)
    if not ok:
        return _err(f"git diff failed: {stderr}")
    return _ok(_parse_diff(stdout))


async def _op_log(args: dict, cwd: str | None) -> str:
    """Handle git log."""
    limit = args.get("limit", _DEFAULT_LOG_LIMIT)
    ok, stdout, stderr = await _run_git(
        ["log", f"-{limit}", "--format=%H\t%an\t%ai\t%s"],
        cwd=cwd,
    )
    if not ok:
        return _err(
            f"git log failed: {stderr}",
            suggestion="Ensure there are commits in the repository.",
        )
    return _ok(_parse_log(stdout))


async def _op_branch(args: dict, cwd: str | None) -> str:
    """Handle git branch (list, create, delete)."""
    if args.get("create"):
        ok, _stdout, stderr = await _run_git(["checkout", "-b", args["create"]], cwd=cwd)
        if not ok:
            return _err(f"Failed to create branch: {stderr}")
        return _ok({"created": args["create"], "current": args["create"]})
    if args.get("delete"):
        ok, _stdout, stderr = await _run_git(["branch", "-d", args["delete"]], cwd=cwd)
        if not ok:
            return _err(f"Failed to delete branch: {stderr}")
        return _ok({"deleted": args["delete"]})
    # List branches
    ok, stdout, stderr = await _run_git(["branch"], cwd=cwd)
    if not ok:
        return _err(f"git branch failed: {stderr}")
    return _ok(_parse_branches(stdout))


async def _op_add(args: dict, cwd: str | None) -> str:
    """Handle git add."""
    paths = args.get("paths", ["."])
    if isinstance(paths, str):
        paths = [paths]
    ok, _stdout, stderr = await _run_git(["add", *paths], cwd=cwd)
    if not ok:
        return _err(f"git add failed: {stderr}")
    return _ok({"added": paths})


async def _op_commit(args: dict, cwd: str | None) -> str:
    """Handle git commit."""
    message = args.get("message", "")
    if not message:
        return _err("Commit message is required.")
    ok, stdout, stderr = await _run_git(["commit", "-m", message], cwd=cwd)
    if not ok:
        if "nothing to commit" in stderr or "nothing to commit" in stdout:
            return _err("Nothing to commit.", suggestion="Stage files with git add first.")
        return _err(f"git commit failed: {stderr}")
    # Parse commit hash from output
    commit_hash = ""
    for line in stdout.splitlines():
        if line.strip().startswith("["):
            parts = line.split()
            for p in parts:
                if len(p) >= 7 and p.endswith("]"):
                    commit_hash = p.rstrip("]")
                    break
    return _ok({"hash": commit_hash, "message": message})


async def _op_checkout(args: dict, cwd: str | None) -> str:
    """Handle git checkout."""
    ref = args.get("ref", "")
    if not ref:
        return _err("Ref (branch name or commit) is required.")
    ok, _stdout, stderr = await _run_git(["checkout", ref], cwd=cwd)
    if not ok:
        suggestion = ""
        if "conflict" in stderr.lower():
            suggestion = "Resolve merge conflicts first, or use git stash."
        elif "detached HEAD" in stderr:
            suggestion = "You're in detached HEAD state. Create a branch with git branch."
        return _err(f"git checkout failed: {stderr}", suggestion=suggestion)
    return _ok({"branch": ref})


async def _op_stash(args: dict, cwd: str | None) -> str:
    """Handle git stash (push, pop, list)."""
    action = args.get("action", "push")
    if action not in ("push", "pop", "list"):
        return _err(f"Unknown stash action: {action}. Use push, pop, or list.")
    ok, stdout, stderr = await _run_git(["stash", action], cwd=cwd)
    if not ok:
        return _err(f"git stash {action} failed: {stderr}")
    return _ok({"result": stdout.strip() or f"stash {action} successful"})


# ─── Dispatch Table ──────────────────────────────────────────────────────

_OPERATIONS: dict[str, object] = {
    "status": _op_status,
    "diff": _op_diff,
    "log": _op_log,
    "branch": _op_branch,
    "add": _op_add,
    "commit": _op_commit,
    "checkout": _op_checkout,
    "stash": _op_stash,
}

_SUPPORTED_OPS = ", ".join(sorted(_OPERATIONS.keys()))


# ─── Main Tool Function ─────────────────────────────────────────────────


async def git(args: dict) -> str:
    """Execute a git operation and return structured result."""
    operation = args.get("operation", "status")
    cwd = args.get("cwd")

    # Sandbox validation
    if cwd:
        allowed, reason = is_path_allowed(cwd)
        if not allowed:
            return _err(reason)

    # Permission check for write operations
    if operation in _WRITE_OPS:
        perm = check_permission("git")
        if not perm.allowed:
            return _err(f"Permission denied for git {operation}: {perm.reason}")

    # Validate git repo
    repo_err = await _validate_repo(cwd)
    if repo_err:
        return _err(repo_err, suggestion="Use 'cd' to navigate to a git repository.")

    handler = _OPERATIONS.get(operation)
    if handler is None:
        return _err(f"Unknown git operation: {operation}. Supported: {_SUPPORTED_OPS}.")

    try:
        return await handler(args, cwd)
    except Exception as e:
        log.error("Git operation '%s' failed: %s", operation, e)
        return _err(str(e))


# ─── Tool Spec ───────────────────────────────────────────────────────────

GIT_SPEC = {
    "type": "function",
    "function": {
        "name": "git",
        "description": (f"Execute git operations with structured output. Supports: {_SUPPORTED_OPS}."),
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": f"Git operation: {_SUPPORTED_OPS}",
                    "enum": sorted(_OPERATIONS.keys()),
                },
                "path": {"type": "string", "description": "File path for diff operation"},
                "ref": {"type": "string", "description": "Git ref (branch, tag, commit) for diff/checkout"},
                "limit": {
                    "type": "integer",
                    "description": f"Number of commits for log (default: {_DEFAULT_LOG_LIMIT})",
                },
                "message": {"type": "string", "description": "Commit message for commit operation"},
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths for add operation",
                },
                "create": {"type": "string", "description": "Branch name to create"},
                "delete": {"type": "string", "description": "Branch name to delete"},
                "action": {"type": "string", "description": "Stash action: push, pop, list"},
                "cwd": {"type": "string", "description": "Working directory (default: current)"},
            },
            "required": ["operation"],
        },
    },
}

TOOLS = [
    (GIT_SPEC, "git"),
]
