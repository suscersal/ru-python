import os
import sys
import subprocess
import importlib
import inspect
import json

try:
    from deep_translator import GoogleTranslator
except ModuleNotFoundError:
    print("Библиотека 'deep-translator' не найдена. Начинаю автоматическую установку...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])
        print("Установка успешно завершена!\n")
        from deep_translator import GoogleTranslator
    except Exception as e:
        print(f"Ошибка при автоматической установке через pip: {e}")
        print("Пожалуйста, установите библиотеку вручную командой: pip install deep-translator")
        sys.exit(1)

file_path = 'modules.json'

def print_table(data_dict):
    col_mod, col_eng, col_ru = 15, 20, 20
    header = f"| {'Модуль':<{col_mod}} | {'Слово (англ)':<{col_eng}} | {'Перевод (рус)':<{col_ru}} |"
    separator = "-" * len(header)
    
    print("\n" + separator)
    print(header)
    print(separator)
    
    for mod_name, mod_content in data_dict.items():
        sources = mod_content.get("sources", {})
        if not sources:
            print(f"| {mod_name:<{col_mod}} | {'(пусто)':<{col_eng}} | {'(пусто)':<{col_ru}} |")
        else:
            for eng_word, ru_content in sources.items():
                ru_word = ru_content.get("ru-name", "")
                print(f"| {mod_name:<{col_mod}} | {eng_word:<{col_eng}} | {ru_word:<{col_ru}} |")
    print(separator + "\n")

if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            data = {}
else:
    data = {}

if data:
    print("Текущая база переводов:")
    print_table(data)
else:
    print("База данных пока пуста.")

print("Выберите режим работы:")
print("1 — Одиночный ввод слова (вручную/с подтверждением ИИ)")
print("2 — Полный автоперевод целого Python-модуля (пакетный режим)")
mode = input("Введите номер режима (1 или 2): ").strip()

translator = GoogleTranslator(source='en', target='ru')
need_to_save = False

if mode == "1":
    module = input('Название модуля: ').strip()
    if module not in data:
        print(f"Модуля '{module}' ещё нет, создаю...")
        data[module] = {"ru-name": module, "sources": {}}
        need_to_save = True

    func = input('Какому слову вы хотите дать перевод (англ): ').strip()
    sources = data[module].setdefault("sources", {})

    if func in sources:
        current_translation = sources[func].get("ru-name")
        print(f"Слово '{func}' уже есть в модуле '{module}'. Текущий перевод: '{current_translation}'")
        
        answer = input("Хотите перезаписать перевод? (да/нет): ").strip().lower()
        if answer in ['да', 'y', 'yes']:
            new_translation = input(f"Введите НОВЫЙ перевод для слова '{func}': ").strip()
            data[module]["sources"][func]["ru-name"] = new_translation
            need_to_save = True
            print(f"Перевод для слова '{func}' успешно обновлен.")
        else:
            print("Изменения отменены.")
    else:
        print("Ищу автоматический перевод...")
        try:
            auto_translation = translator.translate(func).lower()
            print(f"Найден автоперевод: '{auto_translation}'")
            accept = input("Использовать его? (Enter/да, 'нет' - вручную, или ваш вариант): ").strip().lower()
            
            if accept in ['да', 'y', 'yes', '']:
                final_translation = auto_translation
            elif accept in ['нет', 'n', 'no']:
                final_translation = input(f"Введите ручной перевод для '{func}': ").strip()
            else:
                final_translation = accept
        except Exception as e:
            print(f"Не удалось подключиться к переводчику ({e}).")
            final_translation = input(f"Введите перевод вручную для '{func}': ").strip()

        if final_translation:
            data[module]["sources"][func] = {"ru-name": final_translation}
            need_to_save = True
            print(f"Слово '{func}' успешно добавлено.")

elif mode == "2":
    module_name = input('Какой Python-модуль автоматически перевести? (например: math, os): ').strip()
    try:
        imported_module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print(f"Ошибка: Скрипт не смог найти Python-модуль '{module_name}'.")
        sys.exit(1)

    if module_name not in data:
        data[module_name] = {"ru-name": module_name, "sources": {}}

    sources = data[module_name].setdefault("sources", {})
    module_elements = [name for name, _ in inspect.getmembers(imported_module) if not name.startswith('_')]
    
    print(f"\nНайдено {len(module_elements)} элементов в модуле '{module_name}'. Начинаю пакетный перевод...")

    for idx, eng_word in enumerate(module_elements, 1):
        if eng_word in sources:
            print(f"[{idx}/{len(module_elements)}] '{eng_word}' уже есть в базе. Пропускаю.")
            continue
            
        print(f"[{idx}/{len(module_elements)}] Полный автоперевод слова: '{eng_word}'...")
        try:
            translated = translator.translate(eng_word).lower()
            sources[eng_word] = {"ru-name": translated}
            need_to_save = True
        except Exception as e:
            print(f"Ошибка при переводе '{eng_word}': {e}. Прерываю поток.")
            break
else:
    print("Неверный режим работы. Завершение программы.")

if need_to_save:
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print("\nИзменения успешно сохранены! Обновленная таблица:")
    print_table(data)
else:
    print("\nИзменений не обнаружено.")
