"""Logging setup (stdout only — let the process manager / container collect logs)."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
    )
