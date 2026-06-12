"""
termux.py — TUI-дебаггер для ru-python (Textual 8.x).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets._rich_log import RichLog
from textual.widgets._footer import Footer
from textual.widgets._header import Header
from textual.widgets._static import Static
from textual.widgets._input import Input
from rich.text import Text

DEBUG_DIR = Path(__file__).resolve().parent
if str(DEBUG_DIR) not in sys.path:
    sys.path.insert(0, str(DEBUG_DIR))

from core import RuPyDebugger, DebugState  # noqa: E402


class DebuggerApp(App):
    TITLE = "RuPy Debugger"

    CSS = """
    Screen {
        background: #121212;
        layout: vertical;
    }
    #toolbar {
        height: 1;
        background: #1a2a40;
        padding: 0 1;
        color: #7a9abf;
    }
    #sources {
        layout: horizontal;
        height: 1fr;
        min-height: 8;
    }
    #src_rupy_log {
        width: 1fr;
        height: 100%;
        border: solid #0053aa;
    }
    #src_py_log {
        width: 1fr;
        height: 100%;
        border: solid #0053aa;
    }
    #bottom {
        layout: horizontal;
        height: 14;
    }
    #vars_log {
        width: 1fr;
        height: 100%;
        border: solid #1e5f2a;
    }
    #log_pane {
        width: 2fr;
        height: 100%;
        layout: vertical;
        border: solid #5f1e1e;
    }
    #output_log {
        height: 1fr;
        padding: 0 1;
    }
    #cmd_input {
        height: 3;
        dock: bottom;
    }
    #status_bar {
        height: 1;
        background: #1a2a40;
        padding: 0 1;
        color: #7a9abf;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("f5",         "run_debug",        "F5 Запуск",   show=True),
        Binding("f2",         "clear_breakpoints", "F2 Сброс BP", show=True),
        Binding("ctrl+r",     "reload_files",      "^R Reload",   show=True),
        Binding("ctrl+q",     "quit",              "^Q Выход",    show=True),
        #Binding("ctrl+right", "scroll_right",  "^→ Вправо", show=True),
      #  Binding("ctrl+left",  "scroll_left",   "^← Влево",  show=True),
    ]

    def __init__(self, path1: str, path2: str):
        super().__init__()
        self.dbg = RuPyDebugger(path1, path2)
        self._running = False
        self._rupy_lines: list[str] = []
        self._py_lines: list[str] = []
        self._h_scroll: int = 0  # сдвиг по горизонтали (в символах)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            f" rupy: {Path(self.dbg.state.rupy_path).name}"
            f"  py: {Path(self.dbg.state.py_path).name}",
            id="toolbar",
        )
        with Container(id="sources"):
            yield RichLog(id="src_rupy_log", highlight=False, markup=False, wrap=True)
            yield RichLog(id="src_py_log",   highlight=False, markup=False, wrap=True)
        with Container(id="bottom"):
            yield RichLog(id="vars_log", highlight=True, markup=True, wrap=True)
            with Container(id="log_pane"):
                yield RichLog(id="output_log", highlight=True, markup=True, wrap=True)
                yield Input(
                    placeholder="b<N> rb<N> run reload vars bp clear help q",
                    id="cmd_input",
                )
        yield Static("", id="status_bar")
        yield Footer()

    def on_mount(self) -> None:
        self._reload_sources()
        self._log("[bold cyan]RuPy Debugger[/] — добро пожаловать!")
        self._log("[dim] ↑↓ ← → скролл выбранного окна · F5 запуск · F2 сброс BP · ^R reload · ^Q выход · help справка[/dim]")
        self.query_one("#cmd_input").focus()

    # ── helpers ───────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        self.query_one("#output_log", RichLog).write(msg)

    def _set_status(self, msg: str) -> None:
        self.query_one("#status_bar", Static).update(f" {msg}")

    def _render_source(self, log_id: str, lines: list[str]) -> None:
        bp  = self.dbg.state.breakpoints
        cur = self.dbg.state.current_line
        log = self.query_one(log_id, RichLog)
        log.clear()
        for i, line in enumerate(lines, start=1):
            is_bp  = i in bp
            is_cur = i == cur
            t = Text(no_wrap=True)
            if is_cur:
                t.append(f"{i:4d} ", style="bold green")
            elif is_bp:
                t.append(f"{i:4d} ", style="bold red")
            else:
                t.append(f"{i:4d} ", style="dim")
            t.append("●" if is_bp  else " ", style="bold red"   if is_bp  else "")
            t.append("▶" if is_cur else " ", style="bold green" if is_cur else "")
            t.append(" ")
            visible = line[self._h_scroll:]
            if is_cur:
                t.append(visible, style="bold yellow on #00305a")
            elif is_bp:
                t.append(visible, style="on #2a0000")
            else:
                t.append(visible)
            log.write(t)

    def _reload_sources(self) -> None:
        try:
            self._rupy_lines = Path(self.dbg.state.rupy_path).read_text("utf-8").splitlines()
        except Exception as e:
            self._rupy_lines = [f"# Ошибка чтения: {e}"]
        try:
            self._py_lines = Path(self.dbg.state.py_path).read_text("utf-8").splitlines()
        except Exception as e:
            self._py_lines = [f"# Ошибка чтения: {e}"]
        self._refresh_markers()

    def _refresh_markers(self) -> None:
        self._render_source("#src_rupy_log", self._rupy_lines)
        self._render_source("#src_py_log",   self._py_lines)
        cur = self.dbg.state.current_line
        if cur > 0:
            for lid in ("#src_rupy_log", "#src_py_log"):
                self.query_one(lid, RichLog).scroll_to(y=max(0, cur - 3), animate=False)

    def _update_vars(self, locals_: dict) -> None:
        log = self.query_one("#vars_log", RichLog)
        log.clear()
        log.write("[bold #aaffaa] Переменные[/]")
        if not locals_:
            log.write("[dim]— пусто —[/dim]")
            return
        for k, v in locals_.items():
            val = repr(v)
            if len(val) > 48:
                val = val[:45] + "..."
            log.write(f"[cyan]{k}[/] [dim]=[/dim] [yellow]{val}[/]")

    # ── debug callback ────────────────────────────────────────────────────

    def _on_debug_event(self, st: DebugState) -> None:
        self.call_from_thread(self._apply_state, st)

    def _apply_state(self, st: DebugState) -> None:
        self._refresh_markers()
        self._update_vars(st.current_locals)
        color = {
            "running": "green", "paused": "yellow",
            "done": "cyan",     "error":  "red",
        }.get(st.status, "white")
        self._log(f"[{color}]{st.message}[/]")
        self._set_status(f"[{st.status}] {st.message}")
        if st.status == "paused":
            self._log(
                f"[yellow]⏸ Пауза на строке {st.current_line}. "
                "Введите [bold]run[/bold] для продолжения.[/]"
            )
        if st.status in ("done", "error"):
            self._running = False

    # ── actions ───────────────────────────────────────────────────────────

   # def action_scroll_right(self) -> None:
    #    self._h_scroll += 4
   #     self._refresh_markers()
   #     self._set_status(f"Горизонтальный сдвиг: {self._h_scroll}")

   # def action_scroll_left(self) -> None:
  #      self._h_scroll = max(0, self._h_scroll - 4)
   #     self._refresh_markers()
    #    self._set_status(f"Горизонтальный сдвиг: {self._h_scroll}")

    def action_run_debug(self) -> None:
        if self._running:
            self._log("[yellow]Уже запущено.[/]")
            return
        self._running = True
        self._set_status("Запуск...")
        self._log("[green]▶ Запуск...[/]")
        threading.Thread(
            target=lambda: self.dbg.run_debug(on_event=self._on_debug_event),
            daemon=True,
        ).start()

    def action_clear_breakpoints(self) -> None:
        self.dbg.state.breakpoints.clear()
        self._refresh_markers()
        self._log("[dim]Все брейкпоинты сняты.[/]")
        self._set_status("Брейкпоинты сброшены")

    def action_reload_files(self) -> None:
        self._reload_sources()
        self._log("[cyan]↻ Файлы перечитаны.[/]")
        self._set_status("Файлы обновлены")

    # ── input ─────────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        event.input.value = ""
        if not raw:
            return
        self._log(f"[dim]› {raw}[/]")
        self._handle_cmd(raw)

    def _handle_cmd(self, cmd: str) -> None:
        low = cmd.lower()
        if low in ("q", "quit", "exit"):
            self.exit()
        elif low in ("run", "r", "continue", "c"):
            self.action_run_debug()
        elif low in ("reload", "refresh"):
            self.action_reload_files()
        elif low in ("clear", "cls"):
            self.query_one("#output_log", RichLog).clear()
        elif low.startswith("b "):
            try:
                n = int(low.split()[1])
                self.dbg.set_breakpoint(n)
                self._log(f"[red]● BP на строке {n}[/]")
                self._refresh_markers()
            except (ValueError, IndexError):
                self._log("[red]Формат: b <N>[/]")
        elif low.startswith("rb "):
            try:
                n = int(low.split()[1])
                self.dbg.remove_breakpoint(n)
                self._log(f"[dim]○ BP снят со строки {n}[/]")
                self._refresh_markers()
            except (ValueError, IndexError):
                self._log("[red]Формат: rb <N>[/]")
        elif low.startswith("tb "):
            try:
                n = int(low.split()[1])
                self.dbg.toggle_breakpoint(n)
                s = "поставлен" if n in self.dbg.state.breakpoints else "снят"
                self._log(f"[cyan]BP {s} на строке {n}[/]")
                self._refresh_markers()
            except (ValueError, IndexError):
                self._log("[red]Формат: tb <N>[/]")
        elif low in ("bp", "breakpoints", "list"):
            bps = sorted(self.dbg.state.breakpoints)
            self._log(f"[cyan]Брейкпоинты: {bps or '—'}[/]")
        elif low in ("vars", "locals", "v"):
            self._update_vars(self.dbg.state.current_locals)
        elif low in ("help", "?", "h"):
            self._log(
                "[bold cyan]Клавиши:[/] F5=запуск F2=сброс ^R=reload ^Q=выход ↑ / ↓ / ← / →=скролл(нужно нажать на нужное окно)\n",
                "\n[bold cyan]Команды:[/]\n"
                "  [green]run[/] / [green]r[/]  — запустить\n"
                "  [green]b <N>[/]     — поставить BP\n"
                "  [green]rb <N>[/]    — снять BP\n"
                "  [green]tb <N>[/]    — переключить BP\n"
                "  [green]bp[/]        — список BP\n"
                "  [green]vars[/]      — переменные\n"
                "  [green]reload[/]    — перечитать файлы\n"
                "  [green]clear[/]     — очистить лог\n"
                "  [green]q[/]         — выход\n"
                            )
        else:
            self._log(f"[red]Неизвестно:[/] {cmd}  ([dim]help[/dim] — справка)")


def main(path1: str, path2: str, on_event=None) -> int:
    DebuggerApp(path1, path2).run()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python termux.py <file.rupy> <file.py>")
        sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2]))
