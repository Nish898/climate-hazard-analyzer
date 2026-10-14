"""Structured (JSON-lines) logging with automatic deletion of old log files.

Logs go to stdout (for `docker compose logs`) and, optionally, to a daily-rotated
file. Rotated files older than LOG_RETENTION_DAYS are deleted on startup and at
every rollover.
"""
import json
import logging
import os
import re
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from .config import settings

LOG_FILE_NAME = "app.log"
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has; anything else was passed via `extra=` and is emitted as a field.
_STD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}
_SECRET_URI = re.compile(r"(\w+://)[^/\s:@]+:[^/\s@]+@")


def _redact(text: str) -> str:
    """Strip credentials from URIs such as mongodb://user:pass@host."""
    return _SECRET_URI.sub(r"\1***:***@", text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(record.getMessage()),
        }
        rid = request_id_var.get()
        if rid:
            entry["request_id"] = rid
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exception"] = _redact(self.formatException(record.exc_info))
        return json.dumps(entry, default=str)


def purge_old_logs(log_dir: Path, retention_days: int) -> int:
    """Delete rotated log files whose last write is older than `retention_days`."""
    cutoff = time.time() - retention_days * 86400
    removed = 0
    for path in log_dir.glob(f"{LOG_FILE_NAME}*"):
        if path.name == LOG_FILE_NAME:
            continue  # never delete the file currently being written
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


class RetentionFileHandler(TimedRotatingFileHandler):
    """Rotates at midnight UTC (or early, past `max_bytes`) and deletes files older than the retention window."""

    def __init__(self, log_dir: Path, retention_days: int, max_bytes: int = 0):
        super().__init__(log_dir / LOG_FILE_NAME, when="midnight", utc=True, backupCount=0, encoding="utf-8")
        self.log_dir, self.retention_days, self.max_bytes = log_dir, retention_days, max_bytes
        self.namer = self._unique_name

    @staticmethod
    def _unique_name(default: str) -> str:
        """Suffix .1, .2, ... so a second rotation on the same day does not overwrite the first."""
        if not os.path.exists(default):
            return default
        n = 1
        while os.path.exists(f"{default}.{n}"):
            n += 1
        return f"{default}.{n}"

    def shouldRollover(self, record: logging.LogRecord) -> bool:
        if super().shouldRollover(record):
            return True
        if self.max_bytes and self.stream is not None:
            self.stream.seek(0, os.SEEK_END)
            return self.stream.tell() >= self.max_bytes
        return False

    def doRollover(self) -> None:
        super().doRollover()
        purge_old_logs(self.log_dir, self.retention_days)


def setup_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())
    formatter = JsonFormatter()

    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(formatter)
    root.addHandler(stdout)

    if settings.log_to_file:
        log_dir = Path(settings.log_dir)
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            removed = purge_old_logs(log_dir, settings.log_retention_days)
            file_handler = RetentionFileHandler(log_dir, settings.log_retention_days, settings.log_max_mb * 1024 * 1024)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as exc:  # e.g. read-only filesystem: keep serving, log to stdout only
            removed = 0
            root.warning("File logging disabled: cannot use %s (%s)", log_dir, exc)
        else:
            root.info(
                "Logging initialised",
                extra={"log_dir": str(log_dir), "retention_days": settings.log_retention_days, "purged_files": removed},
            )

    for name in ("httpx", "httpcore"):  # openmeteo.py logs upstream calls itself
        logging.getLogger(name).setLevel(logging.WARNING)

    # Route uvicorn's own loggers through our handlers; our middleware logs requests itself.
    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False
