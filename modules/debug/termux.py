from __future__ import annotations

from pathlib import Path
from core import RuPyDebugger


def show_state(st):
    print("" + "=" * 60)
    print(f"Статус: {st.status}")
    print(f"Сообщение: {st.message}")
    print(f"Текущая строка: {st.current_line}")
    print("Брейкпоинты:", sorted(st.breakpoints))
    print("Переменные:")
    if st.current_locals:
        for k, v in st.current_locals.items():
            print(f"  {k} = {v!r}")
    else:
        print("  <пусто>")
    print("=" * 60)


def main(path1: str, path2: str, on_event=None):
    dbg = RuPyDebugger(path1, path2)

    print("Открыт файл:")
    print("rupy:", dbg.state.rupy_path)
    print("py  :", dbg.state.py_path)

    print("Команды:")
    print("  b N   - поставить брейкпоинт на строку N")
    print("  rb N  - снять брейкпоинт")
    print("  run   - запустить")
    print("  q     - выход")

    while True:
        cmd = input("ru-debug> ").strip().lower()
        if cmd == "q":
            break
        elif cmd.startswith("b "):
            line = int(cmd.split(maxsplit=1)[1])
            dbg.set_breakpoint(line)
            print(f"Брейкпоинт поставлен на строку {line}")
        elif cmd.startswith("rb "):
            line = int(cmd.split(maxsplit=1)[1])
            dbg.remove_breakpoint(line)
            print(f"Брейкпоинт снят со строки {line}")
        elif cmd == "run":
            dbg.run_debug(on_event=on_event or show_state)
        else:
            print("Неизвестная команда")

    return 0