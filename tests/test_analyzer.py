"""Unit tests for RepoAnalyzer."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from readme_gen.analyzer import RepoAnalyzer


def _make_tree(root: Path, structure: dict) -> None:
    """Create files/folders from a nested dict."""
    for name, content in structure.items():
        path = root / name
        if isinstance(content, dict):
            path.mkdir(parents=True, exist_ok=True)
            _make_tree(path, content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content or "", encoding="utf-8")


def test_analyzer_basic_structure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(
            root,
            {
                "README.md": "# Hello",
                "requirements.txt": "requests\nflask\n",
                "main.py": "print('hi')\n",
                "src": {
                    "__init__.py": "",
                    "core.py": "def run(): pass\n",
                },
                "tests": {
                    "test_core.py": "def test_run(): assert True\n",
                },
                "docs": {
                    "usage.md": "## Usage\n",
                },
                ".github": {
                    "workflows": {
                        "ci.yml": "name: CI\n",
                    }
                },
            },
        )

        analyzer = RepoAnalyzer(root, max_depth=3)
        context = analyzer.analyze()

        assert context.name == root.name
        assert "Python" in context.languages
        assert context.has_tests is True
        assert context.has_docs is True
        assert context.has_ci is True
        assert context.readme_exists is True
        assert "main.py" in context.entry_points


def test_analyzer_docker_detection() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, {"Dockerfile": "FROM python:3.11\n", "app.py": "print(1)\n"})

        analyzer = RepoAnalyzer(root)
        context = analyzer.analyze()

        assert context.has_docker is True
        assert "Docker" in context.tech_stack


def test_analyzer_missing_path() -> None:
    analyzer = RepoAnalyzer(Path("/nonexistent/path/12345"))
    try:
        analyzer.analyze()
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_repo_context_to_dict() -> None:
    from readme_gen.config import RepoContext

    ctx = RepoContext(path="/tmp/x", name="test-repo", language="Python")
    data = ctx.to_dict()
    assert data["name"] == "test-repo"
    assert data["language"] == "Python"
    assert isinstance(data["tech_stack"], list)