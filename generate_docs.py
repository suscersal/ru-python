from pathlib import Path
import json
import html

snippets_file = Path("rus-python/snippets/rupy-words.json")
docs_dir = Path("docs")
docs_dir.mkdir(exist_ok=True)

def esc(s):
    return html.escape(str(s))

page = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ru-Python Snippets</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f6f8fa; }
    .container { background: white; padding: 30px; border-radius: 8px; }
    .snippet { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 16px 0; background: #fafbfc; }
    pre { background: #1e1e1e; color: #fff; padding: 14px; border-radius: 6px; overflow-x: auto; }
    code { font-family: Consolas, monospace; }
    .meta { margin: 6px 0; color: #555; }
    a { color: #0969da; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <p><a href="index.html">← На главную</a></p>
    <h1>Snippets документация</h1>
"""

count = 0

if snippets_file.exists():
    data = json.loads(snippets_file.read_text(encoding="utf-8"))
    for name, item in data.items():
        prefix = item.get("prefix", "")
        description = item.get("description", "")
        body = item.get("body", "")

        if isinstance(body, list):
            body_text = "".join(body)
        else:
            body_text = str(body)

        page += f"""
    <div class="snippet">
      <h2>{esc(name)}</h2>
      <div class="meta"><b>Prefix:</b> <code>{esc(prefix)}</code></div>
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

(docs_dir / "documentation.html").write_text(page, encoding="utf-8")
print(f"Generated {count} snippets")
