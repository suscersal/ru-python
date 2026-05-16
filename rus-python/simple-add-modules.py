import os
import sys
import subprocess
import importlib
import inspect
import json
import re
import time

# Автоматическая установка базовых библиотек
required_libraries = {
    "deep_translator": "deep-translator",
    "wordsegment": "wordsegment"
}

for module_name, pip_name in required_libraries.items():
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError:
        print(f"Библиотека '{pip_name}' не найдена. Начинаю автоматическую установку...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            print(f"Установка {pip_name} успешно завершена!\n")
        except Exception as e:
            print(f"Ошибка при автоматической установке {pip_name}: {e}")
            print(f"Пожалуйста, установите ее вручную: pip install {pip_name}")
            sys.exit(1)

from deep_translator import GoogleTranslator
import wordsegment
wordsegment.load()  # Загрузка словаря для разделения слов

file_path = 'modules.json'

def has_english_letters(text):
    return bool(re.search('[a-zA-Z]', text))
    
def has_censoured(text):
    
    ban_worlds = [
        "секс",
    ]
    
    for ban_world in ban_worlds:
        if ban_world in text:
            return True
        
    return False
            



def prepare_technical_text(text):
    """
    Максимально расширенная база сокращений для превращения технических
    имен и аббревиатур в полноценные английские фразы.
    """
    # 1. Очистка спецсимволов и разделение snake_case
    text = text.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    
    # 2. Разделение CamelCase (например, IsNaN -> Is Na N)
    text = re.sub(r'(?<!^)(?=[A-Z])', ' ', text)
    
    words = text.lower().split()
    segmented_words = []
    
    # МАКСИМАЛЬНЫЙ СЛОВАРЬ ТЕХНИЧЕСКИХ СОКРАЩЕНИЙ
    abbreviations = {
        # --- МАТЕМАТИКА, СТАТИСТИКА И ГЕОМЕТРИЯ (math, cmath, numpy) ---
        "sqrt": ["calculate", "square", "root"],
        "is": ["is"],
        "pow": ["raise", "to", "power"],
        "abs": ["absolute", "value"],
        "fabs": ["floating", "point", "absolute", "value"],
        "ceil": ["round", "up", "ceiling"],
        "floor": ["round", "down", "floor"],
        "gcd": ["greatest", "common", "divisor"],
        "lcm": ["least", "common", "multiple"],
        "hypot": ["calculate", "hypotenuse"],
        "log": ["natural", "logarithm"],
        "log10": ["base", "10", "logarithm"],
        "log2": ["base", "2", "logarithm"],
        "exp": ["exponential", "function"],
        "expm1": ["exponential", "minus", "1"],
        "sin": ["sine"], "cos": ["cosine"], "tan": ["tangent"],
        "asin": ["arcsine"], "acos": ["arccosine"], "atan": ["arctangent"],
        "atan2": ["arctangent", "two", "arguments"],
        "sinh": ["hyperbolic", "sine"], "cosh": ["hyperbolic", "cosine"], "tanh": ["hyperbolic", "tangent"],
        "asinh": ["inverse", "hyperbolic", "sine"], "acosh": ["inverse", "hyperbolic", "cosine"], "atanh": ["inverse", "hyperbolic", "tangent"],
        "degrees": ["convert", "to", "degrees"], "radians": ["convert", "to", "radians"],
        "prod": ["product", "of", "elements"],
        "sum": ["calculate", "sum"],
        "mod": ["modulo", "remainder"],
        "fmod": ["floating", "point", "modulo"],
        "divmod": ["division", "and", "remainder"],
        "nan": ["not", "a", "number"],
        "isnan": ["is", "not", "a", "number"],
        "inf": ["infinity"],
        "isinf": ["is", "infinity"],
        "isfinite": ["is", "finite"],
        "std": ["standard", "deviation"],
        "var": ["variance"],
        "cov": ["covariance"],
        "corr": ["correlation"],
        "cumprod": ["cumulative", "product"],
        "cumsum": ["cumulative", "sum"],
        "diff": ["calculate", "difference"],
        
        # --- ФАЙЛОВАЯ СИСТЕМА И ОС (os, sys, shutil, pathlib) ---
        "mkdir": ["make", "directory"],
        "makedirs": ["make", "directories", "recursively"],
        "rmdir": ["remove", "directory"],
        "removedirs": ["remove", "directories", "recursively"],
        "listdir": ["list", "directory", "contents"],
        "scandir": ["scan", "directory", "contents"],
        "cwd": ["current", "working", "directory"],
        "getcwd": ["get", "current", "working", "directory"],
        "chdir": ["change", "working", "directory"],
        "environ": ["environment", "variables"],
        "getenv": ["get", "environment", "variable"],
        "putenv": ["set", "environment", "variable"],
        "exec": ["execute", "program"],
        "execv": ["execute", "program", "with", "arguments"],
        "stderr": ["standard", "error", "output"],
        "stdin": ["standard", "input"],
        "stdout": ["standard", "output"],
        "argv": ["argument", "values"],
        "chown": ["change", "owner"],
        "chmod": ["change", "permissions", "mode"],
        "fd": ["file", "descriptor"],
        "lstat": ["link" "state"],
        
        # --- РАБОТА С СЕТЬЮ И ДАННЫМИ (socket, json, urllib, requests) ---
        "json": ["javascript", "object", "notation"],
        "dumps": ["dump", "to", "string"],
        "loads": ["load", "from", "string"],
        "dump": ["write", "to", "file"],
        "load": ["read", "from", "file"],
        "url": ["web", "address", "url"],
        "req": ["network", "request"],
        "res": ["network", "response"],
        "resp": ["network", "response"],
        "msg": ["message"],
        "recv": ["receive", "data"],
        "addr": ["network", "address"],
        "buf": ["temporary", "buffer"],
        "src": ["source"],
        "dst": ["destination"],
        "dest": ["destination"],
        "ctx": ["context"],
        "cfg": ["configuration"],
        "config": ["configuration"],
        
        # --- СТРОКИ, ТЕКСТ И РЕГУЛЯРНЫЕ ВЫРАЖЕНИЯ (re, string) ---
        "re": ["regular", "expression"],
        "regex": ["regular", "expression"],
        "sub": ["substitute", "text"],
        "subn": ["substitute", "text", "with", "count"],
        "match": ["find", "exact", "match"],
        "search": ["search", "pattern"],
        "findall": ["find", "all", "matches"],
        "finditer": ["find", "all", "matches", "as", "iterator"],
        "str": ["string", "text"],
        "char": ["character"],
        "ascii": ["ascii", "encoding"],
        "repr": ["string", "representation"],
        "alnum": ["alphanumeric", "characters"],
        "alpha": ["alphabetic", "letters"],
        "digit": ["numeric", "digits"],
        
        # --- ДАТА И ВРЕМЯ (datetime, time) ---
        "dt": ["date", "time"],
        "ts": ["timestamp"],
        "tz": ["time", "zone"],
        "tzinfo": ["time", "zone", "information"],
        "utcnow": ["universal", "current", "time"],
        "strftime": ["format", "time", "as", "string"],
        "strptime": ["parse", "time", "from", "string"],
        
        # --- СЛУЖЕБНЫЕ И ОБЩИЕ СЛОВА (базовый синтаксис) ---
        "idx": ["index", "number"],
        "num": ["number"],
        "cnt": ["count"],
        "len": ["calculate", "length"],
        "iter": ["create", "iterator"],
        "init": ["initialize", "object"],
        "attr": ["object", "attribute"],
        "getattr": ["get", "object", "attribute"],
        "setattr": ["set", "object", "attribute"],
        "hasattr": ["check", "object", "attribute"],
        "delattr": ["delete", "object", "attribute"],
        "cls": ["class", "type"],
        "func": ["executable", "function"],
        "arg": ["argument"],
        "args": ["arguments", "list"],
        "kwargs": ["keyword", "arguments", "dictionary"],
        "err": ["system", "error"],
        "exc": ["runtime", "exception"],
        "ptr": ["memory", "pointer"],
        "tbl": ["data", "table"],
        "col": ["table", "column"],
        "impl": ["implementation"]
    }
    
    for w in words:
        if w in abbreviations:
            segmented_words.extend(abbreviations[w])
        else:
            seg = wordsegment.segment(w)
            if seg:
                segmented_words.extend(seg)
            else:
                segmented_words.append(w)
                
    return " ".join(segmented_words)


def translate_as_action(eng_word, translator_instance):
    clean_phrase = prepare_technical_text(eng_word)
    

    try:
        raw_translation = translator_instance.translate(clean_phrase).lower()
        

        raw_translation = re.sub(r'\b(это|является|сделать)\b', '', raw_translation)
        return " ".join(raw_translation.split())
    except Exception as e:
        raise e

def print_module_statistics(data_dict, mod_name):
    if mod_name not in data_dict:
        print(f"\nМодуль '{mod_name}' отсутствует в базе данных.")
        return

    try:
        imported_module = importlib.import_module(mod_name)
        all_elements = []
        for name, _ in inspect.getmembers(imported_module):
            if not name.startswith('_'):
                all_elements.append(name)
    except Exception:
        all_elements = list(data_dict[mod_name].get("sources", {}).keys())

    sources = data_dict[mod_name].get("sources", {})
    translated_words = []
    missing_words = []

    for word in all_elements:
        if word in sources and sources[word].get("ru-name"):
            ru_word = sources[word].get("ru-name")
            if not has_english_letters(ru_word):
                translated_words.append((word, ru_word))
                continue
        missing_words.append(word)

    total = len(all_elements)
    translated_count = len(translated_words)
    percent = (translated_count / total * 100) if total > 0 else 0

    col_eng, col_ru = 25, 35
    header = f"| {'Слово (англ)':<{col_eng}} | {'Перевод-описание (рус)':<{col_ru}} |"
    separator = "-" * len(header)

    print("\n" + "=" * 75)
    print(f"СТАТИСТИКА ДЛЯ МОДУЛЯ: {mod_name.upper()}")
    print(f"Всего элементов: {total} | Переведено: {translated_count} ({percent:.1f}%) | Осталось: {len(missing_words)}")
    print("=" * 75)

    if translated_words:
        print("\n[ ГОТОВЫЕ ПЕРЕВОДЫ-ПРЕДЛОЖЕНИЯ ]")
        print(separator)
        print(header)
        print(separator)
        for eng, ru in translated_words:
            print(f"| {eng:<{col_eng}} | {ru:<{col_ru}} |")
        print(separator)

if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        try: data = json.load(file)
        except json.JSONDecodeError: data = {}
else:
    data = {}

print("Выберите режим работы:")
print("1 — Одиночный ввод слова (смысловой автоперевод)")
print("2 — Полный автоперевод целого Python-модуля (пакетный режим фраз)")
print("3 — Посмотреть статистику по конкретному модулю")
mode = input("Введите номер режима (1, 2 или 3): ").strip()

translator = GoogleTranslator(source='en', target='ru')
need_to_save = False

if mode == "1":
    module = input('Название модуля: ').strip()
    if module not in data:
        data[module] = {"ru-name": module, "sources": {}}
        need_to_save = True

    func = input('Какому слову/команде дать перевод (англ): ').strip()
    sources = data[module].setdefault("sources", {})

    if func in sources:
        current_translation = sources[func].get("ru-name")
        print(f"Слово '{func}' уже есть. Текущее описание: '{current_translation}'")
        answer = input("Хотите перезаписать? (да/нет): ").strip().lower()
        if answer not in ['да', 'y', 'yes']:
            print("Изменения отменены.")
            sys.exit(0)

    print(f"Преобразую выражение... Ищу смысловой перевод для: '{prepare_technical_text(func)}'")
    try:
        auto_translation = translate_as_action(func, translator)
        if has_english_letters(auto_translation):
            print(f"Предупреждение: перевод содержит латиницу: '{auto_translation}'")
            final_translation = input(f"Введите ручной перевод-описание для '{func}': ").strip()
        else:
            print(f"Предложенное описание действия: '{auto_translation}'")
            accept = input("Использовать его? (Enter/да, 'нет' - ввести вручную, или ваш вариант): ").strip().lower()
            if accept in ['да', 'y', 'yes', '']:
                final_translation = auto_translation
            elif accept in ['нет', 'n', 'no']:
                final_translation = input(f"Введите свой вариант описания: ").strip()
            else:
                final_translation = accept
    except Exception as e:
        print(f"Ошибка подключения к переводчику ({e}).")
        final_translation = input(f"Введите перевод вручную: ").strip()

    if final_translation:
        if has_english_letters(final_translation):
            print("Ошибка: Текст содержит английские буквы. Запись отменена.")
        else:
            sources[func] = {"ru-name": final_translation}
            need_to_save = True
            print(f"Успешно сохранено описание: {func} -> {final_translation}")

elif mode == "2":
    module_name = input('Какой Python-модуль автоматически перевести в развернутые фразы?: ').strip()
    try:
        imported_module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print(f"Ошибка: Модуль '{module_name}' не найден в системе.")
        sys.exit(1)

    if module_name not in data:
        data[module_name] = {"ru-name": module_name, "sources": {}}

    sources = data[module_name].setdefault("sources", {})
    
    module_elements = []
    for name, _ in inspect.getmembers(imported_module):
        if not name.startswith('_'):
            module_elements.append(name)
    
    print(f"\nНайдено {len(module_elements)} элементов. Начинаю перевод в формат описания действий...")



    for idx, eng_word in enumerate(module_elements, 1):
        # Проверяем, существует ли уже перевод для этого слова
        if eng_word in sources:
            current_ru = sources[eng_word].get("ru-name", "")
            
            # Если перевод есть и он корректный (без латиницы) -> пропускаем
            if not has_english_letters(current_ru) and current_ru:
                print(f"[{idx}/{len(module_elements)}] Слово '{eng_word}' уже есть в базе ('{current_ru}'). Пропуск.")
                continue
            
        # Пауза 1 сек между запросами, чтобы защитить API от блокировки
        time.sleep(1)
        
        prepared_phrase = prepare_technical_text(eng_word)
        print(f"[{idx}/{len(module_elements)}] Перевод '{eng_word}' (как '{prepared_phrase}')...")
        try:
            translated = translate_as_action(eng_word, translator)
            if has_english_letters(translated):
                print(f" -> Пропущено. В результате осталась латиница: '{translated}'")
            elif has_censoured(translated):
                print(f" -> Пропущено. В результате есть слово находящиеся в бан списке: '{translated}'")
            else:
                sources[eng_word] = {"ru-name": translated}
                need_to_save = True
                print(f" -> Успешно: '{translated}'")
        except Exception as e:
            print(f"Прерывание из-за ошибки API: {e}")
            break


elif mode == "3":
    module_name = input('Введите название модуля для вывода статистики: ').strip()
    print_module_statistics(data, module_name)

else:
    print("Неверный режим работы.")

if need_to_save:
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print("\n[ УСПЕХ ] Изменения сохранены в базу modules.json!")
