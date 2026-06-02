from pathlib import Path
import json
import html
import re

snippets_file = Path("rus-python/snippets/rupy-words.json")

def esc(s):
    return html.escape(str(s))

def clean_body(body):
    if isinstance(body, list):
        body = "
".join(body)
    else:
        body = str(body)

    body = re.sub(r"${d+:([^}]*)}", r"\u0001", body)
    body = re.sub(r"${d+|([^}]*)|}", r"\u0001", body)
    body = re.sub(r"$d+", "", body)
    return body

def build_page():
    page = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ru-Python Документация(отображение snippets)</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f6f8fa; }
    .container { background: white; padding: 30px; border-radius: 8px; }
    .snippet { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 16px 0; background: #fafbfc; }
    pre { background: #1e1e1e; color: #fff; padding: 14px; border-radius: 6px; overflow-x: auto; }
    code { font-family: Consolas, monospace; }
    .meta { margin: 6px 0; color: #555; }
    a { color: #0969da; text-decoration: none; }
    h1 { margin-top: 0; }
  </style>
</head>
<body>
  <div class="container">
    <p><a href="#top">← На главную</a></p>
    <h1 id="top">Snippets документация</h1>
"""

    count = 0
    if snippets_file.exists():
        data = json.loads(snippets_file.read_text(encoding="utf-8"))
        for name, item in data.items():
            description = item.get("description", "")
            body_text = clean_body(item.get("body", ""))

            page += f"""
    <div class="snippet">
      <h2>{esc(name)}</h2>
      <div class="meta"><b>Description:</b> {esc(description)}</div>
      <pre><code>{esc(body_text)}</code></pre>
    </div>
"""
            count += 1
    else:
        page += "<p>Файл rupy-words.json не найден.</p>"

    page += f"""
    <p>Всего snippets: {count}</p>
  </div>
</body>
</html>
"""
    return page

Path("index.html").write_text(build_page(), encoding="utf-8")
print("Generated index.html")
