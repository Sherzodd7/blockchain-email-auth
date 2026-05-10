# app/utils/validators.py — Input validation & sanitisation
import re
import base64
from config import Config

# ─── Regex patterns ───────────────────────────────────────────────────────────
EMAIL_RE    = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
SAFE_TEXT_RE = re.compile(r"[<>\"'%;()&+]")   # basic XSS chars


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def validate_email(email: str) -> str:
    """Validate and normalise an email address."""
    if not email or not isinstance(email, str):
        raise ValidationError("Email is required.")
    email = email.strip().lower()
    if len(email) > Config.MAX_EMAIL_LEN:
        raise ValidationError(f"Email exceeds {Config.MAX_EMAIL_LEN} characters.")
    if not EMAIL_RE.match(email):
        raise ValidationError("Invalid email format.")
    return email


def validate_message(message: str) -> str:
    """Validate and sanitise a message body."""
    if not message or not isinstance(message, str):
        raise ValidationError("Message body is required.")
    message = message.strip()
    if len(message) == 0:
        raise ValidationError("Message cannot be blank.")
    if len(message) > Config.MAX_MESSAGE_LEN:
        raise ValidationError(f"Message exceeds {Config.MAX_MESSAGE_LEN} characters.")
    # Strip dangerous HTML characters
    sanitised = SAFE_TEXT_RE.sub("", message)
    return sanitised


def validate_signature(signature_b64: str) -> str:
    """Validate a base64-encoded RSA signature — returns the string back."""
    if not signature_b64 or not isinstance(signature_b64, str):
        raise ValidationError("Signature is required.")
    try:
        import base64
        sig_bytes = base64.b64decode(signature_b64.strip())
    except Exception:
        raise ValidationError("Signature is not valid base64.")
    if len(sig_bytes) < 64:
        raise ValidationError("Signature is too short to be valid.")
    return signature_b64   # ← возвращаем строку, не bytes


def validate_hash(hash_str: str) -> str:
    """Validate a SHA-256 hex hash string."""
    if not hash_str or not isinstance(hash_str, str):
        raise ValidationError("Hash is required.")
    hash_str = hash_str.strip().lower()
    if not re.match(r"^[0-9a-f]{64}$", hash_str):
        raise ValidationError("Hash must be a 64-character hexadecimal string.")
    return hash_str
