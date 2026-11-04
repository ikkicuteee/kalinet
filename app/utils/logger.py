"""Rotating per-user logs; no root permissions required."""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def state_directory():
    base = Path(os.environ.get("XDG_STATE_HOME", ""))
    if not base.is_absolute():
        base = Path.home() / ".local" / "state"
    return base / "kalinet"


def configure_logging():
    directory = state_directory()
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("kalinet")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(directory / "kalinet.log", maxBytes=1_000_000,
                                      backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger
