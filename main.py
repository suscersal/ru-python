import os
import sys
import json
import re
import traceback

# Включаем поддержку ANSI цветов в Windows
# os.system('')

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

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
    # ПРОВЕРКА: Если файла нет, выходим сразу, не пытаясь его парсить
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
            py_lines.append(f"{prefix}print({' '.join(parts[1:])})")


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


            
        elif cmd == 'использовать':
            # Синтаксис: использовать модуль
            # Пример: использовать math -> import math
            module_name = "".join(parts[1:])
            py_lines.append(f"{prefix}import {module_name}")

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
            py_lines.append(f"{prefix}except Exception as ошибка:")
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
            # АВТО-СКОБКИ ДЛЯ ВЫЗОВОВ МЕТОДОВ И ФУНКЦИЙ
            # Если в строке есть пробел и это не присваивание (нет знака =)
            if ' ' in content and '=' not in content and '(' not in content:
                # Находим первое слово (это имя функции/метода)
                # и все остальное (это аргументы)
                func_part, args_part = content.split(' ', 1)
                
                # Если это похоже на вызов (например, бот.взять_вещь)
                if '.' in func_part or any(kw in func_part for kw in ['вывести', 'приветствие']):
                    content = f"{func_part.strip()}({args_part.strip()})"
            
            py_lines.append(f"{prefix}{content}")



    # Сохранение
    output_file = input_file.replace(".rupy", ".py")
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
    
    # Если аргумент передан (например, через VS Code), используем его
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # Если аргументов нет, ищем test.rupy в папке, где лежит сам main.py
        # os.path.dirname(__file__) — это путь к папке со скриптом
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_file = os.path.join(current_dir, "test.rupy")
    
    # Проверяем, существует ли файл, прежде чем запускать
    if os.path.exists(target_file):
        run_rupy(target_file)
    else:
        print(f"{RED}--- ОШИБКА ---")
        print(f"Файл не найден по пути: {target_file}{RESET}")
        print(f"{YELLOW}Положите файл 'test.rupy' в папку со скриптом или перетащите его на main.py{RESET}")
        # Чтобы окно консоли не закрывалось сразу
        # input("\nНажмите Enter, чтобы выйти...")

