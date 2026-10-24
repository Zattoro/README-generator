"""Точка входа: проверка окружения -> графический интерфейс."""

from readme_gen.bootstrap import run_bootstrap
from readme_gen.gui import main as gui_main


def main() -> None:
    bootstrap_result = run_bootstrap()
    gui_main(bootstrap_result)


if __name__ == "__main__":
    main()