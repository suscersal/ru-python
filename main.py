import os
import sys
import json
import re
import traceback
import shutil
import pathlib
import requests
import subprocess
import argparse


sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')


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


def safe_sub(pattern, replacement, text):
    # Группа 1 ловит кавычки. Группа 2 ловит ваш исходный паттерн.
    # Мы убираем \b из начала паттерна, если там есть точка (например, \.вывести)
    full_pattern = r'("[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\')|(' + pattern + ')'
    
    def re_callback(match):
        if match.group(1):
            return match.group(1)  # Найдена строка в кавычках — возвращаем как есть
        return replacement         # Найдено ключевое слово — заменяем
        
    return re.sub(full_pattern, re_callback, text)
    

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

def run_rupy(input_file,log_file,build,build_name=None,extra_files=None,icon=None,translate_only=False,debug=False):
    if not os.path.exists(input_file):
        print(f"{RED}--- ОШИБКА: Файл '{input_file}' не найден! ---{RESET}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    py_lines = []
    all_defs = []
    all_vars = []
    
    
    indent_level = 0
    for line in lines:
        if line == '\n':
            py_lines.append('')
            continue
        raw_line = line.strip()
        raw_line = re.sub(r'\bформ(?=["\'])', 'f', raw_line)
        raw_line = re.sub(r'\bфунк\b', 'lambda', raw_line)
        
        if line.strip().startswith('#'):
            #print(line)
            py_lines.append(line[:len(line)-1])
            continue
        
        if "#" not in raw_line:
    # Заменяем "это.", обходя кавычки
            content = safe_sub(r'это\.', 'self.', raw_line)
    
    # Замена логических операторов
            if 'и' not in all_vars and 'пусть и' not in content and 'как' not in content:
               content = safe_sub(r'\bи\b', 'and', content)
        
            content = safe_sub(r'\bили\b', 'or', content)
            content = safe_sub(r'\bне\b', 'not', content)

    # Замена методов работы с файлами
            content = safe_sub(r'\.вывести\b', '.write', content)
            content = safe_sub(r'\.прочитать\b', '.read', content)
            content = safe_sub(r'\.прочитать_строку\b', '.readline', content)
    
    # Замена булевых констант
            content = safe_sub(r'\bИстина\b', 'True', content)
            content = safe_sub(r'\bЛожь\b', 'False', content)
            
  
            content = safe_sub(r'\b(больше\s+(или|либо)\s+равно|не\s+меньше)\b', ">=", content)
            content = safe_sub(r'\b(меньше\s+(или|либо)\s+равно|не\s+больше)\b', "<=", content)
            content = safe_sub(r'\b(не\s+равно|отличается\s+от)\b', "!=", content)
            content = safe_sub(r'\bбольше\b', ">", content)
            content = safe_sub(r'\bменьше\b', "<", content)
            content = safe_sub(r'\bравно\b', "==", content)

            
            
        
        
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

        elif line.strip().startswith('#'):
          #  print(parts)
            py_lines.append(f'{prefix}#{' '.join(parts[1:])}')
            #print(py_lines[len(py_lines)-1])
            #print("комент")
            continue
        elif cmd == 'вывести':
            def world_in_worlds_list(world,l):
                for i in l:
                    if world in i:
                        return True
                return False
            # Если строка начинается с комментария (после удаления пробелов), пропускаем её
            if line.strip().startswith('#'):
               continue
            
            expression = " ".join(parts[1:])
            
            if world_in_worlds_list('self.',parts):
                py_lines.append(f"{prefix}print({expression})")
                continue
                
           # print(expression,parts,len(py_lines),cmd)
            
            # Проходим по всем модулям в JSON
            for py_mod_name, mod_data in MOD_CONFIG.items():
                ru_mod_name = mod_data.get("ru-name")
                sources = mod_data.get("sources", {})
                
                # 1. Заменяем вызовы через точку (время.спать -> time.sleep)
                if f"{ru_mod_name}." in expression:
                    expression = expression.replace(f"{ru_mod_name}.", f"{py_mod_name}.")
   
                    
                    for py_src, src_data in sources.items():
                        ru_src = src_data.get("ru-name")
                        # Безопасная замена функции после точки
                        expression = re.sub(rf"\.{ru_src}\b", f".{py_src}", expression)
                        
                
                # 2. Прямой вызов функции (спать() -> sleep())
                # Ищем только ЦЕЛОЕ СЛОВО, чтобы не сломать 
                else:
                    for py_src, src_data in sources.items():
                        ru_src = src_data.get("ru-name")
                        # \b гарантирует, что мы заменим "время", но не тронем часть слова 
                        expression = re.sub(rf"\b{ru_src}\b", py_src, expression)
 
            #print(expression+"\n")
            # Записываем итоговый принт
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
            #print(parts,all_defs)
            all_vars.append(parts[1])
            if parts[3] not in all_defs:
               py_lines.append(f"{prefix}{' '.join(parts[1:])}")
            else:
                py_lines.append(f"{prefix}{' '.join(parts[1:4])}({','.join(parts[4:])})")
                
        

        elif cmd == 'если':
            condition = " ".join(parts[1:]).strip()
            py_lines.append(f"{prefix}if {condition}:")
            # Открываем блок: увеличиваем отступ для кода внутри 'если'
            indent_level += 1
            continue

        
        elif cmd == 'иначе' and len(parts) > 1 and parts[1] == 'если':
                    
            condition = " ".join(parts[2:]).strip()
            py_lines.append(f"{prefix}elif {condition}:")
            
            # 3. Открываем новый блок для кода внутри 'иначе если'
            indent_level += 1
            continue

        # Ветка для обычного "иначе"
        elif cmd == 'иначе':
            py_lines.append(f"{prefix}else:")
            
            # 3. Открываем новый блок для кода внутри 'иначе'
            indent_level += 1
            continue
         

            # В НАЧАЛЕ ЦИКЛА ОБРАБОТКИ СТРОКИ:
        elif cmd == 'из':
            # Пример: из время использовать время как в
            # Безопасно убираем начальное "из " из строки content, если оно там осталось
            clean_content = content.replace('из ', '', 1).strip() if content.startswith('из ') else content.strip()
            
            if ' использовать ' in clean_content:
                from_part, import_part = clean_content.split(' использовать ', 1)
                module_name = from_part.strip()
                
                # 1. Переводим имя модуля
                target_mod_data = None
                for py_mod_name, mod_data in MOD_CONFIG.items():
                    if mod_data.get("ru-name") == module_name:
                        module_name = py_mod_name
                        target_mod_data = mod_data
                        break
                
                # 2. Разбираемся с "как" внутри импортируемой части
                if ' как ' in import_part:
                    imported_items, alias = import_part.split(' как ', 1)
                    imported_items = imported_items.strip()
                    alias = alias.strip()
                    
                    # Переводим функцию из sources
                    if target_mod_data and "sources" in target_mod_data:
                        for py_src, src_data in target_mod_data["sources"].items():
                            if src_data.get("ru-name") == imported_items:
                                imported_items = py_src
                                break
                                
                    py_lines.append(f"{prefix}from {module_name} import {imported_items} as {alias}")
                else:
                    imported_items = import_part.strip()
                    if target_mod_data and "sources" in target_mod_data:
                        for py_src, src_data in target_mod_data["sources"].items():
                            if src_data.get("ru-name") == imported_items:
                                imported_items = py_src
                                break
                                
                    py_lines.append(f"{prefix}from {module_name} import {imported_items}")
            else:
                py_lines.append(f"{prefix}{content}")
            continue



        elif cmd == 'использовать':
            # Пример: использовать время как д
            # Очищаем content от слова "использовать ", если оно там есть
            clean_content = content.replace('использовать ', '', 1).strip() if content.startswith('использовать ') else content.strip()
            
            if ' как ' in clean_content:
                module_to_import, alias = clean_content.split(' как ', 1)
                module_to_import = module_to_import.strip()
                alias = alias.strip()
                
                found_in_config = False
                for py_mod_name, mod_data in MOD_CONFIG.items():
                    if mod_data.get("ru-name") == module_to_import:
                        py_lines.append(f"{prefix}import {py_mod_name} as {alias}")
                        found_in_config = True
                        break
                
                if not found_in_config:
                    py_lines.append(f"{prefix}import {module_to_import} as {alias}")
            
            else:
                module_to_import = clean_content
                found_in_config = False
                for py_mod_name, mod_data in MOD_CONFIG.items():
                    if mod_data.get("ru-name") == module_to_import:
                        py_lines.append(f"{prefix}import {py_mod_name}")
                        found_in_config = True
                        break
                
                if not found_in_config:
                    py_lines.append(f"{prefix}import {module_to_import}")
            continue



        elif cmd == 'как':
            # Синтаксис: использовать время как в -> первая команда перехватит "использовать",
            # но если ваша архитектура бьет строку так, что "как" становится отдельной командой:
            # Пример: использовать pandas как pd
            if 'использовать ' in content and ' как ' in content:
                base_part, alias = content.split(' как ', 1)
                alias = alias.strip()
                module_to_import = base_part.replace('использовать ', '').strip()
                
                found_in_config = False
                for py_mod_name, mod_data in MOD_CONFIG.items():
                    if mod_data.get("ru-name") == module_to_import:
                        py_lines.append(f"{prefix}import {py_mod_name} as {alias}")
                        found_in_config = True
                        break
                
                if not found_in_config:
                    py_lines.append(f"{prefix}import {module_to_import} as {alias}")
            else:
                py_lines.append(f"{prefix}{content}")
            continue




        elif 'открыть' in cmd:
            # Исходная строка: открыть("лог.txt", "запись") как файл
            line_content = content.strip()
            
            # 1. Заменяем русские режимы на понятные для Python латинские буквы
            line_content = line_content.replace('"запись"', '"w"').replace("'запись'", "'w'")
            line_content = line_content.replace('"чтение"', '"r"').replace("'чтение'", "'r'")
            line_content = line_content.replace('"добавление"', '"a"').replace("'добавление'", "'a'")
            
            # 2. Автоматически добавляем поддержку UTF-8 перед закрытием скобки функции open
            if ')' in line_content:
                # Находим последнюю скобку в вызове открыть(...) и вставляем кодировку
                line_content = line_content.replace(')', ', encoding="utf-8")', 1)
            
            # 3. Заменяем первое слово "открыть" на "open"
            line_content = re.sub(rf"\bоткрыть\b", "open", line_content, count=1)
            
            # 4. Заменяем ключевое слово "как" на английское "as"
            line_content = re.sub(rf"\bкак\b", "as", line_content)
            
             # 5. Формируем конструкцию с "with" и двоеточием в конце
            py_lines.append(f"{prefix}with {line_content}:")
            
            indent_level += 1
            continue

     
            
        

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
                all_vars.append(err_var)
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

            elif 'раз' in parts or 'раза' in parts:
                py_lines.append(f"{prefix}for {parts[1]} in range({parts[2]}):")
            
            else:
                py_lines.append(f"{prefix}for {parts[1]} in range({parts[-1]}):")
                
            indent_level += 1

        elif 'раз' in parts:
            var_name = parts[0] if len(parts) >= 3 else "_"
            count = parts[1] if len(parts) >= 3 else parts[0]
            
            py_lines.append(f"{prefix}for {var_name} in range({count}):")
            indent_level += 1

        elif cmd == 'пропустить':
            py_lines.append(f"{prefix}pass")

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
            all_defs.append(func_name)
            indent_level += 1

        elif cmd == 'вернуть':
            py_lines.append(f"{prefix}return {' '.join(parts[1:])}")
            
        
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
            if '=' not in content and '(' not in content:
                # Проверяем, есть ли вообще аргументы (разделенные пробелом)
                if ' ' in content:
                    # Находим первое слово и все остальное
                    func_part, args_part = content.split(' ', 1)
        
                    # Если это похоже на вызов (например, бот.взять_вещь)
                    if '.' in func_part or any(kw in func_part for kw in ['вывести', 'приветствие']):
                        content = f"{func_part.strip()}({args_part.strip()})"
                else:
                    # Если пробела нет, значит это вызов функции без аргументов
                    # Например, строка "приветствие" превратится в "приветствие()"
                    if '.' in content or any(kw in content for kw in ['вывести', 'приветствие']):
                        content = f"{content.strip()}()"

            py_lines.append(f"{prefix}{content}")

     



    # Сохранение
    input_path = pathlib.Path(input_file)
    output_file = input_path.with_suffix('.py')
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(py_lines))
    
    print(f"{GREEN}--- Трансляция завершена ({output_file}) ---{RESET}")
    if translate_only:
        print(f"{YELLOW}Режим только трансляции: запуск кода пропущен{RESET}")
        return
    if debug:
        print(f"{YELLOW}Режим debug: запуск с отладкой{RESET}")
    # тут вызывай функцию отладки
        from modules.debug.core import run_debug
        run_debug(input_file, str(output_file))
        return 
        
        
    if build:
        print(f"{YELLOW} Запущена компиляция программы: {input_file} в {input_path.with_suffix('.exe')} ")

        python_path = find_local_python()
       # print(python_path)

        if "не найден" in python_path:
            print(f"{RED}Ошибка: Python не найден, компиляция невозможна.{RESET}")
            return

        # Формируем команду PyInstaller
        pyinstaller_cmd = ["python", "-m", "PyInstaller", "--onefile"]

        # Параметр --name: имя выходного .exe
        if build_name:
            pyinstaller_cmd += ["--name", build_name]
            print(f"{YELLOW} Имя выходного файла: {build_name}.exe {RESET}")
       
        if icon:
            if icon.endswith(".ico"):
                pyinstaller_cmd += ["--icon", icon]
                print(f"{YELLOW} Иконка выходного файла: {icon} {RESET}")
            else:
                print(f"{RED} Иконка должна быть .ico{RESET}")
                
                
            
             

        # Параметр --add-data: дополнительные файлы, включаемые в сборку
        # PyInstaller требует формат SOURCE:DEST (через двоеточие)
        # Если пользователь передал SOURCE;DEST (старый Windows-формат) — автоматически исправляем
        if extra_files:
            for ef in extra_files:
                ef_fixed = ef.replace(";", ":")
                pyinstaller_cmd += [f"--add-data={ef_fixed}"]
                print(f"{YELLOW} Добавлен файл в сборку: {ef_fixed} {RESET}")

        pyinstaller_cmd.append(str(output_file))
        print(f"{GREEN} Команда компиляции: {pyinstaller_cmd} {RESET}")
        try:
            result = subprocess.run(
                pyinstaller_cmd,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"{GREEN}Компиляция завершена успешно!{RESET}")
            else:
                print(f"{RED}Ошибка при компиляции:{RESET}")
                print(result.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"{RED}Не удалось запустить PyInstaller: {e}{RESET}")

        return
    # Запуск
    from contextlib import redirect_stdout


    # Вспомогательный объект-разветвитель (всего 3 строчки кода)
    class Tee:
        def __init__(self, file1, file2): 
            self.f1, self.f2 = file1, file2
        
        def write(self, data): 
            self.f1.write(data)
            self.f2.write(data)
            # МАГИЯ: принудительно заставляем текст появиться на экране прямо сейчас
            self.f1.flush()
            self.f2.flush()
        
        def flush(self): 
            self.f1.flush()
            self.f2.flush()
        
    # Защита: логирование включено ТОЛЬКО если log_file существует,
    # является строкой, не равен None и не пустой
    is_logging_enabled = False
    if log_file is not None:
        if isinstance(log_file, str) and log_file.strip() != "":
            is_logging_enabled = True
             
    print(f"{RED}--- Запуск... ---{RESET}\n")    
    
    # 1. СТРОГАЯ ПРОВЕРКА: Проверяем, что log_file существует, это строка и она не пустая
    is_logging_enabled = False
    if log_file is not None:
        if isinstance(log_file, str) and log_file.strip() != "":
            is_logging_enabled = True

    try:
        full_code = "\n".join(py_lines)
        # Компилируем код, чтобы Python знал "имя" файла и номера строк
        compiled_code = compile(full_code, input_file, 'exec')
        
        # 2. Если логирование включено — пишем в Tee, иначе — стандартно в консоль
        if is_logging_enabled:
            with open(log_file, "a", encoding="utf-8") as f:
                with redirect_stdout(Tee(sys.__stdout__, f)):
                    exec(compiled_code, {})
                    print(f"\n{GREEN}>>> Успешно завершено{RESET}")
        else:
            exec(compiled_code, {})
            print(f"\n{GREEN}>>> Успешно завершено{RESET}")
            
    except Exception as e:
        # Внутренняя функция, чтобы не дублировать код вывода ошибок дважды
        def print_error():
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

        # 3. Пишем ошибку в зависимости от флага логирования
        if is_logging_enabled:
            with open(log_file, "a", encoding="utf-8") as f:
                with redirect_stdout(Tee(sys.__stdout__, f)):
                    print_error()
        else:
            print_error()
            

    

    
def find_python_in_registry():
    import winreg
    """Ищет путь к python.exe через системный реестр Windows."""
    # Проверяем две основные ветки реестра: текущего пользователя и системную
    registry_roots = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
    relative_path = r"SOFTWARE\Python\PythonCore"
    
    for root_key in registry_roots:
        try:
            with winreg.OpenKey(root_key, relative_path) as core_key:
                # Перебираем установленные версии (например, '3.10', '3.11')
                for i in range(winreg.QueryInfoKey(core_key)[0]):
                    version_name = winreg.EnumKey(core_key, i)
                    install_path_str = rf"{relative_path}\{version_name}\InstallPath"
                    
                    try:
                        with winreg.OpenKey(root_key, install_path_str) as ip_key:
                            # Извлекаем прямой путь к исполняемому файлу
                            exe_path, _ = winreg.QueryValueEx(ip_key, "ExecutablePath")
                            if os.path.exists(exe_path):
                                return exe_path
                    except OSError:
                        continue
        except OSError:
            continue
    return None

def find_local_python():
    if not getattr(sys, 'frozen', False):
        return sys.executable
    """Основная функция поиска Python на ПК."""
    # Шаг 1: Пробуем найти через реестр Windows
    registry_path = find_python_in_registry()
    if registry_path:
        return registry_path

    # Шаг 2: Если в реестре нет, сканируем стандартную папку AppData
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    if local_app_data:
        python_dir = os.path.join(local_app_data, 'Programs', 'Python')
        if os.path.exists(python_dir):
            for root, dirs, files in os.walk(python_dir):
                if 'python.exe' in files:
                    full_path = os.path.join(root, 'python.exe')
                    if os.path.exists(full_path):
                        return full_path
                        
    return "Python не найден на ПК"

# Проверка работы функции
#print("Найденный путь к Python:", find_local_python())


if __name__ == "__main__":

    # 1. Определение текущей директории для .py и .exe
    if getattr(sys, 'frozen', False):
        current_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Настройка argparse
    parser = argparse.ArgumentParser(
        description="Интерпретатор RuPy — запуск .rupy файлов с русским синтаксисом",
        epilog="Пример: rupy script.rupy --log_file out.log",
        prog="rupy"
    )

    parser.add_argument(
        "file",
        type=str,
        nargs="?",
        default=os.path.join(current_dir, "test.rupy"),
        help="Путь к .rupy файлу для выполнения (по умолчанию: test.rupy рядом со скриптом)"
    )
    parser.add_argument(
        "--log_file", "-l",
        type=str,
        default=None,
        help="Путь к файлу для записи лога выполнения"
    )
    parser.add_argument(
        "--build", "-b",
        action="store_true",
        default=False,
        help="Скомпилировать .rupy файл в .exe через PyInstaller"
    )
    parser.add_argument(
        "--name", "-n",
        type=str,
        default=None,
        help="Имя выходного .exe файла при сборке"
    )
    parser.add_argument(
        "--add-data", "--add_data",
        type=str,
        dest="extra_files",
        action="append",
        default=[],
        help="Дополнительные файлы для включения в сборку (можно указывать несколько раз)"
    )
    parser.add_argument(
        "--icon", "-i",
        type=str,
        default=None,
        help="Путь к .ico файлу иконки для сборки"
    )
    parser.add_argument(
        "--install",
        type=str,
        metavar="МОДУЛЬ",
        nargs="?",
        const="__setup__",
        default=None,
        help="Установить Python-модуль через pip. Без аргумента — настройка ассоциации файлов"
    )
    parser.add_argument(
         "-m", "--module",
         type=str,
        default=None,
        help="Запустить встроенный модуль (например: build_gui)"
    )
    parser.add_argument(
    "--translate-only", "-t",
    action="store_true",
    default=False,
    help="Только трансляция .rupy → .py без запуска кода"
)
    parser.add_argument(
    "--debug", "-d",
    action="store_true",
    default=False,
    help="Запуск отладки .rupy → .py с показом переменных и брейкпоинтов"
)


    args = parser.parse_args()
    
    if args.module == "build_gui":
        import sys
        import os
        # Добавляем корневую папку в путь поиска модулей
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from modules.build_gui import run
        run()
        sys.exit(0)

    # 3. Логика выполнения
    if args.install is not None:
        print("Запущена установка ассоциации файлов и модулей...")

        python_path = find_local_python()
        print(f"Найденный интерпретатор для установки: {python_path}")

        if "не найден" in python_path:
            print(f"{RED}Ошибка: Не удалось установить модуль. Python не найден в системе.{RESET}")
        elif args.install == "__setup__":
            print(f"{YELLOW}Флаг --install запущен без указания модуля. Выполняется стандартная настройка.{RESET}")
            # Здесь можно добавить код настройки ассоциации файлов .rupy
        else:
            module_name = args.install
            print(f"Установка модуля {module_name} через pip...")
            try:
                result = subprocess.run(
                    [python_path, "-m", "pip", "install", module_name],
                    capture_output=False,
                    text=True
                )
                if result.returncode == 0:
                    print(f"\n{YELLOW}Модуль {module_name} успешно установлен!{RESET}")
                else:
                    print(f"\n{RED}Произошла ошибка при установке модуля.{RESET}")
            except Exception as e:
                print(f"{RED}Не удалось запустить pip: {e}{RESET}")
        sys.exit(0)

    # 4. Обработка файла
    if args.debug:
        debug = True
    else:
        debug = False
    
    target_file = args.file
    
    # Проверяем существование файла
    if not os.path.exists(target_file):
        # Если файл не существует и это не test.rupy, пробуем добавить расширение .rupy
        if not target_file.endswith('.rupy'):
            test_file = target_file + '.rupy'
            if os.path.exists(test_file):
                target_file = test_file
            else:
                # Если это test.rupy по умолчанию и его нет, показываем ошибку
                if target_file == os.path.join(current_dir, "test.rupy"):
                    print(f"{RED}--- ОШИБКА ---")
                    print(f"Файл test.rupy не найден в папке: {current_dir}{RESET}")
                    print(f"{YELLOW}Создайте файл test.rupy или укажите путь к существующему .rupy файлу{RESET}")
                    sys.exit(1)
                else:
                    print(f"{RED}--- ОШИБКА ---")
                    print(f"Файл не найден по пути: {target_file}{RESET}")
                    print(f"{YELLOW}Проверьте правильность пути или создайте файл .rupy{RESET}")
                    sys.exit(1)
    
    # Если файл существует, запускаем
    run_rupy(
        target_file,
        args.log_file,
        args.build,
        args.name,
        args.extra_files or None,
        args.icon,
        args.translate_only,
        debug,  
    )