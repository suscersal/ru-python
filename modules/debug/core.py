from __future__ import annotations

import sys
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

DEBUG_DIR = Path(__file__).resolve().parent
if str(DEBUG_DIR) not in sys.path:
    sys.path.insert(0, str(DEBUG_DIR))


@dataclass
class DebugState:
    rupy_path: str
    py_path: str
    breakpoints: set[int] = field(default_factory=set)
    current_line: int = 0
    current_locals: dict = field(default_factory=dict)
    status: str = "idle"
    message: str = ""


def detect_system() -> str:
    if sys.platform == "android":
        return "termux"
    return "tkinter"


def _split_paths(path1: str, path2: str) -> tuple[str, str]:
    p1 = Path(path1)
    p2 = Path(path2)

    if p1.suffix == ".rupy" and p2.suffix == ".py":
        return str(p1), str(p2)
    if p1.suffix == ".py" and p2.suffix == ".rupy":
        return str(p2), str(p1)

    raise ValueError("Нужно передать один файл .rupy и один файл .py")


class RuPyDebugger:
    def __init__(self, path1: str, path2: str):
        rupy_path, py_path = _split_paths(path1, path2)
        self.state = DebugState(rupy_path=rupy_path, py_path=py_path)

    def set_breakpoint(self, line: int) -> None:
        if line > 0:
            self.state.breakpoints.add(line)

    def remove_breakpoint(self, line: int) -> None:
        self.state.breakpoints.discard(line)

    def toggle_breakpoint(self, line: int) -> None:
        if line in self.state.breakpoints:
            self.state.breakpoints.remove(line)
        else:
            self.state.breakpoints.add(line)

    def load_rupy(self) -> str:
        return Path(self.state.rupy_path).read_text(encoding="utf-8")

    def load_py(self) -> str:
        return Path(self.state.py_path).read_text(encoding="utf-8")

    def run_debug(self, on_event: Optional[Callable[[DebugState], None]] = None) -> int:
        self.state.status = "running"
        py_path = Path(self.state.py_path)

        try:
            py_source = self.load_py()
            compiled = compile(py_source, str(py_path), "exec")
        except SyntaxError as e:
            self.state.status = "error"
            self.state.message = f"Ошибка синтаксиса в .py: {e}"
            if on_event:
                on_event(self.state)
            return 1

        def tracer(frame, event, arg):
            if frame.f_code.co_filename == str(py_path) and event == "line":
                self.state.current_line = frame.f_lineno
                self.state.current_locals = {
            k: v for k, v in frame.f_locals.items()
            if k not in ("__builtins__", "__name__", "__package__", "__loader__", "__spec__")
        }
                self.state.message = f"Строка {frame.f_lineno}"
                if frame.f_lineno in self.state.breakpoints:
                    self.state.status = "paused"
                    self.state.message = f"Брейкпоинт на строке {frame.f_lineno}"
                if on_event:
                    on_event(self.state)
            return tracer

        old_trace = sys.gettrace()
        sys.settrace(tracer)
        try:
            exec(compiled, {})
            if self.state.status != "paused":
                self.state.status = "done"
                self.state.message = "Выполнение завершено"
                if on_event:
                    on_event(self.state)
        except Exception as e:
            self.state.status = "error"
            self.state.message = f"Ошибка выполнения: {e}"
            if on_event:
                on_event(self.state)
            return 1
        finally:
            sys.settrace(old_trace)

        return 0


def run_debug(path1: str, path2: str, on_event=None) -> int:
    mode = detect_system()
    if mode == "termux":
        from termux import main as termux_main
        return termux_main(path1, path2, on_event=on_event)
    from tkinter_app import App
    app = App(path1, path2)
    app.mainloop()
    return 0