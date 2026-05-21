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

# ТОЧНАЯ ПРЯМАЯ ССЫЛКА НА ВАШ ФАЙЛ
GITHUB_RAW_URL = "https://raw.githubusercontent.com/suscersal/ru-python/refs/heads/main/rus-python/modules.json"

def install_if_missing(package):
    try:
        subprocess.run([sys.executable, "-m", "pip", "show", package], 
                       capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print(f"{YELLOW}--- Модуль {package} не найден. Устанавливаю... ---{RESET}")
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

# 1. Проверка зависимостей сборщика
install_if_missing("pyinstaller")
install_if_missing("requests")

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

def sync_modules_before_build(target_path):
    """Синхронизирует файл строго внутри папки rus-python перед сборкой"""
    print(f"{YELLOW}--- Синхронизация модулей с GitHub перед сборкой... ---{RESET}")
    
    # Создаем папку rus-python, если её вдруг нет
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    local_data = {}
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except Exception as e:
            print(f"{RED}--- Ошибка чтения существующего {target_path}: {e} ---{RESET}")

    try:
        # Браузерные заголовки для обхода блокировок/капч GitHub
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        response = requests.get(GITHUB_RAW_URL, headers=headers, timeout=7)
        
        if response.status_code == 200:
            github_data = response.json()
            
            # Выполняем слияние
            if deep_merge(local_data, github_data) or not os.path.exists(target_path):
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(local_data, f, ensure_ascii=False, indent=2)
                print(f"{GREEN}--- Файл {target_path} успешно обновлен данными с GitHub ---{RESET}")
            else:
                print(f"{GREEN}--- Локальный {target_path} уже содержит все актуальные переводы ---{RESET}")
        else:
            print(f"{RED}--- GitHub вернул ошибку: {response.status_code}. Сборка на локальных данных ---{RESET}")
            
    except Exception as e:
        print(f"{RED}--- Не удалось связаться с GitHub ({e}). Сборка на локальных данных ---{RESET}")

# 2. Поиск PyInstaller
scripts_path = os.path.join(os.path.dirname(sys.executable), "Scripts")
pyinstaller = os.path.join(scripts_path, "pyinstaller.exe")

if not os.path.exists(pyinstaller):
    pyinstaller = "pyinstaller" 

# 3. Настройки путей для PyInstaller
script_to_build = "main.py"
exe_name = "rupython"
icon_path = "icon.ico"

# Указываем путь СТРОГО в подпапку исходников, как ты просил
module_file_path = os.path.join("rus-python", "modules.json")

# Запускаем синхронизацию (обновит именно rus-python/modules.json)
sync_modules_before_build(module_file_path)

# Базовые аргументы PyInstaller
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

# Вшиваем файл из правильного места (rus-python/modules.json) внутрь EXE под именем modules.json
if os.path.exists(module_file_path):
    args.extend(["--add-data", f"{module_file_path}{separator}."])
else:
    print(f"{YELLOW}--- Предупреждение: {module_file_path} не найден, сборка без перевода ---{RESET}")

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
        
# 4. Запуск компиляции
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
