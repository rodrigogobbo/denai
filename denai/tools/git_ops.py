"""Git operations tool — structured wrappers for git CLI."""

from __future__ import annotations

import subprocess

from ..logging_config import get_logger
from ..permissions import check_permission
from ..security.sandbox import is_path_allowed

log = get_logger("git_ops")

# ─── Read Operations ──────────────────────────────────────────────────────

_WRITE_OPS = {"add", "commit", "checkout", "stash"}


def _run_git(args: list[str], cwd: str | None = None) -> tuple[bool, str, str]:
    """Run a git command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Git command timed out after 30 seconds"
    except FileNotFoundError:
        return False, "", "Git is not installed or not in PATH"


def _validate_repo(cwd: str | None = None) -> str | None:
    """Check if cwd is inside a git repo. Returns error message or None."""
    ok, _, _ = _run_git(["rev-parse", "--git-dir"], cwd=cwd)
    if not ok:
        return "Not a git repository. Navigate to a git repo first."
    return None


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


# ─── Main Tool Function ──────────────────────────────────────────────────


async def git(args: dict) -> str:
    """Execute a git operation and return structured result."""
    import json

    operation = args.get("operation", "status")
    cwd = args.get("cwd")

    # Sandbox validation
    if cwd:
        allowed, reason = is_path_allowed(cwd)
        if not allowed:
            return json.dumps({"error": reason})

    # Permission check for write operations
    if operation in _WRITE_OPS:
        perm = check_permission("git")
        if not perm.allowed:
            return json.dumps({"error": f"Permission denied for git {operation}: {perm.reason}"})

    # Validate git repo
    repo_err = _validate_repo(cwd)
    if repo_err:
        return json.dumps({"error": repo_err, "suggestion": "Use 'cd' to navigate to a git repository."})

    try:
        if operation == "status":
            ok, stdout, stderr = _run_git(["status", "--porcelain=v2", "--branch"], cwd=cwd)
            if not ok:
                return json.dumps({"error": f"git status failed: {stderr}"})
            return json.dumps(_parse_status(stdout))

        elif operation == "diff":
            cmd = ["diff"]
            if args.get("ref"):
                cmd.append(args["ref"])
            if args.get("path"):
                cmd.extend(["--", args["path"]])
            ok, stdout, stderr = _run_git(cmd, cwd=cwd)
            if not ok:
                return json.dumps({"error": f"git diff failed: {stderr}"})
            return json.dumps(_parse_diff(stdout))

        elif operation == "log":
            limit = args.get("limit", 10)
            ok, stdout, stderr = _run_git(
                ["log", f"-{limit}", "--format=%H\t%an\t%ai\t%s"],
                cwd=cwd,
            )
            if not ok:
                return json.dumps(
                    {
                        "error": f"git log failed: {stderr}",
                        "suggestion": "Ensure there are commits in the repository.",
                    }
                )
            return json.dumps(_parse_log(stdout))

        elif operation == "branch":
            if args.get("create"):
                ok, stdout, stderr = _run_git(["checkout", "-b", args["create"]], cwd=cwd)
                if not ok:
                    return json.dumps({"error": f"Failed to create branch: {stderr}"})
                return json.dumps({"created": args["create"], "current": args["create"]})
            elif args.get("delete"):
                ok, stdout, stderr = _run_git(["branch", "-d", args["delete"]], cwd=cwd)
                if not ok:
                    return json.dumps({"error": f"Failed to delete branch: {stderr}"})
                return json.dumps({"deleted": args["delete"]})
            else:
                ok, stdout, stderr = _run_git(["branch"], cwd=cwd)
                if not ok:
                    return json.dumps({"error": f"git branch failed: {stderr}"})
                return json.dumps(_parse_branches(stdout))

        elif operation == "add":
            paths = args.get("paths", ["."])
            if isinstance(paths, str):
                paths = [paths]
            ok, stdout, stderr = _run_git(["add", *paths], cwd=cwd)
            if not ok:
                return json.dumps({"error": f"git add failed: {stderr}"})
            return json.dumps({"added": paths})

        elif operation == "commit":
            message = args.get("message", "")
            if not message:
                return json.dumps({"error": "Commit message is required."})
            ok, stdout, stderr = _run_git(["commit", "-m", message], cwd=cwd)
            if not ok:
                if "nothing to commit" in stderr or "nothing to commit" in stdout:
                    return json.dumps({"error": "Nothing to commit.", "suggestion": "Stage files with git add first."})
                return json.dumps({"error": f"git commit failed: {stderr}"})
            # Parse commit hash from output
            commit_hash = ""
            for line in stdout.splitlines():
                if line.strip().startswith("["):
                    parts = line.split()
                    for p in parts:
                        if len(p) >= 7 and p.endswith("]"):
                            commit_hash = p.rstrip("]")
                            break
            return json.dumps({"hash": commit_hash, "message": message})

        elif operation == "checkout":
            ref = args.get("ref", "")
            if not ref:
                return json.dumps({"error": "Ref (branch name or commit) is required."})
            ok, stdout, stderr = _run_git(["checkout", ref], cwd=cwd)
            if not ok:
                suggestion = ""
                if "conflict" in stderr.lower():
                    suggestion = "Resolve merge conflicts first, or use git stash."
                elif "detached HEAD" in stderr:
                    suggestion = "You're in detached HEAD state. Create a branch with git branch."
                return json.dumps({"error": f"git checkout failed: {stderr}", "suggestion": suggestion})
            return json.dumps({"branch": ref})

        elif operation == "stash":
            action = args.get("action", "push")
            if action == "push":
                ok, stdout, stderr = _run_git(["stash", "push"], cwd=cwd)
            elif action == "pop":
                ok, stdout, stderr = _run_git(["stash", "pop"], cwd=cwd)
            elif action == "list":
                ok, stdout, stderr = _run_git(["stash", "list"], cwd=cwd)
            else:
                return json.dumps({"error": f"Unknown stash action: {action}. Use push, pop, or list."})
            if not ok:
                return json.dumps({"error": f"git stash {action} failed: {stderr}"})
            return json.dumps({"result": stdout.strip() or f"stash {action} successful"})

        else:
            supported = "status, diff, log, branch, add, commit, checkout, stash"
            return json.dumps({"error": f"Unknown git operation: {operation}. Supported: {supported}."})

    except Exception as e:
        log.error("Git operation '%s' failed: %s", operation, e)
        return json.dumps({"error": str(e)})


# ─── Tool Spec ────────────────────────────────────────────────────────────

GIT_SPEC = {
    "type": "function",
    "function": {
        "name": "git",
        "description": (
            "Execute git operations with structured output. "
            "Supports: status, diff, log, branch, add, commit, checkout, stash."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Git operation: status, diff, log, branch, add, commit, checkout, stash",
                    "enum": ["status", "diff", "log", "branch", "add", "commit", "checkout", "stash"],
                },
                "path": {"type": "string", "description": "File path for diff operation"},
                "ref": {"type": "string", "description": "Git ref (branch, tag, commit) for diff/checkout"},
                "limit": {"type": "integer", "description": "Number of commits for log (default: 10)"},
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
