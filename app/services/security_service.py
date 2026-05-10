# app/services/security_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Security analysis service:
#   • Phishing detection  (keyword-based + heuristic)
#   • Trust Score         (history-based, 0-100)
# ─────────────────────────────────────────────────────────────────────────────

import re
from config                       import Config
from app.utils.logger             import log
from app.database.db_handler      import (
    count_valid_messages_by_email,
    count_phishing_by_email,
    get_messages_by_email,
)


# ─── Phishing Detection ───────────────────────────────────────────────────────

# Additional heuristic patterns (URLs, suspicious structure)
_SUSPICIOUS_URL_RE = re.compile(
    r"(https?://\S+\.(ru|cn|xyz|tk|pw|cc|top)[/\s]|"
    r"bit\.ly|tinyurl|goo\.gl|t\.co/\w+)",
    re.IGNORECASE,
)
_URGENT_RE = re.compile(
    r"\b(immediately|urgent|act now|expires? (today|in \d+ hours?)|"
    r"last chance|final (warning|notice))\b",
    re.IGNORECASE,
)


def detect_phishing(message: str, email: str = "") -> dict:
    """
    Analyse a message for phishing indicators.

    Returns:
        {
          "is_phishing"  : bool,
          "confidence"   : float (0.0 – 1.0),
          "flags"        : list[str],   # human-readable reasons
          "risk_level"   : "low" | "medium" | "high"
        }
    """
    flags    : list[str] = []
    score    : float     = 0.0
    msg_lower            = message.lower()

    # 1. Keyword matching (config-driven, easy to extend)
    for kw in Config.PHISHING_KEYWORDS:
        if kw.lower() in msg_lower:
            flags.append(f"Phishing keyword detected: '{kw}'")
            score += 0.25

    # 2. Suspicious URL patterns
    if _SUSPICIOUS_URL_RE.search(message):
        flags.append("Suspicious URL or URL-shortener detected")
        score += 0.30

    # 3. Urgency language
    if _URGENT_RE.search(message):
        flags.append("Urgency/pressure language detected")
        score += 0.20

    # 4. All-caps ratio > 40%
    alpha = [c for c in message if c.isalpha()]
    if alpha and sum(1 for c in alpha if c.isupper()) / len(alpha) > 0.4:
        flags.append("Excessive use of capital letters")
        score += 0.15

    # 5. Sender history: if email has prior phishing flags, add penalty
    if email:
        prior_phishing = count_phishing_by_email(email)
        if prior_phishing > 0:
            flags.append(f"Sender has {prior_phishing} prior phishing flag(s)")
            score += min(0.3, prior_phishing * 0.1)

    score        = min(score, 1.0)
    is_phishing  = score >= 0.40

    if score < 0.25:
        risk_level = "low"
    elif score < 0.55:
        risk_level = "medium"
    else:
        risk_level = "high"

    if is_phishing:
        log.warning("⚠️  Phishing detected  email=%s  confidence=%.0f%%  flags=%s",
                    email, score * 100, flags)

    return {
        "is_phishing": is_phishing,
        "confidence" : round(score, 3),
        "flags"      : flags,
        "risk_level" : risk_level,
    }


# ─── Trust Score ──────────────────────────────────────────────────────────────

def compute_trust_score(email: str) -> int:
    """
    Compute a 0-100 trust score for a sender based on their message history.

    Algorithm:
        base_score = 50  (new sender)
        +3 per valid message (up to +40)
        -15 per phishing flag
        -5  per invalid/tampered message
        Clamped to [0, 100]
    """
    history  = get_messages_by_email(email)
    if not history:
        return 50   # neutral new sender

    base     = 50
    valid    = sum(1 for m in history if m["status"] == "valid")
    phishing = sum(1 for m in history if m["is_phishing"])
    bad      = sum(1 for m in history if m["status"] in ("invalid", "tampered"))

    score = base + min(valid * 3, 40) - (phishing * 15) - (bad * 5)
    score = max(0, min(100, score))

    log.debug("Trust score  email=%s  valid=%d  phishing=%d  bad=%d  score=%d",
              email, valid, phishing, bad, score)
    return score
