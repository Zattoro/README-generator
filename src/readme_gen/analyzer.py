"""Repository structure analysis and tech stack detection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import PROJECT_TYPE_FOLDERS, RepoContext, TECH_STACK_FILES


class RepoAnalyzer:
    """Scans a local directory and extracts metadata for README generation."""

    # Common entry-point filenames per language
    ENTRY_POINTS = {
        "python": ["main.py", "app.py", "cli.py", "run.py", "__main__.py"],
        "node": ["index.js", "index.ts", "app.js", "server.js", "main.ts"],
        "go": ["main.go"],
        "rust": ["main.rs", "lib.rs"],
        "java": ["Main.java", "Application.java"],
    }

    def __init__(self, path: str | Path, max_depth: int = 3) -> None:
        self.path = Path(path).resolve()
        self.max_depth = max_depth

    def analyze(self) -> RepoContext:
        """Run full analysis and return a populated :class:`RepoContext`."""

        if not self.path.exists():
            raise FileNotFoundError(f"Path not found: {self.path}")

        context = RepoContext(path=str(self.path), name=self.path.name)

        # Detect language from files
        files = self._list_files()
        context.languages = self._detect_languages(files)
        context.language = context.languages[0] if context.languages else ""

        # Detect tech stack from manifest files
        context.tech_stack = self._detect_tech_stack(files)

        # Detect project type from folders
        context.project_type = self._detect_project_type()

        # Feature flags
        context.has_tests = self._has_folder("tests", "test", "__tests__")
        context.has_docs = self._has_folder("docs", "documentation")
        context.has_docker = any(
            f.name.lower() in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}
            for f in files
        )
        context.has_ci = self._has_folder(".github/workflows", ".gitlab-ci")

        # Entry points
        context.entry_points = self._find_entry_points(files)

        # Key files content (truncated)
        context.key_files = self._read_key_files(files)

        # File tree for LLM context
        context.file_tree = self._build_file_tree()

        # Existing README / License
        context.readme_exists = any(
            f.name.lower() == "readme.md" for f in files
        )
        context.license = self._detect_license(files)

        return context

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _list_files(self) -> list[Path]:
        """List all files under self.path, respecting max_depth."""

        result: list[Path] = []
        root = self.path

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune hidden directories and common noise
            dirnames[:] = [
                d
                for d in dirnames
                if not d.startswith(".")
                and d not in {"node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build", "target"}
            ]

            # Respect max_depth
            depth = Path(dirpath).relative_to(root).parts
            if len(depth) >= self.max_depth:
                dirnames[:] = []

            for fname in filenames:
                if fname.startswith("."):
                    continue
                result.append(Path(dirpath) / fname)

        return result

    def _detect_languages(self, files: list[Path]) -> list[str]:
        """Return sorted list of detected programming languages."""

        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".kt": "Kotlin",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".c": "C",
            ".h": "C / C++",
            ".hpp": "C++",
            ".swift": "Swift",
            ".dart": "Dart",
            ".r": "R",
            ".m": "Objective-C",
            ".mm": "Objective-C++",
            ".scala": "Scala",
            ".clj": "Clojure",
            ".ex": "Elixir",
            ".exs": "Elixir",
            ".hs": "Haskell",
            ".ml": "OCaml",
            ".fs": "F#",
            ".lua": "Lua",
            ".sh": "Shell",
            ".ps1": "PowerShell",
            ".sql": "SQL",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".less": "Less",
            ".vue": "Vue",
            ".svelte": "Svelte",
            ".ipynb": "Jupyter Notebook",
        }

        langs: set[str] = set()
        for f in files:
            ext = f.suffix.lower()
            if ext in ext_map:
                langs.add(ext_map[ext])

        return sorted(langs)

    def _detect_tech_stack(self, files: list[Path]) -> list[str]:
        """Match manifest filenames to known tech stack labels."""

        stack: set[str] = set()
        names = {f.name for f in files}

        for filename, label in TECH_STACK_FILES.items():
            # Handle directory markers (end with /)
            if filename.endswith("/"):
                dir_name = filename.rstrip("/")
                if any(f.is_relative_to(self.path / dir_name) for f in files if f.is_dir()):
                    stack.add(label)
            elif filename in names:
                stack.add(label)

        return sorted(stack)

    def _detect_project_type(self) -> str:
        """Heuristic project-type detection from top-level folders."""

        top_dirs = {p.name for p in self.path.iterdir() if p.is_dir() and not p.name.startswith(".")}

        if "src" in top_dirs and ("tests" in top_dirs or "test" in top_dirs):
            return "library / package"
        if "app" in top_dirs or "cmd" in top_dirs:
            return "application"
        if "notebooks" in top_dirs:
            return "data science / notebooks"
        if "infra" in top_dirs or "deploy" in top_dirs:
            return "infrastructure / devops"
        if "examples" in top_dirs:
            return "example / demo project"
        return "general"

    def _has_folder(self, *names: str) -> bool:
        return any((self.path / name).exists() for name in names)

    def _find_entry_points(self, files: list[Path]) -> list[str]:
        """Find likely entry-point files based on language."""

        entry_points: list[str] = []
        for f in files:
            name = f.name.lower()
            for lang, candidates in self.ENTRY_POINTS.items():
                if name in candidates and any(
                    l.lower().startswith(lang[:3]) for l in self._detect_languages([f])
                ):
                    entry_points.append(str(f.relative_to(self.path)))
        return sorted(set(entry_points))

    def _read_key_files(self, files: list[Path]) -> dict[str, str]:
        """Read small manifest files and return name -> truncated content."""

        key_names = {
            "package.json", "requirements.txt", "pyproject.toml",
            "setup.py", "Cargo.toml", "go.mod", "pom.xml",
            "build.gradle", "composer.json", "Gemfile",
            "Dockerfile", "docker-compose.yml",
        }

        contents: dict[str, str] = {}
        for f in files:
            if f.name in key_names:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    # Truncate to keep LLM prompt small
                    contents[f.name] = text[:2000]
                except Exception:  # pragma: no cover - best effort
                    contents[f.name] = ""
        return contents

    def _build_file_tree(self) -> str:
        """Produce a compact ASCII tree string for the LLM."""

        lines: list[str] = []

        def walk(dir_path: Path, prefix: str = "", depth: int = 0) -> None:
            if depth >= self.max_depth:
                return
            try:
                entries = sorted(
                    dir_path.iterdir(),
                    key=lambda p: (p.is_file(), p.name.lower()),
                )
            except PermissionError:
                return

            # Filter noise
            entries = [
                e
                for e in entries
                if not e.name.startswith(".")
                and e.name not in {"node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build", "target"}
            ]

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")
                if entry.is_dir():
                    extension = "    " if is_last else "│   "
                    walk(entry, prefix + extension, depth + 1)

        lines.append(self.path.name)
        walk(self.path)
        return "\n".join(lines)

    def _detect_license(self, files: list[Path]) -> str:
        """Try to read LICENSE file header."""

        for f in files:
            if f.name.upper() in {"LICENSE", "LICENCE", "LICENSE.txt", "LICENCE.txt"}:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    # Return first non-empty line
                    for line in text.splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            return line[:100]
                    return text[:100]
                except Exception:
                    return ""
        return ""