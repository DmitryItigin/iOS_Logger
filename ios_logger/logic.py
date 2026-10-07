"""Чистая логика фильтрации строк лога (без Qt) — вынесена для тестов."""

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


def extract_level(line: str) -> str:
    # Формат строки: "<ts> <level> <process>[<pid>]: <message>".
    level = line.split(" ", 2)[1] if line.count(" ") >= 2 else ""
    return level if level in LOG_LEVELS else "-"


def line_visible(line: str, filter_text: str, enabled_levels: set[str]) -> bool:
    """filter_text — уже в нижнем регистре и без пробелов по краям."""
    if filter_text and filter_text not in line.lower():
        return False
    return extract_level(line) in enabled_levels
