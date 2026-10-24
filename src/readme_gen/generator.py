"""README generation via LLM or offline template."""

from __future__ import annotations

from typing import Any

from .config import PROVIDERS, RepoContext, Settings


class ReadmeGenerator:
    """Generates a README.md string from a :class:`RepoContext`.

    Supports multiple LLM providers (OpenAI, Anthropic, Ollama, OpenRouter,
    Groq, Mistral, Together, Custom OpenAI-compatible) and falls back to an
    offline template when no API key is available.
    """

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        offline: bool = False,
    ) -> None:
        settings = Settings.from_env()

        self.provider = (provider or settings.provider).lower()
        self.api_key = api_key or settings.api_key
        self.model = model or settings.model or PROVIDERS.get(
            self.provider, {}
        ).get("default_model", "gpt-4o-mini")
        self.base_url = base_url or settings.base_url or PROVIDERS.get(
            self.provider, {}
        ).get("default_base_url", "")
        self.temperature = (
            temperature if temperature is not None else settings.temperature
        )
        self.offline = offline or not bool(self.api_key)

        self._client: Any = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def generate(self, context: RepoContext) -> str:
        """Return a complete README.md string for *context*."""

        if self.offline:
            content = self._build_offline(context)
        else:
            prompt = self._build_prompt(context)
            content = self._call_llm(prompt)

        return self._post_process(content, context)

    # ------------------------------------------------------------------ #
    # Offline template generator
    # ------------------------------------------------------------------ #

    def _build_offline(self, context: RepoContext) -> str:
        """Build a complete README without calling any LLM."""

        lines: list[str] = []
        lines.append(f"# {context.name}")
        lines.append("")

        # Description
        if context.description:
            lines.append(context.description)
        else:
            lines.append(
                f"{context.name} is a {context.language or 'software'} project"
                + (
                    " built with " + ", ".join(context.tech_stack[:3])
                    if context.tech_stack
                    else ""
                )
                + "."
            )
        lines.append("")

        # Badges
        badge_parts: list[str] = []
        if context.language:
            badge_parts.append(
                f"![{context.language}](https://img.shields.io/badge/language-{context.language.replace(' ', '%20')}-blue)"
            )
        if context.license:
            badge_parts.append(
                f"![License](https://img.shields.io/badge/license-{context.license.replace(' ', '%20')}-green)"
            )
        badge_parts.append(
            "![Generated with AI](https://img.shields.io/badge/generated%20with-AI-purple)"
        )
        if badge_parts:
            lines.append(" ".join(badge_parts))
            lines.append("")

        # Features (inferred)
        lines.append("## Features")
        for f in self._infer_features(context):
            lines.append(f"- {f}")
        lines.append("")

        # Tech Stack
        lines.append("## Tech Stack")
        if context.tech_stack:
            for t in context.tech_stack:
                lines.append(f"- {t}")
        else:
            lines.append("- Not detected")
        if context.languages:
            lines.append("")
            lines.append("### Languages")
            lines.append(", ".join(context.languages))
        lines.append("")

        # Installation
        lines.append("## Installation")
        lines.append("```bash")
        lines.append(f"git clone https://github.com/your-username/{context.name}.git")
        lines.append(f"cd {context.name}")
        if context.language == "Python":
            lines.append("python -m venv .venv")
            lines.append("source .venv/bin/activate   # Linux/macOS")
            lines.append("# .venv\\Scripts\\activate     # Windows")
            lines.append("pip install -r requirements.txt")
        elif context.language in ("JavaScript", "TypeScript"):
            lines.append("npm install")
        lines.append("```")
        lines.append("")

        # Usage
        lines.append("## Usage")
        if context.entry_points:
            lines.append("```bash")
            for ep in context.entry_points[:3]:
                lines.append(f"python {ep}")
            lines.append("```")
        else:
            lines.append("See the source code for usage examples.")
        lines.append("")

        # Project Structure
        lines.append("## Project Structure")
        lines.append("```")
        lines.append(context.file_tree)
        lines.append("```")
        lines.append("")

        # Optional sections
        if context.has_docker:
            lines.append("## Docker")
            lines.append("```bash")
            lines.append("docker build -t your-image .")
            lines.append("docker run -p 8000:8000 your-image")
            lines.append("```")
            lines.append("")

        if context.has_tests:
            lines.append("## Testing")
            if context.language == "Python":
                lines.append("```bash")
                lines.append("pytest")
                lines.append("```")
            lines.append("")

        if context.has_ci:
            lines.append("## CI/CD")
            lines.append("This project uses GitHub Actions for continuous integration.")
            lines.append("")

        # Contributing
        lines.append("## Contributing")
        lines.append("Contributions are welcome! Please open an issue or submit a pull request.")
        lines.append("")

        # License
        lines.append("## License")
        lines.append(f"{context.license or 'MIT'}")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _infer_features(context: RepoContext) -> list[str]:
        features: list[str] = []
        if context.has_tests:
            features.append("Comprehensive test suite included")
        if context.has_docs:
            features.append("Documentation provided")
        if context.has_docker:
            features.append("Docker-ready for containerized deployment")
        if context.has_ci:
            features.append("CI/CD pipeline configured")
        if context.language == "Python":
            features.append("Modern Python packaging with pyproject/requirements")
        if not features:
            features = [
                "Clean, maintainable codebase",
                "Well-organized project structure",
                "Ready for extension and customization",
            ]
        return features[:6]

    # ------------------------------------------------------------------ #
    # LLM prompt (used when online)
    # ------------------------------------------------------------------ #

    def _build_prompt(self, context: RepoContext) -> str:
        tech = ", ".join(context.tech_stack) if context.tech_stack else "not detected"
        langs = ", ".join(context.languages) if context.languages else "not detected"
        deps = ", ".join(context.dependencies[:15]) if context.dependencies else "not listed"
        entry = ", ".join(context.entry_points) if context.entry_points else "none found"

        return f"""You are an expert technical writer. Generate a professional, complete README.md file
for the following GitHub repository. Output ONLY the markdown content, no extra commentary.

REPOSITORY CONTEXT:
- Name: {context.name}
- Description: {context.description or "not provided"}
- Primary language: {context.language}
- All languages: {langs}
- Tech stack: {tech}
- Project type: {context.project_type}
- Has tests: {context.has_tests}
- Has docs: {context.has_docs}
- Has Docker: {context.has_docker}
- Has CI/CD: {context.has_ci}
- Entry points: {entry}
- Dependencies: {deps}
- Existing README: {context.readme_exists}
- License: {context.license or "not detected"}

FILE TREE:
{context.file_tree}

KEY FILES (truncated):
{self._format_key_files(context.key_files)}

REQUIREMENTS:
1. Start with an H1 title using the repository name.
2. Add a short project description (2-3 sentences).
3. Add a "Features" bullet list (infer 4-6 features from the context).
4. Add a "Tech Stack" section with badges (use shields.io URLs).
5. Add an "Installation" section with shell commands appropriate to the tech stack.
6. Add a "Usage" section with a code example based on entry points.
7. Add a "Project Structure" section showing the main folders.
8. Add a "Contributing" section.
9. Add a "License" section.
10. Keep tone professional and concise. Use markdown tables where appropriate.
11. Do not invent specific API endpoints or function names unless they appear in key files.
"""

    @staticmethod
    def _format_key_files(key_files: dict[str, str]) -> str:
        if not key_files:
            return "(none)"
        parts: list[str] = []
        for name, content in key_files.items():
            parts.append(f"### {name}\n```\n{content}\n```")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    # LLM calls
    # ------------------------------------------------------------------ #

    def _call_llm(self, prompt: str) -> str:
        family = PROVIDERS.get(self.provider, {}).get("family", "openai")

        if family == "anthropic":
            return self._call_anthropic(prompt)
        if family == "ollama":
            return self._call_ollama(prompt)
        # openai, openrouter, groq, mistral, together, custom -> OpenAI-compatible
        return self._call_openai_compatible(prompt)

    def _call_openai_compatible(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key, base_url=self.base_url or None)
        response = client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = [
            block.text for block in response.content if getattr(block, "text", None)
        ]
        return "\n".join(text_parts)

    def _call_ollama(self, prompt: str) -> str:
        import requests

        url = self.base_url or "http://localhost:11434"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        response = requests.post(f"{url}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")

    # ------------------------------------------------------------------ #
    # Post-processing
    # ------------------------------------------------------------------ #

    def _post_process(self, content: str, context: RepoContext) -> str:
        # Ensure the file starts with an H1
        lines = content.strip().splitlines()
        if lines and not lines[0].startswith("# "):
            lines.insert(0, f"# {context.name}")

        # Append a small "Generated with AI" footer (optional transparency)
        footer = "\n---\n\n*README generated with [AI README Generator](https://github.com/your-username/readme-generator-ai)*"

        return "\n".join(lines).rstrip() + footer