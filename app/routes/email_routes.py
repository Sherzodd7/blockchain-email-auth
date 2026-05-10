# app/routes/email_routes.py
# ─────────────────────────────────────────────────────────────────────────────
# Flask Blueprint for all email-auth endpoints:
#
#   POST /api/send          — sign + store message
#   POST /api/verify        — verify signature + blockchain
#   GET  /api/messages      — list all messages
#   GET  /api/stats         — dashboard statistics
#   GET  /api/public-key    — export current RSA public key
#   GET  /api/health        — liveness probe
# ─────────────────────────────────────────────────────────────────────────────

from flask             import Blueprint, request, jsonify, current_app

from app.services      import send_secure_message, verify_message, get_dashboard_data
from app.utils         import (validate_email, validate_message,
                                validate_signature, ValidationError)
from app.utils.logger  import log

bp = Blueprint("email", __name__, url_prefix="/api")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _err(msg: str, code: int = 400) -> tuple:
    log.warning("API error [%d]: %s", code, msg)
    return jsonify({"success": False, "error": msg}), code


def _ok(payload: dict) -> tuple:
    return jsonify({"success": True, **payload}), 200


# ─── POST /api/send ───────────────────────────────────────────────────────────

@bp.post("/send")
def send():
    """
    Send and cryptographically authenticate an email message.

    Request JSON:
        { "email": "user@example.com", "message": "Hello World" }

    Response JSON:
        {
          "success"    : true,
          "message_id" : 1,
          "hash"       : "abc123…",
          "signature"  : "base64…",
          "tx_hash"    : "0x…",
          "trust_score": 75,
          "security"   : { "is_phishing": false, … },
          "status"     : "valid"
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return _err("Request body must be valid JSON.")

    try:
        email   = validate_email(data.get("email", ""))
        message = validate_message(data.get("message", ""))
    except ValidationError as ve:
        return _err(str(ve))

    try:
        result = send_secure_message(email, message)
        log.info("POST /send  ✅  id=%s  email=%s", result.get("message_id"), email)
        return _ok(result)
    except Exception as exc:
        log.error("POST /send  ❌  %s", exc, exc_info=True)
        return _err(f"Internal server error: {exc}", 500)


# ─── POST /api/verify ─────────────────────────────────────────────────────────

@bp.post("/verify")
def verify():
    """
    Verify the authenticity of a message.

    Request JSON:
        { "message": "Hello World", "signature": "base64…" }

    Response JSON:
        {
          "success"      : true,
          "result"       : "VALID" | "INVALID" | "TAMPERED" | "NOT_FOUND",
          "sig_valid"    : true,
          "hash_on_chain": true,
          "details"      : "…"
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return _err("Request body must be valid JSON.")

    try:
        message   = validate_message(data.get("message", ""))
        signature = data.get("signature", "")
        if not signature:
            raise ValidationError("Signature is required.")
        validate_signature(signature)   # raises if invalid base64 / too short
    except ValidationError as ve:
        return _err(str(ve))

    try:
        result = verify_message(message, signature)
        log.info("POST /verify  result=%s", result.get("result"))
        return _ok(result)
    except Exception as exc:
        log.error("POST /verify  ❌  %s", exc, exc_info=True)
        return _err(f"Internal server error: {exc}", 500)


# ─── GET /api/messages ────────────────────────────────────────────────────────

@bp.get("/messages")
def messages():
    """
    Retrieve message history with optional pagination.
    Query params: ?limit=50&offset=0
    """
    try:
        limit  = min(int(request.args.get("limit",  50)), 200)
        offset = max(int(request.args.get("offset",  0)), 0)
    except ValueError:
        return _err("limit and offset must be integers.")

    try:
        data = get_dashboard_data(limit=limit)
        return _ok(data)
    except Exception as exc:
        log.error("GET /messages  ❌  %s", exc, exc_info=True)
        return _err(f"Internal server error: {exc}", 500)


# ─── GET /api/stats ───────────────────────────────────────────────────────────

@bp.get("/stats")
def stats():
    """Return aggregate statistics for the dashboard."""
    try:
        data = get_dashboard_data(limit=0)
        return _ok({
            "stats"              : data["stats"],
            "blockchain_connected": data["blockchain_connected"],
            "total_on_chain"     : data["total_on_chain"],
        })
    except Exception as exc:
        return _err(f"Internal server error: {exc}", 500)


# ─── GET /api/public-key ──────────────────────────────────────────────────────

@bp.get("/public-key")
def public_key():
    """Export the current RSA public key in PEM format."""
    from app.crypto import get_public_key_pem
    return _ok({"public_key": get_public_key_pem()})


# ─── GET /api/health ──────────────────────────────────────────────────────────

@bp.get("/health")
def health():
    """Liveness/readiness probe."""
    from app.blockchain import get_blockchain
    bc = get_blockchain()
    return jsonify({
        "status"     : "ok",
        "blockchain" : "connected" if bc.is_connected else "offline (mock mode)",
    }), 200
