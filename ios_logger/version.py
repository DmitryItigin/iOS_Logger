"""Версия сборки: файл _version.py генерирует CI из git-тега (см. release.yml)."""
try:
    from ._version import VERSION
except ImportError:
    VERSION = "dev"  # запуск из исходников — тега нет
