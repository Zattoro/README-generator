"""Configuration and environment loading."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional at import time
    load_dotenv = None  # type: ignore


# Files that hint at the tech stack
TECH_STACK_FILES: Dict[str, str] = {
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "setup.cfg": "Python",
    "Pipfile": "Python",
    "package.json": "Node.js / JavaScript",
    "package-lock.json": "Node.js / JavaScript",
    "yarn.lock": "Node.js / JavaScript",
    "pnpm-lock.yaml": "Node.js / JavaScript",
    "Cargo.toml": "Rust",
    "Cargo.lock": "Rust",
    "go.mod": "Go",
    "go.sum": "Go",
    "pom.xml": "Java / Maven",
    "build.gradle": "Java / Gradle",
    "build.gradle.kts": "Kotlin / Gradle",
    "composer.json": "PHP",
    "Gemfile": "Ruby",
    "mix.exs": "Elixir",
    "mix.lock": "Elixir",
    "CMakeLists.txt": "C++",
    "meson.build": "C / C++ / Rust",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    ".github/workflows/": "GitHub Actions",
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
}

# Folders that suggest project type
PROJECT_TYPE_FOLDERS: Dict[str, str] = {
    "src": "source code",
    "lib": "library",
    "app": "application",
    "cmd": "Go command structure",
    "pkg": "Go package structure",
    "tests": "test suite",
    "test": "test suite",
    "docs": "documentation",
    "notebooks": "Jupyter notebooks",
    "examples": "usage examples",
    "scripts": "helper scripts",
    "infra": "infrastructure as code",
    "deploy": "deployment scripts",
}

# Supported LLM providers and their default models
PROVIDERS: Dict[str, Dict[str, str]] = {
    "openai": {
        "name": "OpenAI",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "default_base_url": "https://api.openai.com/v1",
        "family": "openai",
    },
    "anthropic": {
        "name": "Anthropic",
        "default_model": "claude-3-haiku-20240307",
        "env_key": "ANTHROPIC_API_KEY",
        "default_base_url": "https://api.anthropic.com",
        "family": "anthropic",
    },
    "ollama": {
        "name": "Ollama (локально, бесплатно)",
        "default_model": "llama3",
        "env_key": "",
        "default_base_url": "http://localhost:11434",
        "family": "ollama",
    },
    "openrouter": {
        "name": "OpenRouter (много моделей через 1 ключ)",
        "default_model": "openai/gpt-4o-mini",
        "env_key": "OPENROUTER_API_KEY",
        "default_base_url": "https://openrouter.ai/api/v1",
        "family": "openai",
    },
    "groq": {
        "name": "Groq (быстрый инференс)",
        "default_model": "llama-3.1-8b-instant",
        "env_key": "GROQ_API_KEY",
        "default_base_url": "https://api.groq.com/openai/v1",
        "family": "openai",
    },
    "mistral": {
        "name": "Mistral AI",
        "default_model": "mistral-small-latest",
        "env_key": "MISTRAL_API_KEY",
        "default_base_url": "https://api.mistral.ai/v1",
        "family": "openai",
    },
    "together": {
        "name": "Together AI",
        "default_model": "meta-llama/Llama-3-8b-chat-hf",
        "env_key": "TOGETHER_API_KEY",
        "default_base_url": "https://api.together.xyz/v1",
        "family": "openai",
    },
    "custom": {
        "name": "Свой OpenAI-совместимый API",
        "default_model": "custom-model",
        "env_key": "CUSTOM_API_KEY",
        "default_base_url": "",
        "family": "openai",
    },
}

# Ordered list for CLI menu display
PROVIDER_CHOICES: List[str] = list(PROVIDERS.keys())


@dataclass
class Settings:
    """Runtime settings loaded from environment variables."""

    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str = ""
    temperature: float = 0.3
    offline: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables (with .env fallback)."""

        if load_dotenv is not None:
            load_dotenv(override=False)

        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        api_key = os.getenv("LLM_API_KEY", "")
        # Fallback to provider-specific key if generic not set
        if not api_key and provider in PROVIDERS:
            env_key = PROVIDERS[provider]["env_key"]
            if env_key:
                api_key = os.getenv(env_key, "")
        model = os.getenv(
            "LLM_MODEL", PROVIDERS.get(provider, {}).get("default_model", "gpt-4o-mini")
        )
        base_url = os.getenv(
            "LLM_BASE_URL", PROVIDERS.get(provider, {}).get("default_base_url", "")
        )
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        offline = os.getenv("LLM_OFFLINE", "false").lower() in ("1", "true", "yes")

        return cls(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            offline=offline,
        )

    def save_to_env(self, path: Path = Path(".env")) -> None:
        """Persist current settings to a .env file."""

        provider_info = PROVIDERS.get(self.provider, {})
        lines = [
            "# Readme-generator-ai settings",
            f"LLM_PROVIDER={self.provider}",
            f"LLM_API_KEY={self.api_key}",
            f"LLM_MODEL={self.model}",
            f"LLM_BASE_URL={self.base_url}",
            f"LLM_TEMPERATURE={self.temperature}",
            f"LLM_OFFLINE={'true' if self.offline else 'false'}",
        ]
        if provider_info.get("env_key"):
            lines.insert(2, f"{provider_info['env_key']}={self.api_key}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@dataclass
class RepoContext:
    """Structured information about a repository."""

    path: str
    name: str
    description: str = ""
    language: str = ""
    languages: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    project_type: str = ""
    has_tests: bool = False
    has_docs: bool = False
    has_docker: bool = False
    has_ci: bool = False
    entry_points: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    file_tree: str = ""
    key_files: Dict[str, str] = field(default_factory=dict)
    readme_exists: bool = False
    license: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "languages": self.languages,
            "tech_stack": self.tech_stack,
            "project_type": self.project_type,
            "has_tests": self.has_tests,
            "has_docs": self.has_docs,
            "has_docker": self.has_docker,
            "has_ci": self.has_ci,
            "entry_points": self.entry_points,
            "dependencies": self.dependencies,
            "file_tree": self.file_tree,
            "key_files": self.key_files,
            "readme_exists": self.readme_exists,
            "license": self.license,
        }