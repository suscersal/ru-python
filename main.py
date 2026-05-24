import os
import sys
import json
import re
import traceback
import shutil
import pathlib
import requests




os.system('')

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


GITHUB_URL = "https://raw.githubusercontent.com/suscersal/ru-python/refs/heads/main/rus-python/modules.json"

def get_resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу (работает для исходного кода и для PyInstaller)"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def deep_merge(dict1, dict2):
    """Рекурсивно объединяет dict2 в dict1. Возвращает True при изменениях."""
    is_updated = False
    for key, value in dict2.items():
        if key not in dict1:
            dict1[key] = value
            is_updated = True
        elif isinstance(dict1[key], dict) and isinstance(value, dict):
            if deep_merge(dict1[key], value):
                is_updated = True
    return is_updated

def sync_with_github(local_path):
    """Сверяет локальный JSON с GitHub и добавляет новые модули/переводы"""
    print("--- Проверка обновлений модулей на GitHub... ---")
    try:
        # Читаем то, что уже лежит рядом с .exe
        with open(local_path, "r", encoding="utf-8") as f:
            local_data = json.load(f)
            
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(GITHUB_URL, headers=headers, timeout=5)
        
        if response.status_code == 200:
            github_data = response.json()
            # Умное слияние, чтобы не затереть локальные правки пользователя
            if deep_merge(local_data, github_data):
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(local_data, f, ensure_ascii=False, indent=2)
                print("--- Файл modules.json успешно обновлен с GitHub ---")
            else:
                print("--- Локальный файл уже содержит все переводы с GitHub ---")
        else:
            print(f"--- GitHub вернул статус: {response.status_code}. Работаем на локальном файле ---")
    except Exception as e:
        print(f"--- Не удалось обновиться с GitHub ({e}). Работаем на локальном файле ---")

def load_config():
    # Проверяем, запущен ли скрипт как скомпилированный EXE
    if getattr(sys, 'frozen', False):
        # Путь к файлу РЯДОМ с запущенным .exe
        exe_dir = os.path.dirname(sys.executable)
        external_json = os.path.join(exe_dir, "modules.json")
        
        # 1. Если файла НЕТ рядом с .exe -> копируем его из вшитых ресурсов (_MEIPASS)
        if not os.path.exists(external_json):
            embedded_json = get_resource_path("modules.json")
            if os.path.exists(embedded_json):
                try:
                    shutil.copy2(embedded_json, external_json)
                    print("--- Файл modules.json извлечен из EXE и сохранен рядом ---")
                except Exception as e:
                    print(f"# Ошибка при извлечении вшитого файла: {e}")
                    # Если скопировать не удалось (например, нет прав записи), читаем прямо из EXE
                    external_json = embedded_json
            else:
                return {} # Если и внутри EXE файла нет
                
        # 2. Если файл ЕСТЬ рядом с .exe -> сверяем его с GitHub
        else:
            sync_with_github(external_json)
            
        # Загружаем итоговый файл
        with open(external_json, "r", encoding="utf-8") as f:
            return json.load(f)
            
    # Если запущен как обычный .py скрипт
    else:
        # Ищем строго в папке исходников rus-python/modules.json
        source_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rus-python', 'modules.json')
        if os.path.exists(source_json):
            with open(source_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

MOD_CONFIG = load_config()


def get_russian_error(raw_error):
    raw_error_str = str(raw_error)
    try:
        # Пытаемся подгрузить базу ошибок, если файла нет — просто вернем текст
        if os.path.exists("errors.json"):
            with open("errors.json", "r", encoding="utf-8") as f:
                error_db = json.load(f)
            
            for pattern, translation in error_db.items():
                if re.search(pattern, raw_error_str, re.IGNORECASE):
                    res = translation
                    match = re.search(pattern, raw_error_str, re.IGNORECASE)
                    if match.groups():
                        for i, group in enumerate(match.groups(), 1):
                            res = res.replace(f"${i}", group)
                    return res
    except:
        pass
    return raw_error_str

def run_rupy(input_file):
    if not os.path.exists(input_file):
        print(f"{RED}--- ОШИБКА: Файл '{input_file}' не найден! ---{RESET}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    py_lines = []
    indent_level = 0
    
    for line in lines:
        # print(line)
        if line == '\n':
            py_lines.append('')
            continue
        raw_line = line.strip()
        # print(raw_line)
        # if not raw_line or raw_line.startswith("#"):
        #     py_lines.append("")
        #     continue
        
        # 1. Глобальные замены
        content = raw_line.replace('это.', 'self.')
        
        # 2. Умная обработка методов списков (сразу с записью и выходом из цикла)
        if '.добавить ' in content or '.удалить ' in content:
            # Превращаем в формат Python
            content = re.sub(r'([\w\[\]\.]+)\.добавить\s+(.+)', r'\1.append(\2)', content)
            content = re.sub(r'([\w\[\]\.]+)\.удалить\s+(.+)', r'\1.remove(\2)', content)
            # Закрываем скобку, если её нет
            if content.count('(') > content.count(')'): content += ')'
            
            # Пишем в файл с ТЕКУЩИМ отступом и идем к следующей строке
            py_lines.append(f"{'    ' * indent_level}{content}")
            continue

        parts = content.split()
        if not parts: continue
        cmd = parts[0]

        # 3. КОРРЕКЦИЯ ОТСТУПА (Важно: уменьшаем ДО создания префикса)
        if cmd in ['конец', 'отловить', 'иначе']:
            indent_level = max(0, indent_level - 1)

        prefix = "    " * indent_level
        
        # 4. ОБРАБОТКА КОМАНД
        if cmd == 'конец':
            # Добавляем pass только если блок был совсем пустой
            if py_lines and py_lines[-1].strip().endswith(':'):
                py_lines.append(f"{prefix}    pass")
            continue # pass добавили (или нет), идем дальше

        elif cmd == 'вывести':
            # 1. Берем всё, что идет после слова "вывести"
            expression = " ".join(parts[1:])
            
            # 2. Проходим по всем модулям в JSON и заменяем русские имена на английские
            for py_mod_name, mod_data in MOD_CONFIG.items():
                ru_mod_name = mod_data.get("ru-name")
                
                # Если в выражении есть "время."
                if f"{ru_mod_name}." in expression:
                    # Заменяем модуль: время. -> time.
                    expression = expression.replace(f"{ru_mod_name}.", f"{py_mod_name}.")
                    
                    # Заменяем функции из этого модуля: .время -> .time
                    sources = mod_data.get("sources", {})
                    for py_src, src_data in sources.items():
                        ru_src = src_data.get("ru-name")
                        if f".{ru_src}" in expression:
                            expression = expression.replace(f".{ru_src}", f".{py_src}")
            
            # 3. Записываем итоговый принт
            py_lines.append(f"{prefix}print({expression})")
            continue


        elif cmd == 'ввод':
            if len(parts) > 1:
                var_name = parts[1]
                # Собираем всё, что идет после имени переменной, в одну строку подсказки
                prompt = " ".join(parts[2:]).strip()
                # Если подсказки нет, оставляем пустые кавычки
                if not prompt: prompt = '""'
                py_lines.append(f"{prefix}{var_name} = input({prompt})")
            continue


        elif cmd == 'пусть':
            py_lines.append(f"{prefix}{' '.join(parts[1:])}")

        elif cmd == 'если':
            # Убираем слово 'если' и берем всё остальное как условие
            condition = " ".join(parts[1:]).strip()
            py_lines.append(f"{prefix}if {condition}:")
            indent_level += 1
            continue


            
        elif cmd == 'использовать' or 'использовать' in cmd:
            module_to_import = content.replace('использовать ', '').strip()
            found_in_config = False
            for py_mod_name, mod_data in MOD_CONFIG.items():
                if mod_data.get("ru-name") == module_to_import:
                    # Если нашли в JSON (например, "время"), пишем английский "import time"
                    # print(py_mod_name)
                    py_lines.append(f"{prefix}import {py_mod_name}")
                    found_in_config = True
                    break
            
            if not found_in_config:
                # Если в JSON модуля нет, оставляем как было (на случай обычных библиотек)
                py_lines.append(f"{prefix}import {module_to_import}")
            continue # Переходим к следующей строке кода

        elif cmd == 'из':
            # Синтаксис: из модуль использовать функция
            # Пример: из math использовать sqrt -> from math import sqrt
            if ' использовать ' in content:
                # Разделяем строку по ключевому слову ' использовать '
                from_part, import_part = content.split(' использовать ', 1)
                
                # Извлекаем имя модуля (убираем само слово 'из')
                module_name = from_part.replace('из', '', 1).strip()
                # Извлекаем то, что импортируем
                imported_items = import_part.strip()
                
                py_lines.append(f"{prefix}from {module_name} import {imported_items}")
            else:
                # Если синтаксис нарушен, пишем как есть
                py_lines.append(f"{prefix}{content}")
       
            
            
        elif cmd == 'иначе':
            py_lines.append(f"{prefix}else:")
            indent_level += 1

        elif cmd == 'попробовать':
            py_lines.append(f"{prefix}try:")
        
            indent_level += 1

        elif cmd == 'отловить':
            args_str = " ".join(parts[1:])
            
            if " как " in args_str:
                err_type_part, var_part = args_str.split(" как ", 1)
                err_type = err_type_part.strip()
                err_var = var_part.strip()
                
                if not err_type or err_type == "Ошибка":
                    err_type = "Exception"
                    
                py_lines.append(f"{prefix}except {err_type} as {err_var}:")
            else:
                remainder = args_str.strip()
                if remainder:
                    py_lines.append(f"{prefix}except {remainder}:")
                else:
                    py_lines.append(f"{prefix}except Exception:")
            
            indent_level += 1



        elif cmd == 'для':
            if ' в ' in content:
                py_lines.append(f"{prefix}for {parts[1]} in {parts[3]}:")
            else:
                py_lines.append(f"{prefix}for {parts[1]} in range({parts[-1]}):")
            indent_level += 1

        elif 'раза' in parts:
            var_name = parts[0] if len(parts) >= 3 else "_"
            count = parts[1] if len(parts) >= 3 else parts[0]
            py_lines.append(f"{prefix}for {var_name} in range({count}):")
            indent_level += 1

        elif cmd == 'класс':
            py_lines.append(f"{prefix}class {parts[1]}:")
            indent_level += 1

        elif cmd == 'создать':
            args = ", ".join(parts[1:])
            py_lines.append(f"{prefix}def __init__(self{', ' + args if args else ''}):")
            indent_level += 1

        elif cmd in ['функция', 'метод']:
            func_name = parts[1]
            args = ", ".join(parts[2:])
            if indent_level > 0:
                py_lines.append(f"{prefix}def {func_name}(self{', ' + args if args else ''}):")
            else:
                py_lines.append(f"{prefix}def {func_name}({args}):")
            indent_level += 1

        elif cmd == 'вернуть':
            py_lines.append(f"{prefix}return {' '.join(parts[1:])}")
            
        elif "#" in cmd:
            py_lines.append(f'{prefix}#{' '.join(parts[1:])}')
        else:
            is_processed = False
            for py_mod, mod_data in MOD_CONFIG.items():
                ru_mod = mod_data.get("ru-name")
                
                # Если строка начинается с "русский_модуль."
                if content.startswith(f"{ru_mod}."):
                    # 1. Заменяем имя модуля: время. -> time.
                    line_to_process = content.replace(f"{ru_mod}.", f"{py_mod}.", 1)
                    
                    # 2. Заменяем функции/классы из sources
                    sources = mod_data.get("sources", {})
                    for py_src, src_data in sources.items():
                        ru_src = src_data.get("ru-name")
                        if f".{ru_src}" in line_to_process:
                            line_to_process = line_to_process.replace(f".{ru_src}", f".{py_src}")
                    
                    # 3. Авто-скобки (если их нет)
                    if '(' not in line_to_process:
                        if ' ' in line_to_process:
                            f_name, args = line_to_process.split(' ', 1)
                            line_to_process = f"{f_name}({args})"
                        else:
                            line_to_process = f"{line_to_process}()"

                    py_lines.append(f"{prefix}{line_to_process}")
                    is_processed = True
                    break
        
            if is_processed: continue

            # АВТО-СКОБКИ ДЛЯ ВЫЗОВОВ МЕТОДОВ И ФУНКЦИЙ
            if ' ' in content and '=' not in content and '(' not in content:
                # Находим первое слово (это имя функции/метода)
                # и все остальное (это аргументы)
                func_part, args_part = content.split(' ', 1)
                
                # Если это похоже на вызов (например, бот.взять_вещь)
                if '.' in func_part or any(kw in func_part for kw in ['вывести', 'приветствие']):
                    content = f"{func_part.strip()}({args_part.strip()})"
            
            py_lines.append(f"{prefix}{content}")



    # Сохранение
    input_path = pathlib.Path(input_file)
    output_file = input_path.with_suffix('.py')
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(py_lines))
    
    print(f"{GREEN}--- Трансляция завершена ({output_file}) ---{RESET}")

    # Запуск
    print(f"{RED}--- Запуск... ---{RESET}\n")    
    try:
        full_code = "\n".join(py_lines)
        # prefix(full_code)
        # Компилируем код, чтобы Python знал "имя" файла и номера строк
        # Это магия, которая свяжет ошибки с твоим файлом
        compiled_code = compile(full_code, input_file, 'exec')
        
        exec(compiled_code, {})
        print(f"\n{GREEN}>>> Успешно завершено{RESET}")
        
    except Exception as e:
        print(f"\n{RED}--- ОШИБКА ---")
        
        # 1. Если это ошибка синтаксиса (отступы, скобки)
        if isinstance(e, SyntaxError):
            print(f"Строка: {e.lineno}")
            print(f"Код: {e.text.strip() if e.text else 'неизвестно'}")
        
        # 2. Если это ошибка во время работы (деление на ноль и т.д.)
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.extract_tb(exc_traceback)
            relevant_entry = None
            for entry in reversed(tb):
                if entry.filename == input_file:
                    relevant_entry = entry
                    break
            
            if relevant_entry:
                print(f"Строка: {relevant_entry.lineno}")
                print(f"Код: {relevant_entry.line.strip()}")
            
        print(f"Что случилось: {get_russian_error(e)}{RESET}")



if __name__ == "__main__":
    import sys
    param = None
    #проверка на запуск .exe
    if len(sys.argv) > 1:
        if '-' not in sys.argv[1]:
            target_file = sys.argv[1]
        else:
            param = sys.argv[1:]
    else:

        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_file = os.path.join(current_dir, "test.rupy")
    
    if param == None:
        if os.path.exists(target_file):
            run_rupy(target_file)
        else:
            print(f"{RED}--- ОШИБКА ---")
            print(f"Файл не найден по пути: {target_file}{RESET}")
            print(f"{YELLOW}Положите файл 'test.rupy' в папку со скриптом или перетащите его на main.py{RESET}")

