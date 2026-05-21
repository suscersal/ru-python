import subprocess
import os
import sys
import platform
import requests
import json

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Самый стабильный CDN-адрес для скачивания файлов из GitHub без блокировок DNS
GITHUB_JSON_URL = "https://raw.githubusercontent.com/suscersal/ru-python/refs/heads/main/rus-python/modules.json"

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
    """
    Рекурсивно объединяет dict2 (GitHub) в dict1 (Локальный).
    Возвращает True, если появились новые ключи или переводы.
    """
    is_updated = False
    for key, value in dict2.items():
        if key not in dict1:
            dict1[key] = value
            is_updated = True
        elif isinstance(dict1[key], dict) and isinstance(value, dict):
            if deep_merge(dict1[key], value):
                is_updated = True
    return is_updated

# Функция синхронизации модулей
def sync_modules_with_github(target_path):
    print(f"{YELLOW}--- Синхронизация модулей с GitHub... ---{RESET}")
    
    local_data = {}
    
    # 1. Читаем локальный файл, если он есть
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except Exception as e:
            print(f"{RED}--- Ошибка чтения локального файла: {e}. Пересоздаем... ---{RESET}")

    # 2. Загружаем свежие переводы из репозитория
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(GITHUB_JSON_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            github_data = response.json()
            
            # Скрещиваем локальный файл и данные с гитхаба
            if deep_merge(local_data, github_data) or not os.path.exists(target_path):
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(local_data, f, ensure_ascii=False, indent=2)
                print(f"{GREEN}--- Файл переводов успешно обновлен и синхронизирован ---{RESET}")
            else:
                print(f"{GREEN}--- Локальный файл уже содержит все актуальные переводы ---{RESET}")
        else:
            print(f"{RED}--- Не удалось получить данные. Статус сервера: {response.status_code} ---{RESET}")
            print(f"{YELLOW}--- Продолжаем сборку на локальной копии ---{RESET}")
            
    except Exception as e:
        print(f"{RED}--- Сеть недоступна ({e}). Продолжаем сборку на локальной копии ---{RESET}")

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

# Запускаем обновление перед упаковкой в EXE
sync_modules_with_github(module_file)

# Базовые аргументы компилятора
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
        
# 4. Запуск сборщика
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
