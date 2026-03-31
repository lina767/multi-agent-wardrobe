"""Structured-ish logging baseline for local / self-hosted runs."""

import logging
import sys
from typing import Any

from app.config import settings


class KeyValueFormatter(logging.Formatter):
    """Renders extras as key=value for grep-friendly logs."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord("", 0, "", 0, (), None, None).__dict__ and not k.startswith("_")
        }
        if not extras:
            return base
        tail = " ".join(f"{k}={v!r}" for k, v in sorted(extras.items()))
        return f"{base} | {tail}"


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    if not root.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(KeyValueFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(h)


def log_metric(logger: logging.Logger, name: str, value: Any, **fields: Any) -> None:
    logger.info("metric %s=%s", name, value, extra=fields)
