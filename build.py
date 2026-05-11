import subprocess
import os
import sys


RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# 1. Функция для автоматической установки модулей
def install_if_missing(package):
    try:
        # Проверяем, установлен ли пакет
        subprocess.run([sys.executable, "-m", "pip", "show", package], 
                       capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print(f"--- Модуль {package} не найден. Устанавливаю... ---")
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

# 2. Устанавливаем PyInstaller, если его нет
install_if_missing("pyinstaller")

# 3. Находим путь к pyinstaller.exe автоматически
# Обычно он лежит в папке Scripts рядом с python.exe
scripts_path = os.path.join(os.path.dirname(sys.executable), "Scripts")
pyinstaller = os.path.join(scripts_path, "pyinstaller.exe")

# Если вдруг не нашли в стандартном месте, пробуем вызвать просто команду
if not os.path.exists(pyinstaller):
    pyinstaller = "pyinstaller" 

# 4. Настройки сборки
script_to_build = "main.py"
exe_name = "rupython"
icon_path = "icon.ico" # Убедись, что файл существует, или закомментируй строку ниже

args = [
    pyinstaller,
    "--onefile",
    "--name", exe_name,
    "--clean"  # Очистить временные файлы перед сборкой
]

# Добавляем иконку только если файл существует
if os.path.exists(icon_path):
    args.extend(["--icon", icon_path])
else:
    print(f"{YELLOW}--- Предупреждение: {icon_path} не найден, сборка будет со стандартной иконкой ---")

args.append(script_to_build)

def test_run():
    exe_path = os.path.join("dist", f"{exe_name}.exe")
    test_file_path = os.path.join('.','test.rupy')
    if os.path.exists(exe_path):
        print(f"{GREEN}--- Запуск собранного файла для проверки... ---{RESET}")
        os.system(f"{exe_path} {test_file_path}")
    else:
        print(f"{RED}--- Ошибка: Исполняемый файл не найден в папке dist ---{RESET}")
        
# test_run()
# 5. Запуск сборки
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
