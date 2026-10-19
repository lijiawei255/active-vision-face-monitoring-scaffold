"""Small logging setup shared by the CLI and examples."""

from __future__ import annotations

import logging
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(level: str = "INFO", log_file: str | Path | None = None) -> logging.Logger:
    logger = logging.getLogger("avfm")
    numeric = getattr(logging, str(level).upper(), None)
    if not isinstance(numeric, int):
        numeric = logging.INFO
    logger.setLevel(numeric)
    logger.propagate = False

    # Avoid duplicate handlers when called more than once (tests, notebooks).
    for handler in list(logger.handlers):
        if getattr(handler, "_avfm_managed", False):
            logger.removeHandler(handler)

    # ``_avfm_managed`` marks handlers owned by this module; ``logging.Handler``
    # has no typed slot for it, so the attribute assignment needs an ignore.
    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter(_FORMAT))
    stream._avfm_managed = True  # type: ignore[attr-defined]
    logger.addHandler(stream)

    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        file_handler._avfm_managed = True  # type: ignore[attr-defined]
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"avfm.{name}" if not name.startswith("avfm") else name)
