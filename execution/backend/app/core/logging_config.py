"""Logging configuration.

Developer-facing logs are detailed; user-facing API messages stay short and
human (handled at the schema/route layer, not here). This module only wires up
the standard library logging with a single, predictable format.
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s :: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the application root."""
    return logging.getLogger(f"imo_ishora.{name}")


__all__ = ["configure_logging", "get_logger"]
