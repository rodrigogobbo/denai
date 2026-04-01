"""Project analysis — /init scans the working directory and generates context."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .config import DATA_DIR
from .logging_config import get_logger

log = get_logger("project")

PROJECTS_DIR = DATA_DIR / "projects"
CONTEXT_STALE_DAYS = 7

# Known project indicators
_INDICATORS: dict[str, dict[str, str]] = {
    "package.json": {"lang": "JavaScript/TypeScript", "ecosystem": "Node.js"},
    "tsconfig.json": {"lang": "TypeScript", "ecosystem": "Node.js"},
    "pyproject.toml": {"lang": "Python", "ecosystem": "PyPI"},
    "setup.py": {"lang": "Python", "ecosystem": "PyPI"},
    "requirements.txt": {"lang": "Python", "ecosystem": "pip"},
    "Cargo.toml": {"lang": "Rust", "ecosystem": "Cargo"},
    "go.mod": {"lang": "Go", "ecosystem": "Go Modules"},
    "pom.xml": {"lang": "Java", "ecosystem": "Maven"},
    "build.gradle": {"lang": "Java/Kotlin", "ecosystem": "Gradle"},
    "build.gradle.kts": {"lang": "Kotlin", "ecosystem": "Gradle"},
    "Gemfile": {"lang": "Ruby", "ecosystem": "Bundler"},
    "composer.json": {"lang": "PHP", "ecosystem": "Composer"},
    "mix.exs": {"lang": "Elixir", "ecosystem": "Mix"},
    "pubspec.yaml": {"lang": "Dart", "ecosystem": "Pub"},
    "CMakeLists.txt": {"lang": "C/C++", "ecosystem": "CMake"},
    "Makefile": {"lang": "C/C++", "ecosystem": "Make"},
    "*.csproj": {"lang": "C#", "ecosystem": ".NET"},
    "*.sln": {"lang": "C#", "ecosystem": ".NET"},
}

_FRAMEWORK_HINTS: dict[str, str] = {
    "next.config": "Next.js",
    "nuxt.config": "Nuxt.js",
    "vite.config": "Vite",
    "webpack.config": "Webpack",
    "angular.json": "Angular",
    "svelte.config": "SvelteKit",
    "astro.config": "Astro",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "Dockerfile": "Docker",
    "docker-compose": "Docker Compose",
    ".github/workflows": "GitHub Actions CI",
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
    ".circleci": "CircleCI",
    "terraform": "Terraform",
    "helm": "Helm",
    "k8s": "Kubernetes",
}

_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    "coverage",
    ".idea",
    ".vscode",
    "vendor",
    ".terraform",
    ".eggs",
    "*.egg-info",
}

_KEY_FILES = {
    "README.md",
    "README.rst",
    "README.txt",
    "README",
    "LICENSE",
    "LICENSE.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".gitignore",
    ".env.example",
    ".editorconfig",
    "Makefile",
    "justfile",
    "Taskfile.yml",
}


@dataclass
class ProjectInfo:
    """Result of project analysis."""

    path: str = ""
    name: str = ""
    languages: list[str] = field(default_factory=list)
    ecosystems: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    key_files: list[str] = field(default_factory=list)
    tree: str = ""
    file_count: int = 0
    dir_count: int = 0
    description: str = ""
    git_info: dict[str, str] = field(default_factory=dict)

    def to_context(self) -> str:
        """Generate a context block for the LLM system prompt."""
        parts = [f"## Projeto: {self.name}"]
        parts.append(f"**Caminho:** `{self.path}`")

        if self.languages:
            parts.append(f"**Linguagens:** {', '.join(self.languages)}")
        if self.ecosystems:
            parts.append(f"**Ecossistema:** {', '.join(self.ecosystems)}")
        if self.frameworks:
            parts.append(f"**Frameworks/Tools:** {', '.join(self.frameworks)}")
        if self.git_info:
            branch = self.git_info.get("branch", "")
            remote = self.git_info.get("remote", "")
            if branch:
                parts.append(f"**Git branch:** {branch}")
            if remote:
                parts.append(f"**Git remote:** {remote}")
        if self.description:
            parts.append(f"**Descrição:** {self.description}")

        parts.append(f"**Estrutura:** {self.file_count} arquivos, {self.dir_count} diretórios")

        if self.key_files:
            parts.append("**Arquivos-chave:** " + ", ".join(f"`{f}`" for f in self.key_files[:10]))

        if self.tree:
            parts.append(f"\n```\n{self.tree}\n```")

        return "\n".join(parts)


# ─── Extracted analysis helpers ──────────────────────────────────────────


def _detect_languages(root: Path) -> tuple[set[str], set[str]]:
    """Detect languages and ecosystems from indicator files.

    Returns (languages, ecosystems) sets.
    """
    langs: set[str] = set()
    ecos: set[str] = set()
    for indicator, meta in _INDICATORS.items():
        if indicator.startswith("*"):
            if list(root.glob(indicator)):
                langs.add(meta["lang"])
                ecos.add(meta["ecosystem"])
        elif (root / indicator).exists():
            langs.add(meta["lang"])
            ecos.add(meta["ecosystem"])
    return langs, ecos


def _detect_frameworks(root: Path) -> set[str]:
    """Detect frameworks/tools from hint files (root + one level deep)."""
    frameworks: set[str] = set()

    for hint, framework in _FRAMEWORK_HINTS.items():
        # Check if any file in root matches the hint
        for f in root.iterdir():
            if hint in f.name:
                frameworks.add(framework)
                break
        # Check exact path (for nested hints like .github/workflows)
        hint_path = root / hint
        if hint_path.exists() or hint_path.is_dir():
            frameworks.add(framework)

    # Check nested framework hints (shallow — one level deep)
    for child in root.iterdir():
        if child.is_dir() and child.name not in _IGNORED_DIRS:
            for hint, framework in _FRAMEWORK_HINTS.items():
                if "/" not in hint and (child / hint).exists():
                    frameworks.add(framework)

    return frameworks


def _detect_key_files(root: Path) -> list[str]:
    """Find key project files (README, LICENSE, Dockerfile, etc.)."""
    return sorted(f.name for f in root.iterdir() if f.name in _KEY_FILES)


def _read_description(root: Path) -> str:
    """Extract a one-line description from the project README."""
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme_path = root / readme_name
        if readme_path.is_file():
            try:
                text = readme_path.read_text(encoding="utf-8", errors="ignore")[:500]
                for line in text.split("\n"):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith("="):
                        return stripped[:200]
            except Exception:
                pass
            break
    return ""


def _read_git_info(root: Path) -> dict[str, str]:
    """Read git branch and remote from .git directory (no subprocess)."""
    git_dir = root / ".git"
    info: dict[str, str] = {}
    if not git_dir.is_dir():
        return info

    try:
        head_file = git_dir / "HEAD"
        if head_file.is_file():
            head = head_file.read_text(encoding="utf-8").strip()
            if head.startswith("ref: refs/heads/"):
                info["branch"] = head.replace("ref: refs/heads/", "")
    except Exception:
        pass

    try:
        config_file = git_dir / "config"
        if config_file.is_file():
            content = config_file.read_text(encoding="utf-8", errors="ignore")
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("url = "):
                    info["remote"] = stripped[6:]
                    break
    except Exception:
        pass

    return info


def _count_entries(root: Path, max_depth: int = 3) -> tuple[int, int]:
    """Count files and directories (respecting depth limit and ignoring noise).

    Returns (file_count, dir_count).
    """
    file_count = 0
    dir_count = 0
    for entry in _walk_shallow(root, max_depth=max_depth):
        if entry.is_file():
            file_count += 1
        elif entry.is_dir():
            dir_count += 1
    return file_count, dir_count


# ─── Main analysis function ─────────────────────────────────────────────


def analyze_project(path: str | Path | None = None) -> ProjectInfo:
    """Analyze a project directory and return structured info."""
    # Resolve and normalize path to prevent path traversal (taint sanitization)
    root = Path(path).expanduser().resolve() if path is not None else Path.cwd().resolve()

    if not root.is_dir():
        return ProjectInfo(path=str(root), name=root.name)

    langs, ecos = _detect_languages(root)
    frameworks = _detect_frameworks(root)
    file_count, dir_count = _count_entries(root)

    return ProjectInfo(
        path=str(root),
        name=root.name,
        languages=sorted(langs),
        ecosystems=sorted(ecos),
        frameworks=sorted(frameworks),
        key_files=_detect_key_files(root),
        tree=_build_tree(root, max_depth=2),
        file_count=file_count,
        dir_count=dir_count,
        description=_read_description(root),
        git_info=_read_git_info(root),
    )


def _build_tree(root: Path, max_depth: int = 2, prefix: str = "") -> str:
    """Build a simple directory tree string."""
    lines: list[str] = []
    if not prefix:
        lines.append(root.name + "/")

    try:
        entries = sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return "\n".join(lines)

    # Filter ignored dirs and hidden files
    entries = [
        e
        for e in entries
        if (e.name not in _IGNORED_DIRS and not e.name.startswith("."))
        or e.name in (".github", ".gitignore", ".env.example")
    ]

    # Limit entries per level
    max_entries = 25
    truncated = len(entries) > max_entries
    entries = entries[:max_entries]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1 and not truncated
        connector = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            if max_depth > 1:
                subtree = _build_tree(entry, max_depth - 1, child_prefix)
                if subtree:
                    lines.append(subtree)
        else:
            lines.append(f"{prefix}{connector}{entry.name}")

    if truncated:
        lines.append(f"{prefix}└── ... ({len(list(root.iterdir())) - max_entries} more)")

    return "\n".join(lines)


def _walk_shallow(root: Path, max_depth: int = 3, _current: int = 0):
    """Walk directory tree with depth limit."""
    if _current >= max_depth:
        return
    try:
        for entry in root.iterdir():
            if entry.name in _IGNORED_DIRS or entry.name.startswith("."):
                continue
            yield entry
            if entry.is_dir():
                yield from _walk_shallow(entry, max_depth, _current + 1)
    except PermissionError:
        pass


# ─── Persistent Context ──────────────────────────────────────────────────


def _project_hash(project_path: str) -> str:
    """Generate a short hash from the absolute project path.

    Uses normpath instead of resolve to avoid following symlinks
    into sensitive directories (CodeQL py/path-injection).
    """
    abs_path = os.path.normpath(os.path.abspath(project_path))  # noqa: PTH100
    return hashlib.sha256(abs_path.encode()).hexdigest()[:12]


def _context_file_for(project_path: str) -> Path:
    """Return the context.yaml path for a given project path."""
    return PROJECTS_DIR / _project_hash(project_path) / "context.yaml"


def save_context(info: ProjectInfo) -> Path:
    """Persist project analysis result to ~/.denai/projects/<hash>/context.yaml."""
    ctx_file = _context_file_for(info.path)
    ctx_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "project_name": info.name,
        "project_hash": _project_hash(info.path),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "project_path": info.path,
        "languages": info.languages,
        "ecosystems": info.ecosystems,
        "frameworks": info.frameworks,
        "git_remote": info.git_info.get("remote", ""),
        "git_branch": info.git_info.get("branch", ""),
        "file_count": info.file_count,
        "dir_count": info.dir_count,
        "description": info.description,
        "key_files": info.key_files,
        "tree_depth_2": info.tree,
    }

    ctx_file.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    log.info("Project context saved to %s", ctx_file)
    return ctx_file


def load_context(project_path: str | None = None) -> dict | None:
    """Load persisted project context for the given path. Returns None if not found/corrupt."""
    path = project_path or str(Path.cwd())
    ctx_file = _context_file_for(path)

    if not ctx_file.is_file():
        return None

    try:
        data = yaml.safe_load(ctx_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            log.warning("Corrupted context file (not a dict): %s", ctx_file)
            return None
        return data
    except Exception as e:
        log.warning("Failed to read context file %s: %s", ctx_file, e)
        return None


def is_context_stale(context: dict, max_days: int = CONTEXT_STALE_DAYS) -> bool:
    """Check if context is older than max_days."""
    analyzed_at = context.get("analyzed_at", "")
    if not analyzed_at:
        return True
    try:
        ts = datetime.fromisoformat(analyzed_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - ts
        return age.days > max_days
    except (ValueError, TypeError):
        return True


def context_to_prompt(context: dict) -> str:
    """Format project context as a concise section for the system prompt."""
    parts = [f"## Projeto: {context.get('project_name', 'Unknown')}"]
    parts.append(f"**Caminho:** `{context.get('project_path', '')}`")

    langs = context.get("languages", [])
    if langs:
        parts.append(f"**Linguagens:** {', '.join(langs)}")

    frameworks = context.get("frameworks", [])
    if frameworks:
        parts.append(f"**Frameworks:** {', '.join(frameworks)}")

    git_remote = context.get("git_remote", "")
    git_branch = context.get("git_branch", "")
    if git_branch:
        parts.append(f"**Git branch:** {git_branch}")
    if git_remote:
        parts.append(f"**Git remote:** {git_remote}")

    desc = context.get("description", "")
    if desc:
        parts.append(f"**Descrição:** {desc}")

    fc = context.get("file_count", 0)
    dc = context.get("dir_count", 0)
    parts.append(f"**Estrutura:** {fc} arquivos, {dc} diretórios")

    tree = context.get("tree_depth_2", "")
    if tree:
        parts.append(f"\n```\n{tree}\n```")

    if is_context_stale(context):
        analyzed_at = context.get("analyzed_at", "")
        try:
            ts = datetime.fromisoformat(analyzed_at)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - ts).days
            parts.append(f"\n⚠️ Contexto do projeto tem {age_days} dias. Execute `/init` para atualizar.")
        except (ValueError, TypeError):
            parts.append("\n⚠️ Contexto do projeto pode estar desatualizado. Execute `/init` para atualizar.")

    return "\n".join(parts)
