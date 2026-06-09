"""
build_gui.py — GUI сборщик для RuPy
Запуск: python main.py -m build_gui
"""

import os
import sys
import subprocess
import threading
import pathlib

# ─────────────────────────────────────────────
# Определение платформы
# ─────────────────────────────────────────────

def is_termux() -> bool:
    return (
        "com.termux" in os.environ.get("PREFIX", "")
        or "com.termux" in os.environ.get("HOME", "")
        or os.path.exists("/data/data/com.termux")
    )

def is_android() -> bool:
    return is_termux() or "ANDROID_ROOT" in os.environ

PLATFORM = "termux" if is_termux() or is_android() else "desktop"

# ─────────────────────────────────────────────
# Общая логика сборки
# ─────────────────────────────────────────────

def get_main_py() -> str:
    """
    Находит main.py в корне проекта
    Структура:
        ru-python/
        ├── main.py          <-- ищем здесь
        └── modules/
            └── build_gui.py <-- этот файл
    """
    # Путь к текущему файлу (modules/build_gui.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Поднимаемся на уровень выше (в корень проекта)
    project_root = os.path.dirname(current_dir)
    
    # main.py должен быть в корне
    main_py = os.path.join(project_root, "main.py")
    
    # Для отладки - выводим путь
    print(f"[DEBUG] Ищем main.py по пути: {main_py}")
    
    if os.path.exists(main_py):
        return main_py
    else:
        # Если не нашли, пробуем другие варианты
        alt_paths = [
            os.path.join(os.getcwd(), "main.py"),           # Текущая папка
            os.path.join(current_dir, "main.py"),           # В папке modules
            os.path.join(project_root, "..", "main.py"),    # Ещё выше
        ]
        
        for alt in alt_paths:
            print(f"[DEBUG] Пробуем: {alt}")
            if os.path.exists(alt):
                return alt
        
        # Если совсем не нашли - ошибка
        raise FileNotFoundError(
            "Не найден main.py! \n"
            f"Искали в: {main_py}\n"
            f"Текущая папка: {os.getcwd()}\n"
            f"Папка скрипта: {current_dir}"
        )

def run_build(rupy_file: str, name: str, icon: str,
              onefile: bool, noconsole: bool,
              log_callback):
    
    try:
        main_py = get_main_py()
    except FileNotFoundError as e:
        log_callback(f"❌ {str(e)}")
        return
    
    log_callback(f"📍 Использую main.py: {main_py}")
    log_callback("▶ Трансляция .rupy → .py ...")
    
    result = subprocess.run(
        [sys.executable, main_py, rupy_file, "-t"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.stdout:
        log_callback(result.stdout)
    if result.returncode != 0:
        if result.stderr:
            log_callback(result.stderr)
        log_callback("✗ Трансляция завершилась с ошибкой")
        return

    py_file = str(pathlib.Path(rupy_file).with_suffix(".py"))
    log_callback(f"✓ Транслировано -> {py_file}")

    log_callback("▶ Запуск PyInstaller ...")
    cmd = [sys.executable, "-m", "PyInstaller"]

    if onefile:
        cmd.append("--onefile")
    if noconsole:
        cmd.append("--noconsole")
    if name.strip():
        cmd += ["--name", name.strip()]
    if icon.strip() and os.path.exists(icon.strip()):
        cmd += ["--icon", icon.strip()]

    cmd.append(py_file)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout:
            log_callback(line.rstrip())
        proc.wait()

        if proc.returncode == 0:
            log_callback("✓ Сборка завершена успешно!")
        else:
            log_callback("✗ PyInstaller завершился с ошибкой")
    except FileNotFoundError:
        log_callback("✗ PyInstaller не найден. Установите: pip install pyinstaller")


# ══════════════════════════════════════════════════════════════
#  ДЕСКТОП: tkinter
# ══════════════════════════════════════════════════════════════

def run_tkinter():
    import tkinter as tk
    from tkinter import filedialog, scrolledtext, ttk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("RuPy — Сборщик проектов")
    root.geometry("750x650")
    root.configure(bg="#1e1e2e")
    root.resizable(True, True)

    BG = "#1e1e2e"
    PANEL = "#2a2a3e"
    ACCENT = "#313244"
    SUCCESS = "#a6e3a1"
    ERROR = "#f38ba8"
    WARNING = "#f9e2af"
    FG = "#cdd6f4"
    BTN_BG = "#89b4fa"
    ENTRY_BG = "#313244"

    FONT_TITLE = ("Segoe UI", 14, "bold")
    FONT_LABEL = ("Segoe UI", 10)
    FONT_BTN = ("Segoe UI", 10, "bold")
    FONT_LOG = ("Consolas", 9)

    main_frame = tk.Frame(root, bg=BG)
    main_frame.pack(fill="both", expand=True, padx=20, pady=15)

    title = tk.Label(main_frame, text="🚀 RuPy Builder Pro", font=FONT_TITLE,
                    bg=BG, fg="#89b4fa")
    title.pack(anchor="w", pady=(0, 15))

    settings_frame = tk.Frame(main_frame, bg=BG)
    settings_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

    fields = {}
    
    def make_field(parent, label_text, browse=False):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="x", pady=5)
        
        tk.Label(frame, text=label_text, bg=BG, fg=FG, font=FONT_LABEL,
                width=15, anchor="w").pack(side="left", padx=(0, 10))
        
        var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=var, bg=ENTRY_BG, fg=FG,
                        insertbackground=FG, relief="flat", font=FONT_LABEL)
        entry.pack(side="left", fill="x", expand=True)
        
        if browse:
            btn = tk.Button(frame, text="📁", command=browse, bg=ACCENT, fg=FG,
                           relief="flat", cursor="hand2", width=3)
            btn.pack(side="left", padx=(5, 0))
        
        return var
    
    def browse_rupy():
        filename = filedialog.askopenfilename(
            title="Выберите .rupy файл",
            filetypes=[("RuPy файлы", "*.rupy"), ("Все файлы", "*.*")]
        )
        if filename:
            fields['rupy_var'].set(filename)
    
    def browse_icon():
        filename = filedialog.askopenfilename(
            title="Выберите иконку",
            filetypes=[("Иконки", "*.ico *.png"), ("Все файлы", "*.*")]
        )
        if filename:
            fields['icon_var'].set(filename)
    
    fields['rupy_var'] = make_field(settings_frame, "📄 .rupy файл:", browse_rupy)
    fields['name_var'] = make_field(settings_frame, "🏷️ Имя файла:")
    fields['icon_var'] = make_field(settings_frame, "🎨 Иконка:", browse_icon)
    
    flags_frame = tk.LabelFrame(settings_frame, text="⚙️ Опции сборки", bg=BG, fg=FG,
                                font=FONT_LABEL, relief="flat")
    flags_frame.pack(fill="x", pady=(15, 10))
    
    fields['onefile_var'] = tk.BooleanVar(value=True)
    fields['noconsole_var'] = tk.BooleanVar(value=False)
    
    def create_colored_check(parent, text, var, row, col):
        frame = tk.Frame(parent, bg=BG)
        frame.grid(row=row, column=col, sticky="w", padx=10, pady=8)
        
        cb = tk.Checkbutton(frame, text=text, variable=var, bg=BG,
                           selectcolor=ACCENT, activebackground=BG,
                           font=FONT_LABEL, fg=FG, cursor="hand2")
        cb.pack(side="left")
        
        indicator = tk.Label(frame, text="●", bg=BG, font=("Segoe UI", 12))
        indicator.pack(side="left", padx=(8, 0))
        
        def update_color(*args):
            if var.get():
                indicator.config(fg=SUCCESS)
            else:
                indicator.config(fg=ERROR)
        
        var.trace('w', update_color)
        update_color()
        return cb
    
    create_colored_check(flags_frame, "📦 Собрать в один файл", fields['onefile_var'], 0, 0)
    create_colored_check(flags_frame, "🚫 Скрыть консоль", fields['noconsole_var'], 0, 1)
    
    def styled_btn(parent, text, cmd):
        b = tk.Button(parent, text=text, command=cmd,
                     bg=BTN_BG, fg=BG, activebackground="#a6e3a1",
                     relief="flat", font=FONT_BTN, padx=15, pady=6, cursor="hand2")
        b.bind("<Enter>", lambda e: b.config(bg="#a6e3a1"))
        b.bind("<Leave>", lambda e: b.config(bg=BTN_BG))
        return b
    
    build_btn = styled_btn(settings_frame, "🔨 СОБРАТЬ ПРОЕКТ 🔨", None)
    build_btn.pack(fill="x", pady=(10, 5))
    
    progress = ttk.Progressbar(settings_frame, mode='indeterminate', length=300)
    progress.pack(fill="x", pady=5)
    progress.pack_forget()
    
    log_frame = tk.Frame(main_frame, bg=PANEL)
    log_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
    
    tk.Label(log_frame, text="📋 Лог сборки", bg=PANEL, fg=FG,
            font=FONT_TITLE).pack(anchor="w", pady=(0, 10))
    
    log_box = scrolledtext.ScrolledText(log_frame, height=25, bg="#0f0f17", fg="#a6e3a1",
                                        font=FONT_LOG, state="disabled", relief="flat",
                                        insertbackground=FG, wrap="word")
    log_box.pack(fill="both", expand=True)
    
    log_box.tag_config("ok", foreground=SUCCESS)
    log_box.tag_config("error", foreground=ERROR)
    log_box.tag_config("warn", foreground=WARNING)
    log_box.tag_config("info", foreground="#89b4fa")
    
    def write_log(text, level="info"):
        def _do():
            log_box.config(state="normal")
            log_box.insert("end", text + "\n", level)
            log_box.see("end")
            log_box.config(state="disabled")
        root.after(0, _do)
    
    def on_build():
        rupy = fields['rupy_var'].get().strip()
        if not rupy or not os.path.exists(rupy):
            messagebox.showerror("Ошибка", "Файл .rupy не выбран!")
            return
        
        build_btn.config(state="disabled", text="⏳ СБОРКА... ⏳")
        progress.pack(fill="x", pady=5)
        progress.start(10)
        write_log("─" * 50, "info")
        
        def thread_target():
            run_build(rupy, fields['name_var'].get(), fields['icon_var'].get(),
                     fields['onefile_var'].get(), fields['noconsole_var'].get(),
                     lambda msg: write_log(msg, "info"))
            root.after(0, lambda: build_btn.config(state="normal", text="🔨 СОБРАТЬ ПРОЕКТ 🔨"))
            root.after(0, lambda: progress.stop())
            root.after(0, lambda: progress.pack_forget())
        
        threading.Thread(target=thread_target, daemon=True).start()
    
    build_btn.config(command=on_build)
    write_log("✨ RuPy Builder Pro готов!", "ok")
    
    root.mainloop()


# ══════════════════════════════════════════════════════════════
#  TERMUX: TUI (упрощённая версия)
# ══════════════════════════════════════════════════════════════

def run_termux_simple():
    """Интерфейс для Termux"""
    
    def clear_screen():
        os.system('clear')
    
    def print_header():
        print("=" * 60)
        print(" 🚀 RuPy Builder Pro - Termux версия")
        print("=" * 60)
        print()
    
    def print_menu():
        print("\n📋 МЕНЮ:")
        print("  1 - Выбрать .rupy файл")
        print("  2 - Установить имя файла")
        print("  3 - Выбрать иконку")
        print("  4 - Включить/выключить --onefile")
        print("  5 - Включить/выключить --noconsole")
        print("  6 - СТАРТ СБОРКИ")
        print("  7 - Показать лог")
        print("  0 - Выход")
        print()
    
    # Настройки
    config = {
        'rupy_file': '',
        'name': '',
        'icon': '',
        'onefile': True,
        'noconsole': False
    }
    
    # Лог
    log_lines = []
    
    def add_log(msg):
        log_lines.append(msg)
        while len(log_lines) > 100:
            log_lines.pop(0)
    
    def resolve_path(path):
        if not path:
            return path
        if path.startswith("~"):
            return os.path.expanduser(path)
        return os.path.abspath(path)
    
    def show_status():
        clear_screen()
        print_header()
        
        print("📁 ТЕКУЩИЕ НАСТРОЙКИ:")
        if config['rupy_file']:
            real_path = resolve_path(config['rupy_file'])
            exists = "✅" if os.path.exists(real_path) else "❌"
            print(f"  📄 .rupy файл: {config['rupy_file']} {exists}")
        else:
            print(f"  📄 .rupy файл: ❌ НЕ ВЫБРАН")
        
        print(f"  🏷️ Имя файла: {config['name'] or '(авто)'}")
        print(f"  🎨 Иконка: {config['icon'] or '(нет)'}")
        print()
        print("⚙️ ОПЦИИ:")
        print(f"  📦 Собрать в один файл: {'✅ ДА' if config['onefile'] else '❌ НЕТ'}")
        print(f"  🚫 Скрыть консоль: {'✅ ДА' if config['noconsole'] else '❌ НЕТ'}")
        print()
        
        if log_lines:
            print("📋 ПОСЛЕДНИЕ СОБЫТИЯ:")
            print("-" * 60)
            for line in log_lines[-5:]:
                print(f"  {line}")
            print("-" * 60)
        
      #  print_menu()
    
    def show_full_log():
        clear_screen()
        print_header()
        print("📋 ПОЛНЫЙ ЛОГ:")
        print("=" * 60)
        if log_lines:
            for line in log_lines:
                print(line)
        else:
            print("(пусто)")
        print("=" * 60)
        input("\nНажмите Enter для продолжения...")
    
    def run_build_simple():
        if not config['rupy_file']:
            add_log("❌ Ошибка: .rupy файл не выбран!")
            input("Нажмите Enter...")
            return
        
        rupy_path = resolve_path(config['rupy_file'])
        if not os.path.exists(rupy_path):
            add_log(f"❌ Ошибка: Файл не найден: {rupy_path}")
            input("Нажмите Enter...")
            return
        
        icon_path = resolve_path(config['icon']) if config['icon'] else ''
        
        add_log(f"🚀 Старт сборки...")
        add_log(f"📁 Файл: {rupy_path}")
        
        def log_callback(msg):
            add_log(msg)
            print(f"  {msg}")
        
        def build_thread():
            run_build(
                rupy_path,
                config['name'],
                icon_path if os.path.exists(icon_path) else '',
                config['onefile'],
                config['noconsole'],
                log_callback
            )
        
        thread = threading.Thread(target=build_thread)
        thread.start()
        thread.join()
        
        input("\nНажмите Enter для продолжения...")
    
    def toggle_onefile():
        config['onefile'] = not config['onefile']
        add_log(f"📦 Собрать в один файл: {'ВКЛ' if config['onefile'] else 'ВЫКЛ'}")
    
    def toggle_noconsole():
        config['noconsole'] = not config['noconsole']
        add_log(f"🚫 Скрыть консоль: {'ВКЛ' if config['noconsole'] else 'ВЫКЛ'}")
    
    def select_rupy_file():
        clear_screen()
        print_header()
        
        print("✏️ ВВЕДИТЕ ПУТЬ К .RUPY ФАЙЛУ")
        print("-" * 60)
        print("Примеры:")
        print(f"  • test.rupy (файл в текущей папке)")
        print(f"  • ../test.rupy (файл на уровень выше)")
        print(f"  • ~/storage/downloads/test.rupy")
        print("-" * 60)
        
        # Показываем .rupy файлы в текущей папке
        current = os.getcwd()
        try:
            files = [f for f in os.listdir(current) if f.endswith('.rupy')]
            if files:
                print("\n📁 Найдено в текущей папке:")
                for f in files:
                    print(f"   • {f}")
        except:
            pass
        
        print()
        path = input("➜ Путь: ").strip()
        
        if not path:
            add_log("❌ Выбор отменён")
        else:
            full_path = resolve_path(path)
            if os.path.exists(full_path):
                if full_path.endswith('.rupy'):
                    config['rupy_file'] = path
                    add_log(f"✅ Выбран файл: {full_path}")
                else:
                    add_log(f"❌ Файл должен быть .rupy: {path}")
            else:
                add_log(f"❌ Файл не найден: {full_path}")
        
        input("\nНажмите Enter...")
    
    def select_icon():
        clear_screen()
        print_header()
        
        print("✏️ ВВЕДИТЕ ПУТЬ К ИКОНКЕ (.ico или .png)")
        print("-" * 60)
        print("(оставьте пустым чтобы пропустить)")
        print("-" * 60)
        
        path = input("\n➜ Путь: ").strip()
        
        if not path:
            config['icon'] = ''
            add_log("🎨 Иконка пропущена")
        else:
            full_path = resolve_path(path)
            if os.path.exists(full_path):
                if full_path.endswith(('.ico', '.png')):
                    config['icon'] = path
                    add_log(f"🎨 Выбрана иконка: {full_path}")
                else:
                    add_log(f"❌ Иконка должна быть .ico или .png: {path}")
            else:
                add_log(f"❌ Иконка не найдена: {full_path}")
        
        input("\nНажмите Enter...")
    
    def set_name():
        clear_screen()
        print_header()
        
        print("✏️ ВВЕДИТЕ ИМЯ ВЫХОДНОГО ФАЙЛА")
        print("-" * 60)
        print("(оставьте пустым чтобы использовать имя .rupy файла)")
        print("-" * 60)
        
        name = input("\n➜ Имя: ").strip()
        config['name'] = name
        if name:
            add_log(f"🏷️ Имя файла: {name}")
        else:
            add_log(f"🏷️ Будет использовано имя .rupy файла")
        
        input("\nНажмите Enter...")
    
    # Главный цикл
    while True:
        show_status()
        
        from simple_term_menu import TerminalMenu
        options = ["0. Выход", "1. Выбрать .rupy файл", "2. Выбрать выходное имя", "3.Выбрать иконку","4. Переключить один файл/папка", "5. Переключить с консолью/без консоли", "6. Запуск сборки","7. Показать лог"]
        
        menu = TerminalMenu(
    options,
    title="Меню с курсором >",
    menu_cursor="> ",
    menu_cursor_style=("fg_red", "bold")
)
        choice = str(menu.show())
       # print(choice)
        if choice == '0':
            print("\n👋 До свидания!")
            break
        
        elif choice == '1':
            select_rupy_file()
        
        elif choice == '2':
            set_name()
        
        elif choice == '3':
            select_icon()
        
        elif choice == '4':
            toggle_onefile()
            input("Нажмите Enter...")
        
        elif choice == '5':
            toggle_noconsole()
            input("Нажмите Enter...")
        
        elif choice == '6':
            run_build_simple()
        
        elif choice == '7':
            show_full_log()
        
        else:
            add_log("❌ Неверный выбор!")
            input("Нажмите Enter...")


# ══════════════════════════════════════════════════════════════
# Точка входа
# ══════════════════════════════════════════════════════════════

def run():
    if PLATFORM == "termux":
        print(f"\n[RuPy] Обнаружен Termux/Android")
        print("[RuPy] Запуск интерфейса...\n")
        run_termux_simple()
    else:
        print(f"[RuPy] Запуск десктоп версии с tkinter")
        run_tkinter()


def app():
    """Главная функция для запуска GUI"""
    run()


if __name__ == "__main__":
    app()