"""Log colouring: muted timestamp, level word tinted by severity (tokens, so it follows the theme)."""
import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

import qa_theme

from .logic import extract_level

_LINE = re.compile(r"^(\S+)\s+(\S+)")

# level -> token; levels not listed (and lines without a level) keep the normal text colour
LEVEL_TOKENS = {
    "FAULT": "error",
    "ERROR": "error",
    "NOTICE": "accent",
    "USER_ACTION": "text_muted",
    "INFO": "text_muted",
    "DEBUG": "text_muted",
}


def _format(color: str, bold: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Medium)
    return fmt


class LogHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt API)
        match = _LINE.match(text)
        if not match:
            return
        tokens = qa_theme.tokens()
        self.setFormat(match.start(1), match.end(1) - match.start(1), _format(tokens["text_muted"]))
        token = LEVEL_TOKENS.get(extract_level(text))
        if token:
            self.setFormat(match.start(2), match.end(2) - match.start(2), _format(tokens[token], bold=True))
