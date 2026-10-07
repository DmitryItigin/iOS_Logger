"""Главное окно iOS Log Viewer (PySide6)."""
import queue
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from .logic import LEVEL_LABELS, LOG_LEVELS, line_visible
from .theme import ThemeToggleButton

APP_NAME = "iOS-Logger"
POLL_INTERVAL_MS = 100
FILTER_DEBOUNCE_MS = 150
VK_F = 0x46  # физическая клавиша F (Windows virtual-key), одинакова в любой раскладке
SEARCH_ALL_BG = QColor("#ffe58a")
SEARCH_CURRENT_BG = QColor("#ff9632")


def _match_selection(start: int, end: int, document: QTextDocument, color: QColor) -> QTextEdit.ExtraSelection:
    selection = QTextEdit.ExtraSelection()
    cursor = QTextCursor(document)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    selection.cursor = cursor
    fmt = QTextCharFormat()
    fmt.setBackground(color)
    fmt.setForeground(QColor("black"))
    selection.format = fmt
    return selection


class MainWindow(QMainWindow):
    def __init__(self, line_queue: queue.Queue, status_queue: queue.Queue):
        super().__init__()
        self.line_queue = line_queue
        self.status_queue = status_queue

        self.paused = False
        self.buffer: list[str] = []
        self.filter_text = ""
        self.visible_count = 0
        self.enabled_levels: set[str] = set(LOG_LEVELS)

        self.search_matches: list[tuple[int, int]] = []
        self.search_current = -1
        self.search_scan_pos = 0
        self._match_selections: list[QTextEdit.ExtraSelection] = []

        self.setWindowTitle("iOS Log Viewer")
        self.resize(1000, 600)
        self._build_ui()

        self._filter_timer = QTimer(self, singleShot=True, interval=FILTER_DEBOUNCE_MS)
        self._filter_timer.timeout.connect(self.apply_filter)
        self._poll_timer = QTimer(self, interval=POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self.poll_queues)
        self._poll_timer.start()

    # --- UI ---

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        toolbar = QHBoxLayout()
        self.pause_btn = QPushButton("Пауза")
        self.pause_btn.clicked.connect(self.toggle_pause)
        toolbar.addWidget(self.pause_btn)
        clear_btn = QPushButton("Очистить")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)
        export_btn = QPushButton("Экспорт в файл")
        export_btn.clicked.connect(self.export)
        toolbar.addWidget(export_btn)

        toolbar.addSpacing(12)
        toolbar.addWidget(QLabel("Фильтр:"))
        self.filter_entry = QLineEdit()
        self.filter_entry.setMinimumWidth(200)
        self.filter_entry.setClearButtonEnabled(True)
        self.filter_entry.textEdited.connect(lambda _text: self._filter_timer.start())
        self.filter_entry.textChanged.connect(self._on_filter_text_changed)
        toolbar.addWidget(self.filter_entry)
        self.filter_count_label = QLabel("0/0")
        self.filter_count_label.setMinimumWidth(80)
        toolbar.addWidget(self.filter_count_label)
        toolbar.addWidget(self._build_levels_button())

        toolbar.addStretch()
        self.status_label = QLabel("Ожидание устройства...")
        toolbar.addWidget(self.status_label)
        toolbar.addWidget(ThemeToggleButton(APP_NAME))
        root.addLayout(toolbar)

        self.search_frame = self._build_search_bar()
        root.addWidget(self.search_frame)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text.setFont(QFont("Consolas", 9))
        root.addWidget(self.text, 1)

        self.setCentralWidget(central)

    def _build_levels_button(self) -> QToolButton:
        button = QToolButton()
        button.setText("Уровни ▾")
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        quick = QHBoxLayout()
        all_btn = QPushButton("Все")
        none_btn = QPushButton("Ничего")
        quick.addWidget(all_btn)
        quick.addWidget(none_btn)
        layout.addLayout(quick)

        self.level_checks: dict[str, QCheckBox] = {}
        for level in LOG_LEVELS:
            check = QCheckBox(LEVEL_LABELS[level])
            check.setChecked(True)
            check.toggled.connect(self._on_levels_changed)
            self.level_checks[level] = check
            layout.addWidget(check)
        all_btn.clicked.connect(lambda: self._set_all_levels(True))
        none_btn.clicked.connect(lambda: self._set_all_levels(False))

        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        button.setMenu(menu)
        return button

    def _build_search_bar(self) -> QWidget:
        frame = QWidget()
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel("Найти:"))
        self.search_entry = QLineEdit()
        self.search_entry.setMinimumWidth(240)
        self.search_entry.textEdited.connect(lambda _text: self.run_search())
        self.search_entry.returnPressed.connect(self._on_search_enter)
        row.addWidget(self.search_entry)
        self.search_count_label = QLabel("0/0")
        self.search_count_label.setMinimumWidth(60)
        row.addWidget(self.search_count_label)
        prev_btn = QPushButton("▲")
        prev_btn.setFixedWidth(36)
        prev_btn.clicked.connect(self.search_prev)
        row.addWidget(prev_btn)
        next_btn = QPushButton("▼")
        next_btn.setFixedWidth(36)
        next_btn.clicked.connect(self.search_next)
        row.addWidget(next_btn)
        close_btn = QPushButton("✕")
        close_btn.setFixedWidth(36)
        close_btn.clicked.connect(self.hide_search)
        row.addWidget(close_btn)
        row.addStretch()
        return frame

    # --- keyboard ---

    def keyPressEvent(self, event) -> None:
        ctrl = event.modifiers() & Qt.ControlModifier
        if ctrl and event.nativeVirtualKey() == VK_F:
            self.show_search()
            return
        if event.key() == Qt.Key_Escape:
            if self.search_entry.hasFocus():
                self.hide_search()
                return
            if self.filter_entry.hasFocus():
                self.filter_entry.clear()
                self._filter_timer.stop()
                self.apply_filter()
                return
        super().keyPressEvent(event)

    def _on_search_enter(self) -> None:
        if QApplication.keyboardModifiers() & Qt.ShiftModifier:
            self.search_prev()
        else:
            self.search_next()

    # --- toolbar actions ---

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_btn.setText("Продолжить" if self.paused else "Пауза")
        if not self.paused:
            self.rerender_buffer()  # показать всё, что пришло за время паузы

    def clear(self) -> None:
        self.buffer.clear()
        self.text.clear()
        self.visible_count = 0
        self.update_filter_label()
        self._reset_search_state()
        self.update_search_label()

    def update_filter_label(self) -> None:
        self.filter_count_label.setText(f"{self.visible_count}/{len(self.buffer)}")

    # --- filtering ---

    def _on_filter_text_changed(self, text: str) -> None:
        if not text:  # кнопка очистки в поле / Escape — применяем сразу
            self._filter_timer.stop()
            self.apply_filter()

    def apply_filter(self) -> None:
        new_filter = self.filter_entry.text().strip().lower()
        if new_filter == self.filter_text:
            return
        self.filter_text = new_filter
        self.rerender_buffer()

    def _on_levels_changed(self) -> None:
        self.enabled_levels = {level for level, check in self.level_checks.items() if check.isChecked()}
        self.rerender_buffer()

    def _set_all_levels(self, value: bool) -> None:
        for check in self.level_checks.values():
            check.blockSignals(True)
            check.setChecked(value)
            check.blockSignals(False)
        self._on_levels_changed()

    def _visible(self, line: str) -> bool:
        return line_visible(line, self.filter_text, self.enabled_levels)

    def rerender_buffer(self) -> None:
        visible = [line for line in self.buffer if self._visible(line)]
        self.text.setPlainText("\n".join(visible) + "\n" if visible else "")
        self.visible_count = len(visible)
        self.update_filter_label()
        self._reset_search_state()
        if self.search_frame.isVisible() and self.search_entry.text():
            self.run_search()
        else:
            self.update_search_label()
        self._scroll_to_end()

    def _scroll_to_end(self) -> None:
        bar = self.text.verticalScrollBar()
        bar.setValue(bar.maximum())

    # --- search ---

    def _doc_end(self) -> int:
        return self.text.document().characterCount() - 1

    def _reset_search_state(self) -> None:
        self.search_matches = []
        self.search_current = -1
        self.search_scan_pos = self._doc_end()
        self._match_selections = []
        self.text.setExtraSelections([])

    def show_search(self) -> None:
        self.search_frame.show()
        self.search_entry.setFocus()
        self.search_entry.selectAll()
        if self.search_entry.text():
            self.run_search()

    def hide_search(self) -> None:
        self.search_frame.hide()
        self._reset_search_state()
        self.update_search_label()
        self.text.setFocus()

    def _find_all(self, query: str, start: int, stop: int) -> list[tuple[int, int]]:
        found = []
        document = self.text.document()
        position = start
        while True:
            cursor = document.find(query, position)  # без регистра по умолчанию
            if cursor.isNull() or cursor.selectionEnd() > stop:
                break
            found.append((cursor.selectionStart(), cursor.selectionEnd()))
            position = cursor.selectionEnd()
        return found

    def run_search(self) -> None:
        query = self.search_entry.text()
        self.search_matches = self._find_all(query, 0, self._doc_end()) if query else []
        self.search_current = 0 if self.search_matches else -1
        self.search_scan_pos = self._doc_end()
        document = self.text.document()
        self._match_selections = [
            _match_selection(start, end, document, SEARCH_ALL_BG) for start, end in self.search_matches
        ]
        self.refresh_search_highlights()

    def append_search_matches(self) -> None:
        """Дозаписывает совпадения в новых строках, не сбрасывая текущую позицию
        поиска (старые индексы не смещаются: новый текст всегда добавляется в конец).
        Вид не прокручивается, кроме случая, когда появилось первое совпадение."""
        query = self.search_entry.text()
        if not self.search_frame.isVisible() or not query:
            return
        end_of_doc = self._doc_end()
        new_matches = self._find_all(query, self.search_scan_pos, end_of_doc)
        self.search_scan_pos = end_of_doc
        if not new_matches:
            return
        document = self.text.document()
        self.search_matches += new_matches
        self._match_selections += [
            _match_selection(start, end, document, SEARCH_ALL_BG) for start, end in new_matches
        ]
        first_match = self.search_current == -1
        if first_match:
            self.search_current = 0
        self.refresh_search_highlights(scroll=first_match)

    def refresh_search_highlights(self, scroll: bool = True) -> None:
        document = self.text.document()
        selections = list(self._match_selections)
        if 0 <= self.search_current < len(self.search_matches):
            start, end = self.search_matches[self.search_current]
            selections.append(_match_selection(start, end, document, SEARCH_CURRENT_BG))
            if scroll:
                cursor = QTextCursor(document)
                cursor.setPosition(start)
                self.text.setTextCursor(cursor)
                self.text.centerCursor()
        self.text.setExtraSelections(selections)
        self.update_search_label()

    def update_search_label(self) -> None:
        total = len(self.search_matches)
        current = self.search_current + 1 if self.search_matches else 0
        self.search_count_label.setText(f"{current}/{total}")

    def search_next(self) -> None:
        if not self.search_matches:
            self.run_search()
            return
        self.search_current = (self.search_current + 1) % len(self.search_matches)
        self.refresh_search_highlights()

    def search_prev(self) -> None:
        if not self.search_matches:
            self.run_search()
            return
        self.search_current = (self.search_current - 1) % len(self.search_matches)
        self.refresh_search_highlights()

    # --- export ---

    def export(self) -> None:
        if not self.buffer:
            QMessageBox.information(self, "Экспорт", "Буфер логов пуст.")
            return

        lines_to_export = self.buffer
        filter_active = bool(self.filter_text) or len(self.enabled_levels) != len(LOG_LEVELS)
        if filter_active:
            choice = QMessageBox.question(
                self,
                "Экспорт",
                f"Сейчас применён фильтр: показано {self.visible_count} из {len(self.buffer)} строк.\n\n"
                "Экспортировать только отфильтрованные строки?\n"
                "«Нет» — экспортировать весь лог целиком.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if choice == QMessageBox.Cancel:
                return
            if choice == QMessageBox.Yes:
                lines_to_export = [line for line in self.buffer if self._visible(line)]

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт",
            f"ios_log_{datetime.now():%Y%m%d_%H%M%S}.txt",
            "Текстовый файл (*.txt);;Все файлы (*.*)",
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".txt"  # нативный диалог Windows не дописывает расширение сам
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines_to_export))
        except OSError as e:
            QMessageBox.critical(self, "Экспорт", f"Не удалось сохранить файл: {e}")
        else:
            QMessageBox.information(self, "Экспорт", f"Сохранено: {path}")

    # --- stream ---

    def poll_queues(self) -> None:
        while not self.status_queue.empty():
            kind, value = self.status_queue.get_nowait()
            if kind == "connected":
                self.status_label.setText(f"Подключено: {value}")
            elif kind == "disconnected":
                self.status_label.setText("Ожидание устройства...")
            elif kind == "error":
                self.status_label.setText(f"Ошибка: {value}")

        lines = []
        while not self.line_queue.empty():
            lines.append(self.line_queue.get_nowait())
        if not lines:
            return

        self.buffer.extend(lines)
        if self.paused:
            # Пока пауза, строки копятся в буфере, но не рисуются; при «Продолжить» они появятся.
            self.update_filter_label()
            return
        matching = [line for line in lines if self._visible(line)]
        if matching:
            cursor = QTextCursor(self.text.document())
            cursor.movePosition(QTextCursor.End)
            cursor.insertText("\n".join(matching) + "\n")
            self.visible_count += len(matching)
        self.update_filter_label()
        self.append_search_matches()
        if not (self.search_frame.isVisible() and self.search_matches):
            self._scroll_to_end()

