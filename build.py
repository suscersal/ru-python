import subprocess
import os
import sys
import platform

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def install_if_missing(package):
    try:
        subprocess.run([sys.executable, "-m", "pip", "show", package], 
                       capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print(f"{YELLOW}--- Модуль {package} не найден. Устанавливаю... ---{RESET}")
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

# 1. Проверка зависимостей
install_if_missing("pyinstaller")

# 2. Поиск PyInstaller
scripts_path = os.path.join(os.path.dirname(sys.executable), "Scripts")
pyinstaller = os.path.join(scripts_path, "pyinstaller.exe")

if not os.path.exists(pyinstaller):
    pyinstaller = "pyinstaller" 

# 3. Настройки
script_to_build = "main.py"
exe_name = "rupython"
icon_path = "icon.ico"
module_file = "modules.json"

# Base аргументы
args = [
    pyinstaller,
    "--onefile",
    "--name", exe_name,
    "--clean"
]

# Проверка и добавление иконки
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
    exe_path = os.path.join("dist", f"{exe_name}.exe")
    test_file_path = os.path.join(".", "test.rupy")
    if os.path.exists(exe_path):
        print(f"{GREEN}--- Запуск собранного файла для проверки... ---{RESET}")
        subprocess.run([exe_path, test_file_path])
    else:
        print(f"{RED}--- Ошибка: Исполняемый файл не найден в папке dist ---{RESET}")
        
# 4. Сборка
print(f"{GREEN}--- Начинаю сборку {exe_name}.exe ---{RESET}")
try:
    result = subprocess.run(args)
    if result.returncode == 0:
        print(f"{GREEN}\n Готово! Файл {exe_name}.exe создан в папке 'dist'.{RESET}")
        test_run()
    else:
        print(f"\n {RED}Ошибка сборки. Код: {result.returncode}{RESET}")
except Exception as e:
    print(f"{RED}Ошибка при запуске PyInstaller: {e}{RESET}")
