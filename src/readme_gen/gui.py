"""Графический интерфейс AI README Generator на tkinter (тёмная тема)."""

from __future__ import annotations

import shutil
import tempfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from .analyzer import RepoAnalyzer
from .clone import clone_github_repo, is_github_url, suggest_output_name
from .config import PROVIDERS, Settings
from .generator import ReadmeGenerator
from .bootstrap import run_bootstrap, BootstrapResult

# --- Цвета тёмной темы ---------------------------------------------------
BG_COLOR = "#1e1e1e"          # фон окна
FRAME_COLOR = "#252526"       # фон панелей / LabelFrame
PANEL_COLOR = "#2d2d2d"       # фон внутренних панелей
INPUT_COLOR = "#333333"       # фон полей ввода
TEXT_COLOR = "#cccccc"        # основной текст
MUTED_COLOR = "#858585"       # вспомогательный текст
ACCENT_COLOR = "#007acc"      # акцент (кнопки, ползунок)
ACCENT_HOVER = "#005a9e"      # акцент при наведении
BORDER_COLOR = "#3e3e42"      # рамки
DISABLED_COLOR = "#4a4a4a"    # неактивные элементы


class DarkStyle:
    """Применяет тёмную тему ко всем ttk-виджетам."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.style = ttk.Style(root)

        # Используем базовую тему 'clam' — она легче всего перекрашивается
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self._configure_base()
        self._configure_frames()
        self._configure_labels()
        self._configure_buttons()
        self._configure_entries()
        self._configure_combobox()
        self._configure_radiobuttons()
        self._configure_scale()
        self._configure_statusbar()

    def _configure_base(self) -> None:
        self.root.configure(bg=BG_COLOR)
        self.style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR,
                             bordercolor=BORDER_COLOR, darkcolor=BORDER_COLOR,
                             lightcolor=BORDER_COLOR, insertcolor=TEXT_COLOR)

    def _configure_frames(self) -> None:
        self.style.configure("TFrame", background=BG_COLOR, borderwidth=0)
        self.style.configure("TLabelframe", background=FRAME_COLOR,
                             bordercolor=BORDER_COLOR, lightcolor=BORDER_COLOR,
                             darkcolor=BORDER_COLOR)
        self.style.configure("TLabelframe.Label", background=FRAME_COLOR,
                             foreground=TEXT_COLOR, font=("Segoe UI", 10, "bold"))

    def _configure_labels(self) -> None:
        self.style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR,
                             font=("Segoe UI", 9))
        self.style.configure("Muted.TLabel", background=BG_COLOR,
                             foreground=MUTED_COLOR, font=("Segoe UI", 9))

    def _configure_buttons(self) -> None:
        self.style.configure("TButton", background=ACCENT_COLOR,
                             foreground="white", borderwidth=0,
                             focuscolor=ACCENT_COLOR, font=("Segoe UI", 9, "bold"))
        self.style.map("TButton",
                       background=[("active", ACCENT_HOVER), ("disabled", DISABLED_COLOR)],
                       foreground=[("disabled", "#666666")])

    def _configure_entries(self) -> None:
        self.style.configure("TEntry", fieldbackground=INPUT_COLOR,
                             foreground=TEXT_COLOR, bordercolor=BORDER_COLOR,
                             lightcolor=BORDER_COLOR, darkcolor=BORDER_COLOR,
                             insertcolor=TEXT_COLOR)
        self.style.map("TEntry",
                       fieldbackground=[("disabled", DISABLED_COLOR)],
                       foreground=[("disabled", "#666666")])

    def _configure_combobox(self) -> None:
        self.style.configure("TCombobox", fieldbackground=INPUT_COLOR,
                             background=INPUT_COLOR, foreground=TEXT_COLOR,
                             bordercolor=BORDER_COLOR, arrowcolor=TEXT_COLOR,
                             insertcolor=TEXT_COLOR)
        self.style.map("TCombobox",
                       fieldbackground=[("readonly", INPUT_COLOR)],
                       foreground=[("readonly", TEXT_COLOR)],
                       background=[("active", ACCENT_COLOR)])

    def _configure_radiobuttons(self) -> None:
        self.style.configure("TRadiobutton", background=BG_COLOR,
                             foreground=TEXT_COLOR, focuscolor=ACCENT_COLOR,
                             font=("Segoe UI", 9))
        self.style.map("TRadiobutton",
                       background=[("active", BG_COLOR), ("selected", BG_COLOR)],
                       foreground=[("active", TEXT_COLOR)])

    def _configure_scale(self) -> None:
        self.style.configure("TScale", background=BG_COLOR,
                             troughcolor=INPUT_COLOR, bordercolor=BORDER_COLOR,
                             lightcolor=ACCENT_COLOR, darkcolor=ACCENT_COLOR)
        self.style.map("TScale",
                       background=[("active", ACCENT_COLOR)])

    def _configure_statusbar(self) -> None:
        self.style.configure("Status.TLabel", background=FRAME_COLOR,
                             foreground=MUTED_COLOR, font=("Segoe UI", 8),
                             borderwidth=0, relief="flat")


class ReadmeGeneratorApp:
    def __init__(self, root: tk.Tk, bootstrap_result: BootstrapResult) -> None:
        self.root = root
        self.bootstrap = bootstrap_result
        self.root.title("AI README Generator")
        self.root.geometry("920x800")
        self.root.minsize(750, 650)

        # Тёмная тема
        self.dark = DarkStyle(root)

        self.temp_dir: Path | None = None

        self._build_ui()
        self._toggle_source()
        self._toggle_mode()
        self._show_bootstrap_info()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding="14")
        main.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title = ttk.Label(
            main, text="AI README Generator", font=("Segoe UI", 18, "bold"),
            foreground=ACCENT_COLOR,
        )
        title.pack(pady=(0, 6))

        subtitle = ttk.Label(
            main,
            text="Генерация профессионального README.md для любого репозитория",
            style="Muted.TLabel",
        )
        subtitle.pack(pady=(0, 16))

        # --- Инфо о среде (от bootstrap) ------------------------------- #
        self.env_frame = ttk.LabelFrame(main, text="Окружение", padding="10")
        self.env_frame.pack(fill=tk.X, pady=6)
        self.env_label = ttk.Label(self.env_frame, text="", style="Muted.TLabel")
        self.env_label.pack(anchor=tk.W)

        # --- Источник -------------------------------------------------- #
        src_frame = ttk.LabelFrame(main, text="Источник репозитория", padding="10")
        src_frame.pack(fill=tk.X, pady=6)

        self.source_var = tk.StringVar(value="local")
        ttk.Radiobutton(
            src_frame,
            text="Локальная папка на ПК",
            variable=self.source_var,
            value="local",
            command=self._toggle_source,
        ).pack(anchor=tk.W, pady=2)

        ttk.Radiobutton(
            src_frame,
            text="Ссылка на GitHub / Git репозиторий",
            variable=self.source_var,
            value="url",
            command=self._toggle_source,
        ).pack(anchor=tk.W, pady=2)

        # Поле локального пути
        self.path_frame = ttk.Frame(src_frame)
        self.path_frame.pack(fill=tk.X, pady=6)
        ttk.Label(self.path_frame, text="Путь:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=".")
        self.path_entry = ttk.Entry(self.path_frame, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(self.path_frame, text="Обзор…", command=self._browse_folder).pack(
            side=tk.LEFT
        )

        # Поле URL
        self.url_frame = ttk.Frame(src_frame)
        ttk.Label(self.url_frame, text="URL:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        # --- Режим ----------------------------------------------------- #
        mode_frame = ttk.LabelFrame(main, text="Режим генерации", padding="10")
        mode_frame.pack(fill=tk.X, pady=6)

        self.mode_var = tk.StringVar(value="offline")
        ttk.Radiobutton(
            mode_frame,
            text="Офлайн (без API ключа, шаблон)",
            variable=self.mode_var,
            value="offline",
            command=self._toggle_mode,
        ).pack(anchor=tk.W, pady=2)

        ttk.Radiobutton(
            mode_frame,
            text="Онлайн (LLM API)",
            variable=self.mode_var,
            value="online",
            command=self._toggle_mode,
        ).pack(anchor=tk.W, pady=2)

        # Онлайн-настройки
        self.online_frame = ttk.Frame(mode_frame)

        prov_row = ttk.Frame(self.online_frame)
        prov_row.pack(fill=tk.X, pady=4)
        ttk.Label(prov_row, text="Провайдер:").pack(side=tk.LEFT)
        self.provider_var = tk.StringVar(value="openai")
        provider_names = [f"{PROVIDERS[p]['name']} ({p})" for p in PROVIDERS]
        self.provider_combo = ttk.Combobox(
            prov_row, values=provider_names, state="readonly", width=42
        )
        self.provider_combo.current(0)
        self.provider_combo.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        key_row = ttk.Frame(self.online_frame)
        key_row.pack(fill=tk.X, pady=4)
        ttk.Label(key_row, text="API ключ:").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(
            key_row, textvariable=self.api_key_var, show="*", width=52
        )
        self.api_key_entry.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        model_row = ttk.Frame(self.online_frame)
        model_row.pack(fill=tk.X, pady=4)
        ttk.Label(model_row, text="Модель:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value="gpt-4o-mini")
        self.model_entry = ttk.Entry(model_row, textvariable=self.model_var, width=52)
        self.model_entry.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        url_row = ttk.Frame(self.online_frame)
        url_row.pack(fill=tk.X, pady=4)
        ttk.Label(url_row, text="Base URL:").pack(side=tk.LEFT)
        self.base_url_var = tk.StringVar()
        self.base_url_entry = ttk.Entry(
            url_row, textvariable=self.base_url_var, width=52
        )
        self.base_url_entry.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        temp_row = ttk.Frame(self.online_frame)
        temp_row.pack(fill=tk.X, pady=4)
        ttk.Label(temp_row, text="Температура:").pack(side=tk.LEFT)
        self.temp_var = tk.DoubleVar(value=0.3)
        self.temp_scale = ttk.Scale(
            temp_row,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.temp_var,
            command=lambda v: self.temp_label.config(text=f"{float(v):.1f}"),
        )
        self.temp_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.temp_label = ttk.Label(temp_row, text="0.3", style="Muted.TLabel")
        self.temp_label.pack(side=tk.LEFT)

        # --- Кнопки ---------------------------------------------------- #
        btn_frame = ttk.Frame(main, padding="10")
        btn_frame.pack(fill=tk.X, pady=12)

        self.generate_btn = ttk.Button(
            btn_frame, text="Сгенерировать README", command=self._start_generation
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Очистить лог", command=self._clear_log).pack(
            side=tk.LEFT, padx=5
        )

        # --- Лог ------------------------------------------------------- #
        log_frame = ttk.LabelFrame(main, text="Лог", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=16, wrap=tk.WORD,
            bg=INPUT_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            selectbackground=ACCENT_COLOR, selectforeground="white",
            borderwidth=0, highlightthickness=0, font=("Consolas", 9),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # --- Статус ---------------------------------------------------- #
        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(
            main, textvariable=self.status_var, style="Status.TLabel",
            anchor=tk.W, padding=(4, 4),
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _show_bootstrap_info(self) -> None:
        lines: list[str] = []
        if self.bootstrap.git_available:
            lines.append("✅ Git найден — полноценное клонирование доступно")
        else:
            lines.append("⚠️ Git не найден — используется скачивание ZIP с GitHub")

        if self.bootstrap.internet_available:
            lines.append("✅ Интернет доступен")
        else:
            lines.append("❌ Интернет недоступен — только локальные папки")

        if self.bootstrap.use_zip_fallback:
            lines.append("📦 Режим: скачивание архивов ZIP с GitHub")

        self.env_label.config(text="   ".join(lines))

    def _toggle_source(self) -> None:
        if self.source_var.get() == "local":
            self.path_frame.pack(fill=tk.X, pady=6)
            self.url_frame.pack_forget()
        else:
            self.path_frame.pack_forget()
            self.url_frame.pack(fill=tk.X, pady=6)

    def _toggle_mode(self) -> None:
        if self.mode_var.get() == "offline":
            self.online_frame.pack_forget()
        else:
            self.online_frame.pack(fill=tk.X, pady=6)

    def _browse_folder(self) -> None:
        folder = filedialog.askdirectory(
            title="Выберите папку с репозиторием"
        )
        if folder:
            self.path_var.set(folder)

    def _log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _clear_log(self) -> None:
        self.log_text.delete("1.0", tk.END)

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #

    def _start_generation(self) -> None:
        self.generate_btn.config(state=tk.DISABLED)
        self.status_var.set("Генерация...")
        thread = threading.Thread(target=self._generate_thread, daemon=True)
        thread.start()

    def _generate_thread(self) -> None:
        try:
            # ----- Источник ----- #
            if self.source_var.get() == "local":
                work_path = Path(self.path_var.get()).resolve()
                url = None
                keep = False
            else:
                url = self.url_var.get().strip()
                if not url:
                    self._log("Ошибка: введите ссылку на репозиторий")
                    return
                if not is_github_url(url):
                    self._log(
                        "Внимание: это не похоже на Git-ссылку, но попробуем всё равно."
                    )
                self.temp_dir = Path(tempfile.mkdtemp(prefix="readme_gen_"))
                try:
                    work_path = clone_github_repo(
                        url,
                        target_dir=self.temp_dir,
                        use_zip_fallback=self.bootstrap.use_zip_fallback,
                    )
                    self._log(f"Загружено во временную папку: {work_path}")
                except Exception as exc:
                    self._log(f"Ошибка загрузки репозитория: {exc}")
                    return
                keep = False

            if not work_path.exists():
                self._log(f"Ошибка: путь не найден: {work_path}")
                return

            # ----- Настройки ----- #
            offline = self.mode_var.get() == "offline"
            provider = "offline"
            api_key = ""
            model = ""
            base_url = ""
            temperature = self.temp_var.get()

            if not offline:
                provider_idx = self.provider_combo.current()
                provider = list(PROVIDERS.keys())[provider_idx]
                api_key = self.api_key_var.get().strip()
                model = self.model_var.get().strip() or PROVIDERS[provider][
                    "default_model"
                ]
                base_url = self.base_url_var.get().strip()
                if not api_key:
                    self._log("Ошибка: введите API ключ для выбранного провайдера")
                    return

            # ----- Анализ ----- #
            self._log("Анализ репозитория…")
            analyzer = RepoAnalyzer(work_path)
            context = analyzer.analyze()
            self._log(f"Язык: {context.language or 'не определён'}")
            self._log(f"Стек: {', '.join(context.tech_stack) or 'не определён'}")

            # ----- Генерация ----- #
            self._log("Генерация README…")
            generator = ReadmeGenerator(
                provider=provider,
                api_key=api_key,
                model=model,
                base_url=base_url,
                temperature=temperature,
                offline=offline,
            )
            readme = generator.generate(context)

            # ----- Сохранение ----- #
            if self.source_var.get() == "local":
                out_path = work_path / "README.md"
            else:
                out_path = Path.cwd() / f"{work_path.name}_README.md"

            out_path.write_text(readme, encoding="utf-8")
            self._log(f"Готово! README сохранён: {out_path}")
            self.status_var.set(f"Готово: {out_path}")

            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Готово", f"README сохранён в:\n{out_path}"
                ),
            )

        except Exception as exc:  # noqa: BLE001
            self._log(f"Ошибка: {exc}")
            self.status_var.set("Ошибка")
        finally:
            self.generate_btn.config(state=tk.NORMAL)
            # Очистка временной папки после генерации по URL
            if self.temp_dir:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir = None


def main(bootstrap_result: BootstrapResult | None = None) -> None:
    if bootstrap_result is None:
        bootstrap_result = run_bootstrap()

    root = tk.Tk()
    app = ReadmeGeneratorApp(root, bootstrap_result)
    root.mainloop()


if __name__ == "__main__":
    main()