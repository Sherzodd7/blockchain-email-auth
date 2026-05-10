# app/services/email_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Main orchestration service — ties together:
#   Crypto  →  Blockchain  →  Database  →  Security
#
# Public API:
#   send_secure_message(email, message) → dict
#   verify_message(message, signature)  → dict
#   get_dashboard_data()                → dict
# ─────────────────────────────────────────────────────────────────────────────

from app.crypto.rsa_crypto              import hash_message, sign_message, verify_signature, get_public_key_pem
from app.blockchain.web3_client         import get_blockchain
from app.database.db_handler            import (
    save_message, get_all_messages, get_message_by_hash,
    get_messages_by_email, get_stats, update_status,
)
from app.services.security_service      import detect_phishing, compute_trust_score
from app.utils.logger                   import log


# ─── Send ─────────────────────────────────────────────────────────────────────

def send_secure_message(email: str, message: str) -> dict:
    """
    Full send pipeline:
      1. Phishing scan
      2. Hash message (SHA-256)
      3. Sign hash (RSA)
      4. Store hash on blockchain
      5. Persist to database
      6. Compute sender trust score

    Returns structured result dict.
    """
    log.info("📨 send_secure_message  email=%s  msg_len=%d", email, len(message))

    # ── Step 1: Security scan ──────────────────────────────────────────────
    sec_result  = detect_phishing(message, email)
    trust_score = compute_trust_score(email)

    # ── Step 2: Cryptographic operations ──────────────────────────────────
    msg_hash    = hash_message(message)
    signature   = sign_message(message)
    log.debug("Hash=%s…  sig_len=%d chars", msg_hash[:16], len(signature))

    # ── Step 3: Blockchain storage ─────────────────────────────────────────
    bc          = get_blockchain()
    try:
        bc_result = bc.store_hash(msg_hash)
        tx_hash   = bc_result.get("tx_hash", "")
        bc_status = bc_result.get("status", "unknown")
    except Exception as exc:
        log.error("Blockchain store_hash failed: %s", exc)
        tx_hash  = ""
        bc_status = "error"

    # ── Step 4: Database persistence ───────────────────────────────────────
    db_status = "valid" if not sec_result["is_phishing"] else "phishing"
    row_id    = save_message(
        email       = email,
        message     = message,
        hash_str    = msg_hash,
        signature   = signature,
        tx_hash     = tx_hash,
        status      = db_status,
        trust_score = trust_score,
        is_phishing = sec_result["is_phishing"],
    )

    log.info("✅ Message sent  id=%d  tx=%s…  phishing=%s",
             row_id, tx_hash[:18] if tx_hash else "none", sec_result["is_phishing"])

    return {
        "success"         : True,
        "message_id"      : row_id,
        "hash"            : msg_hash,
        "signature"       : signature,
        "tx_hash"         : tx_hash,
        "blockchain_status": bc_status,
        "trust_score"     : trust_score,
        "security"        : sec_result,
        "status"          : db_status,
        "public_key"      : get_public_key_pem(),
    }


# ─── Verify ───────────────────────────────────────────────────────────────────

def verify_message(message: str, signature: str) -> dict:
    """
    Full verification pipeline:
      1. Recompute hash from plaintext
      2. Verify RSA signature
      3. Check hash existence on blockchain
      4. Cross-check with database record

    Possible outcomes:
        VALID    — signature OK + hash on-chain + DB record present
        INVALID  — signature fails
        TAMPERED — signature OK but hash not on-chain (message altered after signing)
        NOT_FOUND — no record in DB
    """
    log.info("🔍 verify_message  msg_len=%d", len(message))

    # ── Step 1: Signature verification ────────────────────────────────────
    sig_ok = verify_signature(message, signature)

    if not sig_ok:
        log.warning("Verification result: INVALID (bad signature)")
        return {
            "result"      : "INVALID",
            "sig_valid"   : False,
            "hash_on_chain": False,
            "details"     : "Digital signature verification failed. Message may be forged.",
        }

    # ── Step 2: Recompute hash ─────────────────────────────────────────────
    msg_hash = hash_message(message)

    # ── Step 3: Blockchain check ───────────────────────────────────────────
    bc        = get_blockchain()
    bc_result = bc.check_hash_exists(msg_hash)
    on_chain  = bc_result.get("exists", False)

    # ── Step 4: DB cross-check ─────────────────────────────────────────────
    db_record = get_message_by_hash(msg_hash)

    if sig_ok and on_chain:
        result  = "VALID"
        details = "Signature verified ✔  Hash confirmed on blockchain ✔  Record found in database ✔"
    elif sig_ok and not on_chain:
        result  = "TAMPERED"
        details = "Signature is mathematically valid BUT hash was not found on the blockchain. Message may have been tampered with after signing."
    else:
        result  = "NOT_FOUND"
        details = "No matching record found."

    log.info("Verification result: %s  hash=%s…  on_chain=%s", result, msg_hash[:16], on_chain)

    return {
        "result"         : result,
        "sig_valid"      : sig_ok,
        "hash"           : msg_hash,
        "hash_on_chain"  : on_chain,
        "blockchain_info": bc_result,
        "db_record"      : db_record,
        "details"        : details,
    }


# ─── Dashboard ────────────────────────────────────────────────────────────────

def get_dashboard_data(limit: int = 50) -> dict:
    """Aggregate data for the dashboard view."""
    messages = get_all_messages(limit=limit)
    stats    = get_stats()
    bc       = get_blockchain()

    return {
        "messages"          : messages,
        "stats"             : stats,
        "blockchain_connected": bc.is_connected,
        "total_on_chain"    : bc.get_total_hashes(),
        "public_key"        : get_public_key_pem(),
    }
