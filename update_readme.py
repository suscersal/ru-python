"""
Скрипт обновления примера кода в README.md
Читает test.rupy и вставляет его содержимое между маркерами в README.
"""

import os
import sys

README_PATH = "README.md"
EXAMPLE_PATH = "test.rupy"

START_MARKER = "<!-- EXAMPLES_START -->"
END_MARKER = "<!-- EXAMPLES_END -->"


def update_readme():
    if not os.path.exists(README_PATH):
        print(f"Ошибка: {README_PATH} не найден")
        sys.exit(1)

    if not os.path.exists(EXAMPLE_PATH):
        print(f"Ошибка: {EXAMPLE_PATH} не найден")
        sys.exit(1)

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
        example = f.read()

    if START_MARKER not in readme or END_MARKER not in readme:
        print(f"Ошибка: маркеры не найдены в {README_PATH}")
        print(f"Добавьте в README:\n{START_MARKER}\n...\n{END_MARKER}")
        sys.exit(1)

    new_block = f"{START_MARKER}\n```\n{example.strip()}\n```\n{END_MARKER}"

    before = readme[:readme.index(START_MARKER)]
    after = readme[readme.index(END_MARKER) + len(END_MARKER):]
    new_readme = before + new_block + after

    if new_readme == readme:
        print("README уже актуален, изменений нет.")
        return

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_readme)

    print(f"README обновлен: вставлен пример из {EXAMPLE_PATH}")


if __name__ == "__main__":
    update_readme()
