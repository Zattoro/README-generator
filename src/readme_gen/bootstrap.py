"""Автопроверка и установка недостающего ПО перед запуском GUI.

Проверяет:
- наличие Git (для полноценного клонирования)
- соединение с интернетом
- возможность скачивания ZIP-архивов с GitHub (резервный способ без Git)

Если чего-то не хватает, показывает дружелюбное окно и предлагает установить
или перейти в режим работы без Git (скачивание ZIP).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Tuple

import tkinter as tk
from tkinter import ttk, messagebox


class BootstrapResult:
    """Итог проверки окружения."""

    def __init__(self) -> None:
        self.git_available: bool = False
        self.internet_available: bool = False
        self.github_zip_available: bool = False
        self.use_zip_fallback: bool = True


def _check_git() -> bool:
    """Возвращает True, если git доступен в PATH."""
    return shutil.which("git") is not None


def _check_internet(timeout: float = 5.0) -> bool:
    """Проверяет соединение с интернетом через запрос к GitHub."""
    try:
        urllib.request.urlopen("https://github.com", timeout=timeout)
        return True
    except Exception:  # noqa: BLE001
        return False


def _check_github_zip(timeout: float = 8.0) -> bool:
    """Проверяет, можно ли скачать ZIP-архив с GitHub (HEAD-запрос)."""
    try:
        req = urllib.request.Request(
            "https://github.com/octocat/Hello-World/archive/refs/heads/main.zip",
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 302, 301)
    except Exception:  # noqa: BLE001
        return False


def run_bootstrap() -> BootstrapResult:
    """Показывает окно проверки окружения и возвращает результат."""

    result = BootstrapResult()

    root = tk.Tk()
    root.title("AI README Generator — проверка окружения")
    root.geometry("520x340")
    root.resizable(False, False)

    # Центрируем окно
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    container = ttk.Frame(root, padding="20")
    container.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        container, text="Проверка необходимых компонентов…",
        font=("Segoe UI", 12, "bold"),
    ).pack(pady=(0, 12))

    status_vars: dict[str, tk.StringVar] = {}

    def add_check(name: str) -> tk.StringVar:
        var = tk.StringVar(value="Проверяется…")
        row = ttk.Frame(container)
        row.pack(fill=tk.X, pady=3)
        ttk.Label(row, text=name, width=28).pack(side=tk.LEFT)
        lbl = ttk.Label(row, textvariable=var, width=14)
        lbl.pack(side=tk.RIGHT)
        status_vars[name] = var
        return var

    git_var = add_check("Git")
    net_var = add_check("Интернет")
    zip_var = add_check("ZIP-загрузка с GitHub")

    result_label = ttk.Label(container, text="", foreground="#006600")
    result_label.pack(pady=(10, 0))

    btn_frame = ttk.Frame(container)
    btn_frame.pack(pady=(14, 0), fill=tk.X)

    continue_btn = ttk.Button(btn_frame, text="Продолжить", state=tk.DISABLED)
    continue_btn.pack(side=tk.RIGHT)

    def run_checks() -> None:
        # Git
        git_ok = _check_git()
        result.git_available = git_ok
        git_var.set("✅ Есть" if git_ok else "❌ Не найден")

        # Интернет
        net_ok = _check_internet()
        result.internet_available = net_ok
        net_var.set("✅ Есть" if net_ok else "❌ Нет")

        # ZIP GitHub
        zip_ok = _check_github_zip() if net_ok else False
        result.github_zip_available = zip_ok
        zip_var.set("✅ Доступно" if zip_ok else "❌ Недоступно")

        # Логика
        if git_ok:
            result.use_zip_fallback = False
            result_label.config(
                text="Всё готово. Запуск программы…",
                foreground="#006600",
            )
        elif net_ok and zip_ok:
            result.use_zip_fallback = True
            result_label.config(
                text="Git не найден. Будем скачивать архивы ZIP с GitHub.\n"
                     "Это работает без установки дополнительного ПО.",
                foreground="#006600",
            )
        else:
            result.use_zip_fallback = True
            result_label.config(
                text="Внимание: нет интернета или GitHub недоступен.\n"
                     "Программа будет работать только с локальными папками.",
                foreground="#b35900",
            )

        continue_btn.config(state=tk.NORMAL)

    # Запускаем проверки с небольшой задержкой, чтобы окно успело отрисоваться
    root.after(100, run_checks)

    def on_continue() -> None:
        root.destroy()

    continue_btn.config(command=on_continue)

    # Если интернета нет и Git нет — кнопка всё равно активна, но с предупреждением
    root.mainloop()

    return result


if __name__ == "__main__":
    run_bootstrap()