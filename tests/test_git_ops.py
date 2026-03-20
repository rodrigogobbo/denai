"""Tests for git operations tool."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from denai.tools.git_ops import (
    GIT_SPEC,
    _parse_branches,
    _parse_diff,
    _parse_log,
    _parse_status,
    _run_git,
    _validate_repo,
    git,
)


def _git_init(path):
    """Init a git repo at path (test helper)."""
    subprocess.run(  # noqa: S603
        ["git", "init", str(path)],  # noqa: S607
        capture_output=True,
    )


def _git_run(args, cwd):
    """Run a git command in cwd (test helper)."""
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=str(cwd),
        capture_output=True,
    )


# ─── Parser tests ────────────────────────────────────────────────────────


class TestParseStatus:
    """Test git status parsing."""

    def test_empty_output(self):
        result = _parse_status("")
        assert result["branch"] == ""
        assert result["staged"] == []
        assert result["unstaged"] == []
        assert result["untracked"] == []

    def test_branch_head(self):
        output = "# branch.head main\n"
        result = _parse_status(output)
        assert result["branch"] == "main"

    def test_branch_ab(self):
        output = "# branch.head feat\n# branch.ab +3 -1\n"
        result = _parse_status(output)
        assert result["ahead"] == 3
        assert result["behind"] == 1

    def test_staged_file(self):
        output = "1 M. N... 100644 100644 100644 abc def src/main.py\n"
        result = _parse_status(output)
        assert "src/main.py" in result["staged"]
        assert result["unstaged"] == []

    def test_unstaged_file(self):
        output = "1 .M N... 100644 100644 100644 abc def src/main.py\n"
        result = _parse_status(output)
        assert result["staged"] == []
        assert "src/main.py" in result["unstaged"]

    def test_both_staged_and_unstaged(self):
        output = "1 MM N... 100644 100644 100644 abc def src/main.py\n"
        result = _parse_status(output)
        assert "src/main.py" in result["staged"]
        assert "src/main.py" in result["unstaged"]

    def test_untracked_file(self):
        output = "? new_file.txt\n"
        result = _parse_status(output)
        assert "new_file.txt" in result["untracked"]

    def test_full_status(self):
        output = (
            "# branch.head develop\n"
            "# branch.ab +2 -0\n"
            "1 A. N... 100644 100644 100644 abc def added.py\n"
            "1 .M N... 100644 100644 100644 abc def modified.py\n"
            "? untracked.txt\n"
        )
        result = _parse_status(output)
        assert result["branch"] == "develop"
        assert result["ahead"] == 2
        assert result["behind"] == 0
        assert "added.py" in result["staged"]
        assert "modified.py" in result["unstaged"]
        assert "untracked.txt" in result["untracked"]


class TestParseDiff:
    """Test git diff parsing."""

    def test_empty_diff(self):
        result = _parse_diff("")
        assert result["files"] == []

    def test_single_file_diff(self):
        output = (
            "diff --git a/src/main.py b/src/main.py\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,4 @@\n"
            " import os\n"
            "+import sys\n"
            " \n"
            " def main():\n"
        )
        result = _parse_diff(output)
        assert len(result["files"]) == 1
        f = result["files"][0]
        assert f["name"] == "src/main.py"
        assert f["added"] == 1
        assert f["removed"] == 0

    def test_multi_file_diff(self):
        output = "diff --git a/a.py b/a.py\n+line1\ndiff --git a/b.py b/b.py\n-line2\n+line3\n"
        result = _parse_diff(output)
        assert len(result["files"]) == 2
        assert result["files"][0]["name"] == "a.py"
        assert result["files"][0]["added"] == 1
        assert result["files"][1]["name"] == "b.py"
        assert result["files"][1]["added"] == 1
        assert result["files"][1]["removed"] == 1

    def test_patch_is_string(self):
        output = "diff --git a/f.py b/f.py\n+new line\n"
        result = _parse_diff(output)
        assert isinstance(result["files"][0]["patch"], str)


class TestParseLog:
    """Test git log parsing."""

    def test_empty_log(self):
        result = _parse_log("")
        assert result["commits"] == []

    def test_single_commit(self):
        output = "abc1234\tJohn Doe\t2025-01-15 10:30:00 -0300\tfeat: add feature\n"
        result = _parse_log(output)
        assert len(result["commits"]) == 1
        c = result["commits"][0]
        assert c["hash"] == "abc1234"
        assert c["author"] == "John Doe"
        assert c["message"] == "feat: add feature"

    def test_multiple_commits(self):
        output = "aaa\tAlice\t2025-01-15\tfirst\nbbb\tBob\t2025-01-14\tsecond\nccc\tCharlie\t2025-01-13\tthird\n"
        result = _parse_log(output)
        assert len(result["commits"]) == 3

    def test_skips_empty_lines(self):
        output = "aaa\tAlice\t2025-01-15\tfirst\n\nbbb\tBob\t2025-01-14\tsecond\n"
        result = _parse_log(output)
        assert len(result["commits"]) == 2


class TestParseBranches:
    """Test git branch parsing."""

    def test_empty(self):
        result = _parse_branches("")
        assert result["branches"] == []
        assert result["current"] == ""

    def test_single_branch(self):
        result = _parse_branches("* main\n")
        assert result["branches"] == ["main"]
        assert result["current"] == "main"

    def test_multiple_branches(self):
        output = "  develop\n  feat/test\n* main\n"
        result = _parse_branches(output)
        assert len(result["branches"]) == 3
        assert result["current"] == "main"


# ─── Helper tests ────────────────────────────────────────────────────────


class TestRunGit:
    """Test _run_git helper."""

    def test_success(self):
        ok, stdout, stderr = _run_git(["--version"])
        assert ok is True
        assert "git version" in stdout

    def test_invalid_command(self):
        ok, stdout, stderr = _run_git(["invalid-command-xyz"])
        assert ok is False

    def test_timeout(self):
        with patch(
            "denai.tools.git_ops.subprocess.run",
            side_effect=subprocess.TimeoutExpired("git", 30),
        ):
            ok, stdout, stderr = _run_git(["status"])
            assert ok is False
            assert "timed out" in stderr

    def test_git_not_found(self):
        with patch(
            "denai.tools.git_ops.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            ok, stdout, stderr = _run_git(["status"])
            assert ok is False
            assert "not installed" in stderr


class TestValidateRepo:
    """Test _validate_repo."""

    def test_valid_repo(self, tmp_path):
        _git_init(tmp_path)
        err = _validate_repo(str(tmp_path))
        assert err is None

    def test_invalid_repo(self, tmp_path):
        err = _validate_repo(str(tmp_path))
        assert err is not None
        assert "Not a git repository" in err


# ─── Main function tests ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGitFunction:
    """Test the main git() tool function."""

    @pytest.fixture(autouse=True)
    def _allow_sandbox(self):
        """Allow any path in sandbox for git tests."""
        with patch("denai.tools.git_ops.is_path_allowed", return_value=(True, "")):
            yield

    async def test_status_in_repo(self, tmp_path):
        _git_init(tmp_path)
        result = await git({"operation": "status", "cwd": str(tmp_path)})
        data = json.loads(result)
        assert "branch" in data

    async def test_not_a_repo(self, tmp_path):
        result = await git({"operation": "status", "cwd": str(tmp_path)})
        data = json.loads(result)
        assert "error" in data
        assert "Not a git repository" in data["error"]

    async def test_unknown_operation(self, tmp_path):
        _git_init(tmp_path)
        result = await git({"operation": "invalid_op", "cwd": str(tmp_path)})
        data = json.loads(result)
        assert "error" in data
        assert "Unknown git operation" in data["error"]

    async def test_diff_empty(self, tmp_path):
        _git_init(tmp_path)
        result = await git({"operation": "diff", "cwd": str(tmp_path)})
        data = json.loads(result)
        assert "files" in data
        assert data["files"] == []

    async def test_log_empty_repo(self, tmp_path):
        _git_init(tmp_path)
        result = await git({"operation": "log", "cwd": str(tmp_path)})
        data = json.loads(result)
        # Empty repo has no commits — should return error
        assert "error" in data or data.get("commits") == []

    async def test_branch_list(self, tmp_path):
        _git_init(tmp_path)
        # Create initial commit so branch exists
        (tmp_path / "file.txt").write_text("test")
        _git_run(["add", "."], tmp_path)
        _git_run(
            ["-c", "user.name=Test", "-c", "user.email=test@test.com", "commit", "-m", "init"],
            tmp_path,
        )
        result = await git({"operation": "branch", "cwd": str(tmp_path)})
        data = json.loads(result)
        assert "branches" in data
        assert len(data["branches"]) >= 1

    async def test_add_and_commit(self, tmp_path):
        _git_init(tmp_path)
        _git_run(
            ["-c", "user.name=Test", "-c", "user.email=t@t.com", "commit", "--allow-empty", "-m", "init"],
            tmp_path,
        )
        (tmp_path / "new.txt").write_text("hello")

        # Mock permission check to allow
        with patch("denai.tools.git_ops.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()

            # Add
            result = await git({"operation": "add", "paths": ["."], "cwd": str(tmp_path)})
            data = json.loads(result)
            assert "added" in data

            # Commit — need git user config
            _git_run(["config", "user.name", "Test"], tmp_path)
            _git_run(["config", "user.email", "test@test.com"], tmp_path)
            result = await git({"operation": "commit", "message": "test: add file", "cwd": str(tmp_path)})
            data = json.loads(result)
            assert "message" in data
            assert data["message"] == "test: add file"

    async def test_commit_requires_message(self, tmp_path):
        _git_init(tmp_path)
        with patch("denai.tools.git_ops.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
            result = await git({"operation": "commit", "message": "", "cwd": str(tmp_path)})
            data = json.loads(result)
            assert "error" in data
            assert "required" in data["error"]

    async def test_checkout_requires_ref(self, tmp_path):
        _git_init(tmp_path)
        with patch("denai.tools.git_ops.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
            result = await git({"operation": "checkout", "ref": "", "cwd": str(tmp_path)})
            data = json.loads(result)
            assert "error" in data
            assert "required" in data["error"]

    async def test_stash_unknown_action(self, tmp_path):
        _git_init(tmp_path)
        with patch("denai.tools.git_ops.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
            result = await git({"operation": "stash", "action": "nope", "cwd": str(tmp_path)})
            data = json.loads(result)
            assert "error" in data
            assert "Unknown stash action" in data["error"]

    async def test_write_op_permission_denied(self, tmp_path):
        _git_init(tmp_path)
        with patch("denai.tools.git_ops.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": False, "level": "deny", "reason": "blocked"})()
            result = await git({"operation": "add", "cwd": str(tmp_path)})
            data = json.loads(result)
            assert "error" in data
            assert "Permission denied" in data["error"]

    async def test_sandbox_violation(self):
        with patch(
            "denai.tools.git_ops.is_path_allowed",
            return_value=(False, "Path not allowed"),
        ):
            result = await git({"operation": "status", "cwd": "/etc"})
            data = json.loads(result)
            assert "error" in data
            assert "not allowed" in data["error"].lower()

    async def test_default_operation_is_status(self, tmp_path):
        _git_init(tmp_path)
        result = await git({"cwd": str(tmp_path)})
        data = json.loads(result)
        assert "branch" in data

    async def test_add_string_path(self, tmp_path):
        """Test that paths as string gets converted to list."""
        _git_init(tmp_path)
        (tmp_path / "file.txt").write_text("x")

        with patch("denai.tools.git_ops.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
            result = await git({"operation": "add", "paths": "file.txt", "cwd": str(tmp_path)})
            data = json.loads(result)
            assert "added" in data
            assert data["added"] == ["file.txt"]


# ─── Spec tests ──────────────────────────────────────────────────────────


class TestGitSpec:
    """Test GIT_SPEC structure."""

    def test_spec_structure(self):
        assert GIT_SPEC["type"] == "function"
        func = GIT_SPEC["function"]
        assert func["name"] == "git"
        assert "description" in func
        params = func["parameters"]
        assert params["required"] == ["operation"]
        assert "operation" in params["properties"]

    def test_spec_has_all_operations(self):
        ops = GIT_SPEC["function"]["parameters"]["properties"]["operation"]["enum"]
        expected = [
            "status",
            "diff",
            "log",
            "branch",
            "add",
            "commit",
            "checkout",
            "stash",
        ]
        assert ops == expected
