# app/utils/logger.py — Centralized colored logging
import logging
import os
import colorlog
from config import Config

def setup_logger(name: str = "blockchain_email_auth") -> logging.Logger:
    """
    Creates and returns a configured logger instance.
    Outputs to both console (colored) and rotating log file.
    """
    os.makedirs(Config.LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:          # avoid duplicate handlers on reload
        return logger

    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.DEBUG))

    # ── Console handler (colored) ─────────────────────────────────────────────
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s[%(asctime)s] %(levelname)s%(reset)s — %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "bold_red",
        }
    ))

    # ── File handler ──────────────────────────────────────────────────────────
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s — %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

# Module-level logger — import this wherever needed
log = setup_logger()
