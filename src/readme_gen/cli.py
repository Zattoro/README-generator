"""Command-line interface for the README generator."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, Prompt
from rich.syntax import Syntax
from rich.table import Table

from .analyzer import RepoAnalyzer
from .clone import clone_github_repo, is_github_url, suggest_output_name
from .config import PROVIDERS, PROVIDER_CHOICES, Settings
from .generator import ReadmeGenerator

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="readme-gen",
        description="Generate a professional README.md using AI.",
    )
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Generate README for a directory")
    # Source: either local path or Git URL
    gen.add_argument("path", nargs="?", default=".", help="Path to local repository (default: .)")
    gen.add_argument(
        "--url",
        help="GitHub/Git repository URL to clone and generate README for",
    )
    gen.add_argument(
        "--keep",
        action="store_true",
        help="Keep cloned repository after generation (only with --url)",
    )
    gen.add_argument("-o", "--output", help="Output file path (default: <path>/README.md)")
    gen.add_argument(
        "--provider",
        choices=PROVIDER_CHOICES,
        help="LLM provider (overrides interactive choice / .env)",
    )
    gen.add_argument("--model", help="Model name (overrides .env)")
    gen.add_argument("--api-key", help="API key (overrides .env)")
    gen.add_argument("--base-url", help="Custom base URL (overrides .env)")
    gen.add_argument(
        "--temperature",
        type=float,
        help="Sampling temperature (overrides .env)",
    )
    gen.add_argument(
        "--offline",
        action="store_true",
        help="Force offline template mode (no LLM API call)",
    )
    gen.add_argument(
        "--no-preview",
        action="store_true",
        help="Skip printing preview to console",
    )
    gen.add_argument(
        "--save-env",
        action="store_true",
        help="Save chosen settings to .env file before generating",
    )

    return parser


# ---------------------------------------------------------------------- #
# Interactive menu
# ---------------------------------------------------------------------- #

def _show_banner() -> None:
    console.print(
        Panel.fit(
            "[bold blue]AI README Generator[/bold blue]\n"
            "Создаёт профессиональный README.md для любого репозитория",
            border_style="blue",
        )
    )


def _choose_source() -> tuple[str, Optional[str]]:
    """Ask user whether to use local path or Git URL."""
    table = Table(title="Источник репозитория", show_header=True)
    table.add_column("№", style="cyan", justify="center")
    table.add_column("Способ", style="green")
    table.add_column("Описание", style="magenta")

    table.add_row("1", "Локальный путь", "Укажи путь к скачанному репозиторию на ПК")
    table.add_row("2", "Ссылка GitHub / Git", "Клонируй репозиторий по URL и сгенерируй README")

    console.print(table)
    choice = Prompt.ask("Выберите способ", choices=["1", "2"], default="1")

    if choice == "1":
        path = Prompt.ask("Путь к репозиторию", default=".")
        return "local", path
    else:
        url = Prompt.ask("Ссылка на репозиторий (GitHub / Git)")
        if not is_github_url(url):
            console.print("[yellow]Внимание: это не выглядит как Git-ссылка, но попробуем всё равно.[/yellow]")
        return "url", url


def _choose_provider() -> str:
    table = Table(title="Доступные провайдеры LLM", show_header=True)
    table.add_column("№", style="cyan", justify="center")
    table.add_column("Провайдер", style="green")
    table.add_column("Модель по умолчанию", style="magenta")

    for idx, pid in enumerate(PROVIDER_CHOICES, start=1):
        info = PROVIDERS[pid]
        table.add_row(str(idx), info["name"], info["default_model"])

    console.print(table)
    choice = Prompt.ask(
        "Выберите провайдера",
        choices=[str(i) for i in range(1, len(PROVIDER_CHOICES) + 1)],
        default="1",
    )
    return PROVIDER_CHOICES[int(choice) - 1]


def _ask_api_key(provider: str) -> str:
    info = PROVIDERS.get(provider, {})
    env_key = info.get("env_key", "")
    if not env_key:
        console.print(f"[yellow]Провайдер {provider} не требует API ключа.[/yellow]")
        return ""

    if Confirm.ask(f"Использовать существующий ключ из окружения ({env_key})?", default=True):
        import os

        existing = os.getenv(env_key, "")
        if existing:
            console.print(f"[green]Найден ключ в окружении: {existing[:4]}***[/green]")
            return existing

    return Prompt.ask(f"Введите API ключ для {info['name']}", password=True)


def interactive_mode() -> int:
    """Run the interactive TUI menu."""
    _show_banner()
    console.print("\n1. Офлайн режим (локальный путь, без API ключа)")
    console.print("2. Онлайн режим (локальный путь + API ключ)")
    console.print("3. По ссылке GitHub (клонировать + сгенерировать)")
    console.print("4. Выход\n")

    choice = Prompt.ask("Выберите опцию", choices=["1", "2", "3", "4"], default="1")

    if choice == "4":
        console.print("До свидания!")
        return 0

    if choice == "3":
        source_type, source_value = _choose_source()
        if source_type != "url":
            # fallback if user picked local in submenu
            path = source_value
            offline = True
            provider = "offline"
            api_key = ""
            model = ""
            base_url = ""
            temperature = 0.3
        else:
            url = source_value
            offline = Confirm.ask("Использовать офлайн-режим (без API)?", default=True)
            if offline:
                provider = "offline"
                api_key = ""
                model = ""
                base_url = ""
                temperature = 0.3
            else:
                provider = _choose_provider()
                api_key = _ask_api_key(provider)
                default_model = PROVIDERS[provider]["default_model"]
                model = Prompt.ask("Название модели", default=default_model)
                default_url = PROVIDERS[provider].get("default_base_url", "")
                base_url = Prompt.ask(
                    "Базовый URL API (Enter для значения по умолчанию)",
                    default=default_url,
                )
                if not base_url:
                    base_url = default_url
                temperature = FloatPrompt.ask(
                    "Temperature (0.0 = точно, 1.0 = креативно)",
                    default=0.3,
                )

            # Ask where to save output
            default_out = suggest_output_name(url) + "_README.md"
            output = Prompt.ask(
                "Куда сохранить README (Enter для значения по умолчанию)",
                default=default_out,
            )

        keep = Confirm.ask("Оставить клонированный репозиторий после генерации?", default=False)

        return _run_generate(
            path=None,
            url=url if source_type == "url" else None,
            local_path=path if source_type == "local" else None,
            output=output if source_type == "url" else None,
            provider=provider,
            api_key=api_key,
            model=model or None,
            base_url=base_url or None,
            temperature=temperature,
            offline=offline,
            keep=keep,
            no_preview=False,
            save_env=False,
        )

    # Choices 1 and 2: local path
    offline = choice == "1"
    path = Prompt.ask("Путь к репозиторию", default=".")

    provider: str = "offline"
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    temperature: float = 0.3

    if not offline:
        provider = _choose_provider()
        api_key = _ask_api_key(provider)
        default_model = PROVIDERS[provider]["default_model"]
        model = Prompt.ask("Название модели", default=default_model)
        default_url = PROVIDERS[provider].get("default_base_url", "")
        base_url = Prompt.ask(
            "Базовый URL API (Enter для значения по умолчанию)",
            default=default_url,
        )
        if not base_url:
            base_url = default_url
        temperature = FloatPrompt.ask(
            "Temperature (0.0 = точно, 1.0 = креативно)",
            default=0.3,
        )

    output = Prompt.ask(
        "Файл вывода (Enter для README.md внутри репозитория)",
        default="",
    )
    save_env = Confirm.ask("Сохранить настройки в .env?", default=True)

    return _run_generate(
        path=path,
        url=None,
        local_path=None,
        output=output or None,
        provider=provider,
        api_key=api_key,
        model=model or None,
        base_url=base_url or None,
        temperature=temperature,
        offline=offline,
        keep=False,
        no_preview=False,
        save_env=save_env,
    )


# ---------------------------------------------------------------------- #
# Core run logic
# ---------------------------------------------------------------------- #

def _run_generate(
    path: Optional[str],
    url: Optional[str],
    local_path: Optional[str],
    output: Optional[str],
    provider: str,
    api_key: str,
    model: Optional[str],
    base_url: Optional[str],
    temperature: float,
    offline: bool,
    keep: bool,
    no_preview: bool,
    save_env: bool,
) -> int:
    # Determine the working directory
    temp_dir: Optional[Path] = None
    work_path: Path

    if url:
        console.print(f"[bold blue]Клонирование[/bold blue] {url} ...")
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="readme_gen_"))
            work_path = clone_github_repo(url, target_dir=temp_dir)
        except RuntimeError as exc:
            console.print(f"[red]Ошибка клонирования:[/red] {exc}")
            return 1
        console.print(f"[green]Клонировано в[/green] {work_path}")
    elif local_path:
        work_path = Path(local_path).resolve()
    else:
        work_path = Path(path or ".").resolve()

    if not work_path.exists():
        console.print(f"[red]Error:[/red] путь не найден: {work_path}")
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        return 1

    # Settings
    settings = Settings.from_env()
    provider = provider or settings.provider
    api_key = api_key or settings.api_key
    model = model or settings.model
    base_url = base_url or settings.base_url
    temperature = temperature if temperature is not None else settings.temperature

    if save_env:
        Settings(
            provider=provider,
            api_key=api_key,
            model=model or "",
            base_url=base_url or "",
            temperature=temperature,
            offline=offline,
        ).save_to_env(work_path / ".env")
        console.print(f"[green]Настройки сохранены в {work_path / '.env'}[/green]")

    # Analyze
    console.print(f"[bold blue]Анализ[/bold blue] {work_path} ...")
    analyzer = RepoAnalyzer(work_path)
    try:
        context = analyzer.analyze()
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Ошибка анализа:[/red] {exc}")
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        return 1

    console.print(f"Язык: [green]{context.language or 'не определён'}[/green]")
    console.print(
        f"Стек: [green]{', '.join(context.tech_stack) or 'не определён'}[/green]"
    )

    # Generate
    mode = "ОФФЛАЙН" if offline else "ОНЛАЙН"
    console.print(f"[bold blue]Генерация README ({mode})...[/bold blue]")
    generator = ReadmeGenerator(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        offline=offline,
    )

    try:
        readme = generator.generate(context)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Ошибка генерации:[/red] {exc}")
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        return 1

    # Output path
    if output:
        out_path = Path(output)
    else:
        out_path = work_path / "README.md"

    out_path.write_text(readme, encoding="utf-8")
    console.print(f"[green]README записан в[/green] {out_path}")

    if not no_preview:
        console.print("\n")
        console.print(
            Panel(
                Syntax(readme, "markdown", theme="monokai", line_numbers=False),
                title="Предпросмотр",
                border_style="green",
            )
        )

    # Cleanup temp clone if not keeping
    if temp_dir and not keep:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        console.print("[yellow]Временная папка с клоном удалена.[/yellow]")

    return 0


# ---------------------------------------------------------------------- #
# Entry point
# ---------------------------------------------------------------------- #

def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # No subcommand -> interactive menu
    if not args.command:
        return interactive_mode()

    if args.command == "generate":
        return _run_generate(
            path=args.path,
            url=args.url,
            local_path=None,
            output=args.output,
            provider=args.provider or "",
            api_key=args.api_key or "",
            model=args.model,
            base_url=args.base_url,
            temperature=args.temperature if args.temperature is not None else 0.3,
            offline=args.offline,
            keep=args.keep,
            no_preview=args.no_preview,
            save_env=args.save_env,
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())