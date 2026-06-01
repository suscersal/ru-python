import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODULES_FILE = BASE / "modules.json"
README_FILE = BASE / "README.md"

START = "<!--START_SECTION:translations-->"
END = "<!--END_SECTION:translations-->"

data = json.loads(MODULES_FILE.read_text(encoding="utf-8"))

rows = []
for module_name, module_data in data.items():
    module_ru = module_data.get("ru-name", "")
    rows.append((module_name, module_name, module_ru))

    sources = module_data.get("sources", {})
    for source_name, source_data in sources.items():
        source_ru = source_data.get("ru-name", "")
        rows.append((module_name, source_name, source_ru))

table = """| Модуль | Имя | Русский |
|---|---|---|
"""
for module_name, english_name, russian_name in rows:
    table += f"| {module_name} | {english_name} | {russian_name} |
"

readme = README_FILE.read_text(encoding="utf-8") if README_FILE.exists() else ""

if START in readme and END in readme:
    before = readme.split(START, 1)[0]
    after = readme.split(END, 1)[1]
    new_readme = before + START + "
" + table + END + after
else:
    if readme and not readme.endswith("
"):
        readme += "
"
    new_readme = readme + "
## Таблица переводов

" + table

README_FILE.write_text(new_readme, encoding="utf-8")