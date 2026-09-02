"""
iOS Log Viewer - минимальный просмотрщик логов с iOS-устройства по USB.

Требования:
    pip install -r requirements.txt
    Установлен драйвер Apple Mobile Device (idevice) - ставится вместе
    с iTunes или приложением "Apple Devices" из Microsoft Store.

Запуск:
    python ios_log_viewer.py
"""
import asyncio
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext

from pymobiledevice3 import usbmux
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.os_trace import OsTraceService

POLL_INTERVAL_MS = 100
DEVICE_POLL_INTERVAL_S = 1.0

# Порядок соответствует SyslogLogLevel из pymobiledevice3 (+ "-" для строк
# без определённого уровня).
LOG_LEVELS = ["FAULT", "ERROR", "USER_ACTION", "NOTICE", "INFO", "DEBUG", "-"]
LEVEL_LABELS = {
    "FAULT": "Fault",
    "ERROR": "Error",
    "USER_ACTION": "User action",
    "NOTICE": "Notice",
    "INFO": "Info",
    "DEBUG": "Debug",
    "-": "Без уровня",
}


class LogBackend:
    """Крутится в отдельном потоке с собственным asyncio event loop:
    ждёт подключения устройства и стримит из него syslog."""

    def __init__(self, line_queue: queue.Queue, status_queue: queue.Queue):
        self.line_queue = line_queue
        self.status_queue = status_queue
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._monitor())

    async def _monitor(self):
        stream_task = None
        connected_serial = None
        while True:
            try:
                devices = await usbmux.list_devices()
            except Exception:
                devices = []
            usb_devices = [d for d in devices if d.is_usb]

            if usb_devices:
                serial = usb_devices[0].serial
                if stream_task is None or stream_task.done():
                    connected_serial = serial
                    self.status_queue.put(("connected", serial))
                    stream_task = self.loop.create_task(self._stream(serial))
            else:
                if connected_serial is not None:
                    connected_serial = None
                    self.status_queue.put(("disconnected", None))
                if stream_task is not None and not stream_task.done():
                    stream_task.cancel()
                stream_task = None

            await asyncio.sleep(DEVICE_POLL_INTERVAL_S)

    async def _stream(self, serial: str):
        try:
            lockdown = await create_using_usbmux(serial=serial)
            async for entry in OsTraceService(lockdown=lockdown).syslog():
                ts = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
                # entry.level может быть 0 (NOTICE), а 0 - falsy, поэтому
                # сравнение именно с None (а не просто "if entry.level").
                level = entry.level.name if entry.level is not None else "-"
                process = entry.image_name or ""
                self.line_queue.put(f"{ts} {level:<7} {process}[{entry.pid}]: {entry.message}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.status_queue.put(("error", str(e)))


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("iOS Log Viewer")
        root.geometry("1000x600")

        toolbar = tk.Frame(root)
        toolbar.pack(fill=tk.X, padx=6, pady=6)

        self.pause_btn = tk.Button(toolbar, text="Пауза", width=12, command=self.toggle_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Очистить", width=12, command=self.clear).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Экспорт в файл", width=14, command=self.export).pack(side=tk.LEFT, padx=4)

        self.status_label = tk.Label(toolbar, text="Ожидание устройства...", anchor="e")
        self.status_label.pack(side=tk.RIGHT, padx=4)

        tk.Label(toolbar, text="Фильтр:").pack(side=tk.LEFT, padx=(12, 4))
        self.filter_entry = tk.Entry(toolbar, width=24)
        self.filter_entry.pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="✕", width=3, command=self.clear_filter).pack(side=tk.LEFT, padx=(2, 4))
        self.filter_count_label = tk.Label(toolbar, text="0/0", width=12)
        self.filter_count_label.pack(side=tk.LEFT, padx=4)

        self.filter_entry.bind("<KeyRelease>", self.on_filter_change)
        self.filter_entry.bind("<Escape>", self.clear_filter)

        self.level_vars: dict[str, tk.BooleanVar] = {
            level: tk.BooleanVar(value=True) for level in LOG_LEVELS
        }
        self.level_btn = tk.Button(toolbar, text="Уровни ▾", width=10, command=self.toggle_level_popup)
        self.level_btn.pack(side=tk.LEFT, padx=(8, 4))
        self.level_popup: tk.Toplevel | None = None

        self.search_frame = tk.Frame(root)
        tk.Label(self.search_frame, text="Найти:").pack(side=tk.LEFT, padx=(6, 4))
        self.search_entry = tk.Entry(self.search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=4)
        self.search_count_label = tk.Label(self.search_frame, text="0/0", width=8)
        self.search_count_label.pack(side=tk.LEFT, padx=4)
        tk.Button(self.search_frame, text="▲", width=3, command=self.search_prev).pack(side=tk.LEFT, padx=2)
        tk.Button(self.search_frame, text="▼", width=3, command=self.search_next).pack(side=tk.LEFT, padx=2)
        tk.Button(self.search_frame, text="✕", width=3, command=self.hide_search).pack(side=tk.LEFT, padx=(2, 4))

        self.search_entry.bind("<Return>", self.search_next)
        self.search_entry.bind("<Shift-Return>", self.search_prev)
        self.search_entry.bind("<KeyRelease>", self.on_search_change)
        self.search_entry.bind("<Escape>", self.hide_search)

        self.search_frame.pack(fill=tk.X, padx=6, pady=(0, 4))

        self.text = scrolledtext.ScrolledText(root, wrap=tk.NONE, font=("Consolas", 9))
        self.text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        self.text.configure(state=tk.DISABLED)
        self.text.tag_config("search_all", background="#ffe58a", foreground="black")
        self.text.tag_config("search_current", background="#ff9632", foreground="black")

        # Привязка по физическому keycode (70 = клавиша F), а не по символу:
        # при русской раскладке физическая F даёт символ "а", и биндинг
        # по символу "<Control-f>" в такой раскладке не срабатывает.
        root.bind("<Control-KeyPress>", self.on_ctrl_keypress)

        self.paused = False
        self.buffer: list[str] = []

        self.filter_text: str = ""
        self.visible_count: int = 0
        self._filter_after_id = None

        self.search_matches: list[tuple[str, str]] = []
        self.search_current = -1
        self.search_scan_pos = "1.0"

        self.line_queue: queue.Queue = queue.Queue()
        self.status_queue: queue.Queue = queue.Queue()
        self.backend = LogBackend(self.line_queue, self.status_queue)

        self.root.after(POLL_INTERVAL_MS, self.poll_queues)

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text="Продолжить" if self.paused else "Пауза")

    def clear(self):
        self.buffer.clear()
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)
        self.visible_count = 0
        self.update_filter_label()
        self.search_matches = []
        self.search_current = -1
        self.search_scan_pos = "1.0"
        self.update_search_label()

    def on_ctrl_keypress(self, event):
        if event.keycode == 70:  # физическая клавиша F, любая раскладка
            self.show_search(event)
        elif event.keycode == 86:  # физическая клавиша V, любая раскладка
            return self.paste_into_focused_entry()

    def paste_into_focused_entry(self):
        """На нелатинской раскладке штатный биндинг Ctrl+V у Entry не
        срабатывает (он завязан на keysym "v"), поэтому вставляем вручную -
        так же, как Ctrl+F выше завязан на физический keycode, а не символ."""
        widget = self.root.focus_get()
        if not isinstance(widget, tk.Entry):
            return None
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        if widget.selection_present():
            widget.delete("sel.first", "sel.last")
        widget.insert(tk.INSERT, text)
        # widget.insert() не эмулирует нажатие клавиши, поэтому биндинги
        # <KeyRelease> сами не сработают - обновляем фильтр/поиск вручную.
        if widget is self.filter_entry:
            if self._filter_after_id is not None:
                self.root.after_cancel(self._filter_after_id)
                self._filter_after_id = None
            self.apply_filter()
        elif widget is self.search_entry:
            self.run_search()
        return "break"

    def show_search(self, event=None):
        if not self.search_frame.winfo_ismapped():
            self.search_frame.pack(fill=tk.X, padx=6, pady=(0, 4), before=self.text)
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
        if self.search_entry.get():
            self.run_search()
        return "break"

    def hide_search(self, event=None):
        self.clear_search_tags()
        self.search_matches = []
        self.search_current = -1
        self.search_frame.pack_forget()
        self.text.focus_set()
        return "break"

    def on_search_change(self, event=None):
        if event is not None and event.keysym in ("Return", "Up", "Down", "Escape"):
            return
        self.run_search()

    def clear_search_tags(self):
        self.text.tag_remove("search_all", "1.0", tk.END)
        self.text.tag_remove("search_current", "1.0", tk.END)

    def on_filter_change(self, event=None):
        if event is not None and event.keysym == "Escape":
            return
        if self._filter_after_id is not None:
            self.root.after_cancel(self._filter_after_id)
        self._filter_after_id = self.root.after(150, self.apply_filter)

    def apply_filter(self):
        self._filter_after_id = None
        new_filter = self.filter_entry.get().strip().lower()
        if new_filter == self.filter_text:
            return
        self.filter_text = new_filter
        self.rerender_buffer()

    def clear_filter(self, event=None):
        if self._filter_after_id is not None:
            self.root.after_cancel(self._filter_after_id)
            self._filter_after_id = None
        self.filter_entry.delete(0, tk.END)
        self.apply_filter()
        return "break"

    def update_filter_label(self):
        self.filter_count_label.config(text=f"{self.visible_count}/{len(self.buffer)}")

    def extract_level(self, line: str) -> str:
        # Формат строки: "<ts> <level> <process>[<pid>]: <message>".
        level = line.split(" ", 2)[1] if line.count(" ") >= 2 else ""
        return level if level in self.level_vars else "-"

    def line_visible(self, line: str) -> bool:
        if self.filter_text and self.filter_text not in line.lower():
            return False
        return self.level_vars[self.extract_level(line)].get()

    def toggle_level_popup(self):
        if self.level_popup is not None and self.level_popup.winfo_exists():
            self.level_popup.destroy()
            self.level_popup = None
            return

        popup = tk.Toplevel(self.root)
        popup.title("Уровни логов")
        popup.transient(self.root)
        popup.resizable(False, False)
        x = self.level_btn.winfo_rootx()
        y = self.level_btn.winfo_rooty() + self.level_btn.winfo_height()
        popup.geometry(f"+{x}+{y}")

        btns = tk.Frame(popup)
        btns.pack(fill=tk.X, padx=6, pady=(6, 2))
        tk.Button(btns, text="Все", width=8, command=lambda: self.set_all_levels(True)).pack(side=tk.LEFT, padx=2)
        tk.Button(btns, text="Ничего", width=8, command=lambda: self.set_all_levels(False)).pack(side=tk.LEFT, padx=2)

        for level in LOG_LEVELS:
            tk.Checkbutton(
                popup,
                text=LEVEL_LABELS[level],
                variable=self.level_vars[level],
                command=self.apply_level_filter,
                anchor="w",
            ).pack(fill=tk.X, padx=8, pady=1)

        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
        popup.bind("<Escape>", lambda e: popup.destroy())
        self.level_popup = popup

    def set_all_levels(self, value: bool):
        for var in self.level_vars.values():
            var.set(value)
        self.apply_level_filter()

    def apply_level_filter(self):
        self.rerender_buffer()

    def rerender_buffer(self):
        self.clear_search_tags()
        visible = [line for line in self.buffer if self.line_visible(line)]
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        if visible:
            self.text.insert(tk.END, "\n".join(visible) + "\n")
        self.text.configure(state=tk.DISABLED)
        self.visible_count = len(visible)
        self.update_filter_label()
        self.search_matches = []
        self.search_current = -1
        self.search_scan_pos = self.text.index(f"{tk.END}-1c")
        if self.search_frame.winfo_ismapped() and self.search_entry.get():
            self.run_search()
        else:
            self.update_search_label()
        self.text.see(tk.END)

    def run_search(self):
        query = self.search_entry.get()
        self.clear_search_tags()
        self.search_matches = []
        self.search_current = -1
        if query:
            start = "1.0"
            while True:
                pos = self.text.search(query, start, stopindex=tk.END, nocase=True)
                if not pos:
                    break
                end = f"{pos}+{len(query)}c"
                self.text.tag_add("search_all", pos, end)
                self.search_matches.append((pos, end))
                start = end
        self.search_scan_pos = self.text.index(f"{tk.END}-1c")
        if self.search_matches:
            self.search_current = 0
            self.highlight_current()
        else:
            self.update_search_label()

    def append_search_matches(self):
        """Дозаписывает совпадения в уже отрисованных новых строках лога,
        не сбрасывая текущую позицию поиска (старые индексы не смещаются,
        т.к. новый текст всегда добавляется в конец)."""
        if not self.search_frame.winfo_ismapped():
            return
        query = self.search_entry.get()
        if not query:
            return
        start = self.search_scan_pos
        end_of_doc = self.text.index(f"{tk.END}-1c")
        while True:
            pos = self.text.search(query, start, stopindex=end_of_doc, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(query)}c"
            self.text.tag_add("search_all", pos, end)
            self.search_matches.append((pos, end))
            start = end
        self.search_scan_pos = end_of_doc
        if self.search_current == -1 and self.search_matches:
            self.search_current = 0
            self.highlight_current()
        else:
            self.update_search_label()

    def update_search_label(self):
        total = len(self.search_matches)
        current = self.search_current + 1 if self.search_matches else 0
        self.search_count_label.config(text=f"{current}/{total}")

    def highlight_current(self):
        self.text.tag_remove("search_current", "1.0", tk.END)
        if not self.search_matches:
            self.update_search_label()
            return
        pos, end = self.search_matches[self.search_current]
        self.text.tag_add("search_current", pos, end)
        self.text.see(pos)
        self.update_search_label()

    def search_next(self, event=None):
        if not self.search_matches:
            self.run_search()
            return "break"
        self.search_current = (self.search_current + 1) % len(self.search_matches)
        self.highlight_current()
        return "break"

    def search_prev(self, event=None):
        if not self.search_matches:
            self.run_search()
            return "break"
        self.search_current = (self.search_current - 1) % len(self.search_matches)
        self.highlight_current()
        return "break"

    def export(self):
        if not self.buffer:
            messagebox.showinfo("Экспорт", "Буфер логов пуст.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt"), ("Все файлы", "*.*")],
            initialfile=f"ios_log_{datetime.now():%Y%m%d_%H%M%S}.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.buffer))
        except OSError as e:
            messagebox.showerror("Экспорт", f"Не удалось сохранить файл: {e}")
        else:
            messagebox.showinfo("Экспорт", f"Сохранено: {path}")

    def poll_queues(self):
        while not self.status_queue.empty():
            kind, value = self.status_queue.get_nowait()
            if kind == "connected":
                self.status_label.config(text=f"Подключено: {value}")
            elif kind == "disconnected":
                self.status_label.config(text="Ожидание устройства...")
            elif kind == "error":
                self.status_label.config(text=f"Ошибка: {value}")

        lines = []
        while not self.line_queue.empty():
            lines.append(self.line_queue.get_nowait())

        if lines and not self.paused:
            self.buffer.extend(lines)
            matching = [line for line in lines if self.line_visible(line)]
            if matching:
                self.text.configure(state=tk.NORMAL)
                for line in matching:
                    self.text.insert(tk.END, line + "\n")
                self.text.configure(state=tk.DISABLED)
                self.visible_count += len(matching)
            self.update_filter_label()
            self.append_search_matches()
            if not (self.search_frame.winfo_ismapped() and self.search_matches):
                self.text.see(tk.END)

        self.root.after(POLL_INTERVAL_MS, self.poll_queues)


def main():
    root = tk.Tk()
    App(root)
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass
    root.mainloop()


if __name__ == "__main__":
    main()
