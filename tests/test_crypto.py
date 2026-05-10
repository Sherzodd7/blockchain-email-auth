# tests/test_crypto.py
"""
Unit tests for the cryptographic layer (RSA + SHA-256).
Run with:  python -m pytest tests/test_crypto.py -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import base64
import pytest

from app.crypto.rsa_crypto import (
    generate_keys,
    hash_message,
    sign_message,
    verify_signature,
    get_public_key_pem,
)


# ─── Hash tests ───────────────────────────────────────────────────────────────

class TestHashMessage:
    def test_returns_64_char_hex(self):
        h = hash_message("hello")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        assert hash_message("test") == hash_message("test")

    def test_different_inputs_different_hashes(self):
        assert hash_message("abc") != hash_message("ABC")

    def test_empty_string(self):
        # SHA-256 of "" is a well-known value
        h = hash_message("")
        assert h == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_known_value(self):
        # SHA-256("The quick brown fox jumps over the lazy dog")
        expected = "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592"
        assert hash_message("The quick brown fox jumps over the lazy dog") == expected


# ─── Sign / Verify tests ──────────────────────────────────────────────────────

class TestSignVerify:
    def test_sign_returns_base64(self):
        sig = sign_message("hello world")
        decoded = base64.b64decode(sig)
        assert len(decoded) == 256   # RSA-2048 signature is 256 bytes

    def test_verify_valid_signature(self):
        msg = "Blockchain email authentication test"
        sig = sign_message(msg)
        assert verify_signature(msg, sig) is True

    def test_verify_wrong_message(self):
        sig = sign_message("original message")
        assert verify_signature("tampered message", sig) is False

    def test_verify_corrupted_signature(self):
        msg = "integrity check"
        sig = sign_message(msg)
        # Flip a few bytes
        raw     = base64.b64decode(sig)
        corrupt = bytearray(raw)
        corrupt[10] ^= 0xFF
        bad_sig = base64.b64encode(bytes(corrupt)).decode()
        assert verify_signature(msg, bad_sig) is False

    def test_verify_empty_signature_raises_or_returns_false(self):
        result = verify_signature("hello", "")
        assert result is False

    def test_verify_with_custom_public_key(self):
        pub = get_public_key_pem()
        msg = "custom key verification"
        sig = sign_message(msg)
        assert verify_signature(msg, sig, public_key_pem=pub) is True


# ─── Key generation ───────────────────────────────────────────────────────────

class TestKeyGeneration:
    def test_generate_keys_returns_pem_strings(self, tmp_path, monkeypatch):
        """generate_keys should write valid PEM files."""
        from config import Config
        monkeypatch.setattr(Config, "KEYS_DIR",          str(tmp_path))
        monkeypatch.setattr(Config, "PRIVATE_KEY_PATH",  str(tmp_path / "priv.pem"))
        monkeypatch.setattr(Config, "PUBLIC_KEY_PATH",   str(tmp_path / "pub.pem"))

        priv, pub = generate_keys()
        assert "BEGIN RSA PRIVATE KEY" in priv or "BEGIN PRIVATE KEY" in priv
        assert "BEGIN PUBLIC KEY" in pub
        