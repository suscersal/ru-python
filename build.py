import subprocess
import os
import sys
import platform
import requests
import json
import re

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# ИСПРАВЛЕНО: Прямая ссылка на сырой JSON-файл (Raw контент)
GITHUB_RAW_URL = "https://github.com/suscersal/ru-python/blob/main/rus-python/modules.json"

def install_if_missing(package):
    try:
        subprocess.run([sys.executable, "-m", "pip", "show", package], 
                       capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print(f"{YELLOW}--- Модуль {package} не найден. Устанавливаю... ---{RESET}")
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

# 1. Проверка зависимостей
install_if_missing("pyinstaller")

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

def clean_and_parse_json(raw_text, source_name=""):
    """Очищает текст от возможных маркеров конфликтов Git и парсит JSON."""
    cleaned = re.sub(r'<<<<<<< HEAD.*?=======', '', raw_text, flags=re.DOTALL)
    cleaned = re.sub(r'>>>>>>> [a-f0-9]+', '', cleaned)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print(f"{RED}--- Ошибка структуры JSON в {source_name}: {e} ---{RESET}")
        return None

# Функция умного слияния локального файла и данных с GitHub
def sync_modules_with_github(target_path):
    print(f"{YELLOW}--- Синхронизация модулей с GitHub... ---{RESET}")
    
    local_data = {}
    local_broken = False
    
    # Чтение локального файла
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                local_raw = f.read()
            local_data = json.loads(local_raw)
        except Exception as e:
            print(f"{RED}--- Локальный {target_path} поврежден ({e}). Восстановление... ---{RESET}")
            parsed = clean_and_parse_json(local_raw, "локальном файле")
            if parsed is not None:
                local_data = parsed
                print(f"{GREEN}--- Локальный файл успешно реанимирован ---{RESET}")
            else:
                local_broken = True

    # Скачивание с GitHub
    github_data = None
    try:
        response = requests.get(GITHUB_RAW_URL, timeout=10)
        if response.status_code == 200:
            github_data = clean_and_parse_json(response.text, "GitHub")
        else:
            print(f"{RED}--- Не удалось скачать. Статус GitHub: {response.status_code} ---{RESET}")
    except Exception as e:
        print(f"{RED}--- Ошибка сети при обращении к GitHub: {e} ---{RESET}")

    # Логика обработки результатов
    if github_data is None and (local_broken or not local_data):
        print(f"{RED}--- Нет доступных источников данных. Создание базового шаблона ---{RESET}")
        local_data = {"os": {"ru-name": "ос", "sources": {}}}
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(local_data, f, ensure_ascii=False, indent=2)
        return

    if github_data:
        if deep_merge(local_data, github_data) or local_broken:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(local_data, f, ensure_ascii=False, indent=2)
            print(f"{GREEN}--- Данные успешно объединены и сохранены в {target_path} ---{RESET}")
        else:
            print(f"{GREEN}--- Локальный файл содержит актуальную версию переводов ---{RESET}")
    else:
        if not local_broken:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(local_data, f, ensure_ascii=False, indent=2)
            print(f"{YELLOW}--- Работа в режиме офлайн на локальной копии ---{RESET}")

# 2. Поиск PyInstaller
scripts_path = os.path.join(os.path.dirname(sys.executable), "Scripts")
pyinstaller = os.path.join(scripts_path, "pyinstaller.exe")

if not os.path.exists(pyinstaller):
    pyinstaller = "pyinstaller" 

# 3. Настройки сборки
script_to_build = "main.py"
exe_name = "rupython"
icon_path = "icon.ico"
module_file = "modules.json"

# Запуск синхронизации перед компиляцией
sync_modules_with_github(module_file)

# Base аргументы PyInstaller
args = [
    pyinstaller,
    "--onefile",
    "--name", exe_name,
    "--clean"
]

if os.path.exists(icon_path):
    args.extend(["--icon", icon_path])
else:
    print(f"{YELLOW}--- Предупреждение: {icon_path} не найден, стандартная иконка ---{RESET}")

separator = ";" if platform.system() == "Windows" else ":"

if os.path.exists(module_file):
    args.extend(["--add-data", f"{module_file}{separator}."])
else:
    print(f"{YELLOW}--- Предупреждение: {module_file} не найден, сборка без перевода ---{RESET}")

args.append(script_to_build)

def test_run():
    exe_ext = ".exe" if platform.system() == "Windows" else ""
    exe_path = os.path.join("dist", f"{exe_name}{exe_ext}")
    test_file_path = os.path.join(".", "test.rupy")
    if os.path.exists(exe_path):
        print(f"{GREEN}--- Запуск собранного файла для проверки... ---{RESET}")
        subprocess.run([exe_path, test_file_path])
    else:
        print(f"{RED}--- Ошибка: Исполняемый файл не найден в папке dist ---{RESET}")
        
# 4. Сборка
print(f"{GREEN}--- Начинаю сборку {exe_name} ---{RESET}")
try:
    result = subprocess.run(args)
    if result.returncode == 0:
        print(f"{GREEN}\n Готово! Файл {exe_name} создан в папке 'dist'.{RESET}")
        test_run()
    else:
        print(f"\n {RED}Ошибка сборки. Код: {result.returncode}{RESET}")
except Exception as e:
    print(f"{RED}Ошибка при запуске PyInstaller: {e}{RESET}")
