"""Structured-ish logging setup using the standard library.

We keep dependencies light: a JSON-ish key=value formatter is enough to make
pipeline stages greppable without pulling in structlog. Swap the handler here if
you adopt structlog later.
"""
from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s level=%(levelname)s logger=%(name)s %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
