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
    rows.append((module_name, module_name, module_data.get("ru-name", "")))
    for source_name, source_data in module_data.get("sources", {}).items():
        rows.append((module_name, source_name, source_data.get("ru-name", "")))

lines = [
    "| Модуль | Имя | Русский |",
    "|---|---|---|",
]

for module_name, english_name, russian_name in rows:
    lines.append("| {} | {} | {} |".format(module_name, english_name, russian_name))

table = "".join(lines) + ""

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
