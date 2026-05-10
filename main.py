#!/usr/bin/env python3
# main.py — Entry point for the Blockchain Email Auth system
"""
Usage:
    python main.py             # start server (default: http://0.0.0.0:5000)
    python main.py --demo      # run a quick CLI demo without the web server
    python main.py --test      # run unit tests
"""
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from app           import create_app
from config        import Config
from app.utils.logger import log


def run_server():
    """Start the Flask development server."""
    app = create_app(Config)
    log.info("=" * 60)
    log.info("  🔐 Blockchain Email Authentication System")
    log.info("  URL  : http://%s:%d", Config.HOST, Config.PORT)
    log.info("  Debug: %s", Config.DEBUG)
    log.info("  DB   : %s", Config.DB_PATH)
    log.info("  Chain: %s", Config.GANACHE_URL)
    log.info("=" * 60)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)


def run_demo():
    """
    CLI demonstration: send + verify a message without the web UI.
    Useful for smoke-testing all layers.
    """
    from app.services import send_secure_message, verify_message

    print("\n" + "=" * 60)
    print("  BLOCKCHAIN EMAIL AUTH — CLI DEMO")
    print("=" * 60)

    # ── 1. Send a legitimate message ──────────────────────────────────────
    print("\n[1] Sending a secure message…")
    result = send_secure_message(
        email   = "alice@example.com",
        message = "Hello Bob! This is a blockchain-authenticated message.",
    )
    print(f"    ✅ Message ID  : {result['message_id']}")
    print(f"    🔑 Hash        : {result['hash'][:32]}…")
    print(f"    ⛓  TX Hash     : {result['tx_hash'][:32]}…")
    print(f"    🛡  Trust Score : {result['trust_score']}/100")
    print(f"    🔒 Status      : {result['status']}")

    signature = result["signature"]
    message   = "Hello Bob! This is a blockchain-authenticated message."

    # ── 2. Verify the original message ────────────────────────────────────
    print("\n[2] Verifying the original message…")
    v = verify_message(message, signature)
    print(f"    Result     : {v['result']}")
    print(f"    Sig valid  : {v['sig_valid']}")
    print(f"    On-chain   : {v['hash_on_chain']}")

    # ── 3. Attempt to verify tampered message ─────────────────────────────
    print("\n[3] Verifying a TAMPERED message…")
    vt = verify_message("Hello Bob! This message was CHANGED.", signature)
    print(f"    Result     : {vt['result']}  (expected: INVALID)")

    # ── 4. Phishing demo ──────────────────────────────────────────────────
    print("\n[4] Sending a PHISHING message…")
    pr = send_secure_message(
        email   = "spammer@evil.com",
        message = "URGENT: Verify your account immediately — confirm your password NOW!",
    )
    print(f"    Is Phishing : {pr['security']['is_phishing']}")
    print(f"    Risk Level  : {pr['security']['risk_level']}")
    print(f"    Flags       : {pr['security']['flags']}")

    print("\n" + "=" * 60)
    print("  Demo complete. Open http://localhost:5000 for the web UI.")
    print("=" * 60 + "\n")


def run_tests():
    """Run the test suite via pytest."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=os.path.dirname(__file__),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        # Bootstrap DB + keys before demo
        from app.database import init_db
        from app.crypto   import generate_keys
        import os
        os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
        init_db()
        if not os.path.exists(Config.PRIVATE_KEY_PATH):
            generate_keys()
        run_demo()
    elif "--test" in sys.argv:
        run_tests()
    else:
        run_server()
        