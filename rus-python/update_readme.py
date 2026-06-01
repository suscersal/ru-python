import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODULES_FILE = BASE / "modules.json"
README_FILE = BASE / "README.md"

START = "<!--START_SECTION:translations-->\n"
END = "\n<!--END_SECTION:translations-->"

# Чтение данных
data = json.loads(MODULES_FILE.read_text(encoding="utf-8"))

# Сбор строк таблицы
lines = [
    "| Модуль | Источник / Компонент | Название на русском |",
    "| :--- | :--- | :--- |",
]

for module_name, module_data in data.items():
    # Главная строка модуля
    ru_module = module_data.get("ru-name", "")
    lines.append(f"| **{module_name}** | — | {ru_module} |")
    
    # Строки вложенных источников
    for source_name, source_data in module_data.get("sources", {}).items():
        ru_source = source_data.get("ru-name", "")
        lines.append(f"| {module_name} | `{source_name}` | {ru_source} |")

# Объединяем строго через перенос строки \n
table = "\n".join(lines)

# Чтение README
readme = README_FILE.read_text(encoding="utf-8") if README_FILE.exists() else ""

# Обновление контента
if START.strip() in readme and END.strip() in readme:
    # Разделяем по тегам, игнорируя возможные пробелы вокруг них
    before = readme.split(START.strip(), 1)[0]
    after = readme.split(END.strip(), 1)[1]
    new_readme = f"{before}{START.strip()}\n{table}\n{END.strip()}{after}"
else:
    # Если тегов нет, добавляем секцию в конец файла
    if readme and not readme.endswith("\n"):
        readme += "\n"
    new_readme = f"{readme}\n## Таблица переводов\n\n{START.strip()}\n{table}\n{END.strip()}\n"

# Запись в файл
README_FILE.write_text(new_readme, encoding="utf-8")
