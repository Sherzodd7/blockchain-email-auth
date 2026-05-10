# config.py — Central configuration for all components
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ─── Flask ────────────────────────────────────────────────────────────────────
class Config:
    SECRET_KEY       = os.getenv("SECRET_KEY", "blockchain-email-auth-secret-2024")
    DEBUG            = os.getenv("DEBUG", "True") == "True"
    HOST             = os.getenv("HOST", "0.0.0.0")
    PORT             = int(os.getenv("PORT", 5000))

    # ─── Database ────────────────────────────────────────────────────────────
    DB_PATH          = str(BASE_DIR / "database" / "email_auth.db")

    # ─── Blockchain (Ganache) ─────────────────────────────────────────────────
    GANACHE_URL      = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
    CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")   # filled after deploy
    CHAIN_ID         = int(os.getenv("CHAIN_ID", 1337))    # Ganache default

    # ─── Crypto (RSA Keys) ────────────────────────────────────────────────────
    KEYS_DIR         = str(BASE_DIR / "keys")
    PRIVATE_KEY_PATH = str(BASE_DIR / "keys" / "private_key.pem")
    PUBLIC_KEY_PATH  = str(BASE_DIR / "keys" / "public_key.pem")
    RSA_KEY_SIZE     = 2048

    # ─── Logging ─────────────────────────────────────────────────────────────
    LOG_DIR          = str(BASE_DIR / "logs")
    LOG_FILE         = str(BASE_DIR / "logs" / "app.log")
    LOG_LEVEL        = "DEBUG"

    # ─── Security ────────────────────────────────────────────────────────────
    MAX_MESSAGE_LEN  = 5000
    MAX_EMAIL_LEN    = 254
    TRUST_SCORE_THRESHOLD = 50   # below this → low-trust warning

    # Phishing keywords (extendable)
    PHISHING_KEYWORDS = [
        "verify your account", "click here immediately", "your account has been suspended",
        "confirm your password", "urgent action required", "you have won",
        "free gift", "limited time offer", "update your billing",
        "unusual activity detected", "your paypal", "your bank account",
        "wire transfer", "nigerian prince", "lottery winner",
        "send your credentials", "reset your password now",
    ]


    