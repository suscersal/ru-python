from pathlib import Path
import json
import html
import re

snippets_file = Path("rus-python/snippets/rupy-words.json")

def esc(s):
    return html.escape(str(s))

def clean_body(body):
    if isinstance(body, list):
        body = "".join(body)
    else:
        body = str(body)

    body = re.sub(r"${d+:([^}]*)}", lambda m: m.group(1), body)
    body = re.sub(r"${d+|([^}]*)|}", lambda m: m.group(1), body)
    body = re.sub(r"$0", "", body)
    body = re.sub(r"$d+", "", body)
    return body

def build_index():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=documentation.html">
  <title>Ru-Python</title>
</head>
<body>
  <p>Redirecting to <a href="documentation.html">documentation.html</a>...</p>
</body>
</html>
"""

def build_documentation():
    parts = []
    parts.append("""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Snippets документация</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f6f8fa; }
    .container { background: white; padding: 24px; border-radius: 12px; }
    .snippet { border: 1px solid #ddd; border-radius: 10px; padding: 16px; margin: 16px 0; background: #fafbfc; }
    .title { font-size: 28px; margin: 0 0 20px; }
    .name { font-size: 20px; font-weight: 700; margin: 0 0 10px; }
    .meta { margin: 6px 0; color: #555; line-height: 1.5; }
    pre { background: #1e1e1e; color: #fff; padding: 14px; border-radius: 6px; overflow-x: auto; margin: 12px 0 0; }
    code { font-family: Consolas, monospace; }
    a { color: #0969da; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <p><a href="index.html">← На главную</a></p>
    <h1 class="title">Snippets документация</h1>
""")

    count = 0
    if snippets_file.exists():
        data = json.loads(snippets_file.read_text(encoding="utf-8"))
        for name, item in data.items():
            description = item.get("description", "")
            body_text = clean_body(item.get("body", ""))

            parts.append(f"""
    <div class="snippet">
      <div class="name">{esc(name)}</div>
      <div class="meta"><b>Description:</b> {esc(description)}</div>
      <pre><code>{esc(body_text)}</code></pre>
    </div>
""")
            count += 1
    else:
        parts.append("<p>Файл rupy-words.json не найден.</p>")

    parts.append(f"""
    <p>Всего snippets: {count}</p>
  </div>
</body>
</html>
""")
    return "".join(parts)

Path("index.html").write_text(build_index(), encoding="utf-8")
Path("documentation.html").write_text(build_documentation(), encoding="utf-8")
print("Generated index.html and documentation.html")
