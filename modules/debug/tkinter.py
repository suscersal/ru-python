from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from core import RuPyDebugger


class App(tk.Tk):
    def __init__(self, path1: str, path2: str):
        super().__init__()
        self.title("RuPy Debugger")
        self.geometry("1200x800")

        self.dbg = RuPyDebugger(path1, path2)

        self._build_ui()
        self.reload()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Button(top, text="Открыть .rupy", command=self.open_rupy).pack(side="left")
        ttk.Button(top, text="Открыть .py", command=self.open_py).pack(side="left", padx=5)
        ttk.Button(top, text="Запуск", command=self.run_debug).pack(side="left", padx=5)
        ttk.Button(top, text="Поставить брейкпоинт", command=self.add_breakpoint).pack(side="left", padx=5)
        ttk.Button(top, text="Снять брейкпоинт", command=self.remove_breakpoint).pack(side="left", padx=5)
        ttk.Button(top, text="Заново", command=self.reload).pack(side="left", padx=5)
        ttk.Button(top, text="Стоп", command=self.stop).pack(side="left", padx=5)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=1)

        ttk.Label(left, text="rupy").pack(anchor="w")
        self.rupy_text = tk.Text(left, wrap="none")
        self.rupy_text.pack(fill="both", expand=True)

        ttk.Label(right, text="python").pack(anchor="w")
        self.py_text = tk.Text(right, wrap="none")
        self.py_text.pack(fill="both", expand=True)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=8, pady=8)

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(bottom, textvariable=self.status_var).pack(anchor="w")

        ttk.Label(bottom, text="Переменные:").pack(anchor="w")
        self.vars_text = tk.Text(bottom, height=10)
        self.vars_text.pack(fill="x", expand=False)

    def _ask_line(self) -> int | None:
        win = tk.Toplevel(self)
        win.title("Номер строки")
        win.geometry("240x100")
        result = {"value": None}

        ttk.Label(win, text="Введите номер строки:").pack(pady=5)
        entry = ttk.Entry(win)
        entry.pack(pady=5)
        entry.focus_set()

        def ok():
            try:
                result["value"] = int(entry.get().strip())
            except ValueError:
                result["value"] = None
            win.destroy()

        ttk.Button(win, text="OK", command=ok).pack(pady=5)
        self.wait_window(win)
        return result["value"]

    def open_rupy(self):
        path = filedialog.askopenfilename(
            title="Выбери файл .rupy",
            filetypes=(("RuPy files", "*.rupy"), ("All files", "*.*")),
        )
        if not path:
            return
        self.dbg.state.rupy_path = path
        self.reload()

    def open_py(self):
        path = filedialog.askopenfilename(
            title="Выбери файл .py",
            filetypes=(("Python files", "*.py"), ("All files", "*.*")),
        )
        if not path:
            return
        self.dbg.state.py_path = path
        self.reload()

    def reload(self):
        try:
            rupy = self.dbg.load_rupy() if Path(self.dbg.state.rupy_path).exists() else ""
        except Exception:
            rupy = ""
        try:
            py = self.dbg.load_py() if Path(self.dbg.state.py_path).exists() else ""
        except Exception:
            py = ""

        self.rupy_text.delete("1.0", "end")
        self.rupy_text.insert("1.0", rupy)

        self.py_text.delete("1.0", "end")
        self.py_text.insert("1.0", py)

    def add_breakpoint(self):
        line = self._ask_line()
        if line:
            self.dbg.set_breakpoint(line)
            self.status_var.set(f"Брейкпоинт поставлен на строку {line}")

    def remove_breakpoint(self):
        line = self._ask_line()
        if line:
            self.dbg.remove_breakpoint(line)
            self.status_var.set(f"Брейкпоинт снят со строки {line}")

    def run_debug(self):
        def on_event(st):
            self.status_var.set(f"{st.status}: {st.message}")
            self.vars_text.delete("1.0", "end")
            for k, v in st.current_locals.items():
                self.vars_text.insert("end", f"{k} = {v!r}")
            self.update_idletasks()

        self.dbg.run_debug(on_event=on_event)

    def stop(self):
        self.status_var.set("Остановлено пользователем")