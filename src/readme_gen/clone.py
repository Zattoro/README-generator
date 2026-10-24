"""Скачивание репозиториев по ссылке GitHub (и других Git-хостингов).

Поддерживает два способа:
1. git clone — если установлен Git
2. Скачивание ZIP-архива через GitHub API — работает без установленного Git
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
import io
from pathlib import Path
from typing import Optional, Tuple


def parse_github_url(url: str) -> Optional[Tuple[str, str, str]]:
    """
    Парсит ссылку GitHub на (owner, repo, branch).

    Поддерживает:
    - https://github.com/owner/repo
    - https://github.com/owner/repo/
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/tree/branch-name
    """
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    parts = url.split("/")
    try:
        github_index = parts.index("github.com")
    except ValueError:
        return None

    if len(parts) < github_index + 3:
        return None

    owner = parts[github_index + 1]
    repo = parts[github_index + 2]

    branch = "main"
    if len(parts) > github_index + 4 and parts[github_index + 3] == "tree":
        branch = parts[github_index + 4]

    return owner, repo, branch


def clone_github_repo(
    url: str,
    target_dir: Optional[Path] = None,
    depth: int = 1,
    use_zip_fallback: bool = True,
) -> Path:
    """
    Скачивает репозиторий по ссылке.

    Сначала пробует git clone, если Git установлен.
    Иначе — скачивает ZIP-архив с GitHub (не требует Git).

    Args:
        url: Ссылка на репозиторий.
        target_dir: Куда сохранить. Если None — временная папка.
        depth: Глубина клонирования (для git).
        use_zip_fallback: Разрешить скачивание ZIP вместо git.

    Returns:
        Путь к папке с репозиторием.
    """
    url = url.strip()

    # 1. Пытаемся git clone
    if shutil.which("git") is not None:
        if target_dir is None:
            target_dir = Path(tempfile.mkdtemp(prefix="readme_gen_"))
        else:
            target_dir = Path(target_dir)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                ["git", "clone", "--depth", str(depth), url, str(target_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            return target_dir
        except (subprocess.CalledProcessError, FileNotFoundError):
            if not use_zip_fallback:
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
                raise RuntimeError(
                    f"Не удалось клонировать репозиторий {url}. Git вернул ошибку."
                )
            # Иначе fallback на ZIP

    # 2. ZIP-архив через GitHub (не требует Git)
    parsed = parse_github_url(url)
    if parsed is None:
        raise RuntimeError(
            f"Неизвестный формат ссылки: {url}. "
            "Ожидалась ссылка вида https://github.com/owner/repo"
        )

    owner, repo, branch = parsed
    zip_url = (
        f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    )

    if target_dir is None:
        target_dir = Path(tempfile.mkdtemp(prefix="readme_gen_"))
    else:
        target_dir = Path(target_dir)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(zip_url, timeout=60) as resp:
            data = resp.read()
    except Exception as exc:
        raise RuntimeError(
            f"Не удалось скачать архив с GitHub ({zip_url}):\n{exc}"
        ) from exc

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # В ZIP от GitHub корневая папка имеет вид repo-branch/
            zf.extractall(target_dir)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"Скачанный файл не является ZIP-архивом: {exc}") from exc

    # GitHub кладёт файлы во вложенную папку repo-branch — поднимаем их на уровень выше
    entries = [p for p in target_dir.iterdir() if p.is_dir()]
    if len(entries) == 1:
        inner = entries[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(target_dir / item.name))
        shutil.rmtree(inner, ignore_errors=True)

    return target_dir


def is_github_url(url: str) -> bool:
    """Проверяет, выглядит ли строка как ссылка на Git-репозиторий."""
    url = url.strip().lower()
    return (
        url.startswith("http://")
        or url.startswith("https://")
        or url.startswith("git@")
        or url.startswith("ssh://")
    )


def suggest_output_name(url: str) -> str:
    """Предлагает имя папки на основе URL репозитория."""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.split("/")[-1]