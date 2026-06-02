from pathlib import Path
import json
import html

snippets_file = Path("rus-python/snippets/rupy-words.json")

def esc(s):
    return html.escape(str(s))

def strip_placeholders(text):
    text = str(text)
    out = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch == "$" and i + 1 < n and text[i + 1] == "0":
            i += 2
            continue

        if ch == "$" and i + 1 < n and text[i + 1].isdigit():
            i += 2
            while i < n and text[i].isdigit():
                i += 1
            continue

        if ch == "$" and i + 1 < n and text[i + 1] == "{":
            j = i + 2
            while j < n and text[j].isdigit():
                j += 1

            if j < n and text[j] in [":", "|", "}"]:
                if text[j] == "}":
                    i = j + 1
                    continue

                delim = text[j]
                j += 1
                depth = 1
                start = j

                while j < n and depth > 0:
                    if text[j] == "$" and j + 1 < n and text[j + 1] == "{":
                        depth += 1
                        j += 2
                        continue
                    if text[j] == "}":
                        depth -= 1
                        if depth == 0:
                            content = text[start:j]
                            out.append(strip_placeholders(content))
                            i = j + 1
                            break
                    j += 1
                else:
                    out.append(text[i])
                    i += 1
                continue

        out.append(ch)
        i += 1

    return "".join(out)

def clean_body(body):
    if isinstance(body, list):
        return "
".join(strip_placeholders(line) for line in body)
    return strip_placeholders(body)

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
    parts = ["""<!DOCTYPE html>
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
    .meta { margin: 6px 0; color: #555; line-height: 1.5; white-space: pre-wrap; }
    pre { background: #1e1e1e; color: #fff; padding: 14px; border-radius: 6px; overflow-x: auto; margin: 12px 0 0; white-space: pre-wrap; }
    code { font-family: Consolas, monospace; white-space: pre-wrap; }
    a { color: #0969da; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <p><a href="index.html">← На главную</a></p>
    <h1 class="title">Snippets документация</h1>
"""]

    count = 0
    if snippets_file.exists():
        data = json.loads(snippets_file.read_text(encoding="utf-8"))
        for name, item in data.items():
            description = item.get("description", "")
            body_text = clean_body(item.get("body", ""))

            parts.append(f"""
    <div class="snippet">
      <div class="name">{esc(name)}</div>
      <div class="meta"><b>Description:</b>
{esc(description)}</div>
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
