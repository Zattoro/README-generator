# AI README Generator / Генератор README на ИИ

> **English:** A GUI tool to automatically generate professional `README.md` files.  
> **Русский:** Графический инструмент для автоматического создания профессиональных файлов `README.md`.

---

## 🖼 О проекте / About

| Русский | English |
|---------|---------|
| Программа создаёт готовый к коммиту `README.md` для любого репозитория. Запускается одним `.exe` — без установки Python, Git и без открытия командной строки. | The app generates a ready-to-commit `README.md` for any repository. Runs as a single `.exe` — no Python, no Git, no command line required. |

### ✨ Особенности / Features

**Русский:**
- 🖥️ Полноценный графический интерфейс на tkinter
- 📦 Один `.exe`-файл — всё уже внутри, никакой установки
- 🌐 8 провайдеров LLM: OpenAI, Anthropic, Ollama, OpenRouter, Groq, Mistral, Together AI, Custom
- 🔌 Офлайн-режим: генерирует качественный шаблон без любого API-ключа
- 🌐 Скачивание репозитория по ссылке GitHub без установленного Git (через ZIP)
- 📁 Поддержка локальной папки на ПК
- 🧠 Автопроверка окружения при первом запуске

**English:**
- 🖥️ Full tkinter graphical interface
- 📦 Single `.exe` — everything inside, no installation needed
- 🌐 8 LLM providers: OpenAI, Anthropic, Ollama, OpenRouter, Groq, Mistral, Together AI, Custom
- 🔌 Offline mode: generates a high-quality template without any API key
- 🌐 Download GitHub repo by URL without Git installed (via ZIP archive)
- 📁 Local folder support on your PC
- 🧠 Environment auto-check on first launch

---

## 🚀 Быстрый старт / Quick Start

### Русский
1. Скачайте `AI README Generator` из релизов репозитория
2. Откройте PowerShell от имени администратора в папке с программой
3. Введите `.\build_exe.bat`
4. Откройте папку `dist`
5. Запустите двойным кликом собранный `.exe` файл
6. Выберите источник: локальную папку или ссылку на GitHub
7. Выберите режим: Офлайн (без ключа) или Онлайн (с API-ключом)
8. Нажмите «Сгенерировать README» — файл сохранится рядом с репозиторием

### English
1. Download `AI README Generator` from the repository releases
2. Open PowerShell as Administrator in the program folder
3. Run `.\build_exe.bat`
4. Open the `dist` folder
5. Double-click the built `.exe` file
6. Choose source: local folder or GitHub URL
7. Choose mode: Offline (no key) or Online (with API key)
8. Click «Generate README» — the file will be saved next to the repository

---

## 💻 Использование из командной строки / CLI Usage

```bash
# Локальная папка, офлайн
python -m readme_gen generate . --offline

# По ссылке GitHub с OpenAI
python -m readme_gen generate --url https://github.com/owner/repo \
  --provider openai --api-key sk-...

# Сохранить в отдельный файл
python -m readme_gen generate --url https://github.com/owner/repo \
  --offline -o ./my_readme.md
```

---

## 🤖 Провайдеры LLM / LLM Providers

| Провайдер             | Provider       |    Ключ / Key               |
|-----------------------|----------------|-----------------------------|
| OpenAI                | OpenAI         | `OPENAI_API_KEY`            |
| Anthropic             | Anthropic      | `ANTHROPIC_API_KEY`         |
| Ollama (локально)     | Ollama (local) | не требуется / not required |
| OpenRouter            | OpenRouter     | `OPENROUTER_API_KEY`        |
| Groq                  | Groq           | `GROQ_API_KEY`              |
| Mistral AI            | Mistral AI     | `MISTRAL_API_KEY`           |
| Together AI           | Together AI    | `TOGETHER_API_KEY`          |
| Свой API              | Custom API     | `CUSTOM_API_KEY`            |

---

## 🛠 Разработка / Development

```bash
git clone https://github.com/your-username/readme-generator-ai.git
cd readme-generator-ai
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
pip install -e .
pytest
```

### Сборка .exe / Building .exe
```bash
pip install pyinstaller
.\build_exe.bat
# или / or:
pyinstaller --onefile --windowed --name "AI README Generator" run_gui.py
```

---

## 📄 Лицензия / License

MIT License — см. файл `LICENSE` / see `LICENSE` file.

---

*Создано для портфолио на GitHub / Built for GitHub portfolio*