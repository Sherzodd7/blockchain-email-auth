# tests/test_api.py
"""
Integration tests for Flask API endpoints.
Uses Flask test client (no real Ganache needed — mock mode).

Run with:  python -m pytest tests/test_api.py -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import pytest

from app          import create_app
from config       import Config


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """Create a test Flask client with an isolated temp database."""
    tmp = tmp_path_factory.mktemp("testdb")
    Config.DB_PATH = str(tmp / "test.db")
    app = create_app(Config)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ─── Health ───────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.get_json()
    assert d["status"] == "ok"
    assert "blockchain" in d


# ─── Send ─────────────────────────────────────────────────────────────────────

class TestSendEndpoint:
    def test_send_valid(self, client):
        r = client.post("/api/send", json={
            "email":   "test@example.com",
            "message": "Hello blockchain world!",
        })
        assert r.status_code == 200
        d = r.get_json()
        assert d["success"] is True
        assert "hash" in d
        assert "signature" in d
        assert "tx_hash" in d
        assert len(d["hash"]) == 64

    def test_send_missing_email(self, client):
        r = client.post("/api/send", json={"message": "no email"})
        assert r.status_code == 400
        assert r.get_json()["success"] is False

    def test_send_missing_message(self, client):
        r = client.post("/api/send", json={"email": "user@test.com"})
        assert r.status_code == 400

    def test_send_invalid_email(self, client):
        r = client.post("/api/send", json={"email": "not-an-email", "message": "hi"})
        assert r.status_code == 400

    def test_send_empty_message(self, client):
        r = client.post("/api/send", json={"email": "x@x.com", "message": "   "})
        assert r.status_code == 400

    def test_send_phishing_message(self, client):
        r = client.post("/api/send", json={
            "email"  : "spammer@evil.com",
            "message": "Verify your account immediately — click here to confirm your password",
        })
        assert r.status_code == 200
        d = r.get_json()
        assert d["security"]["is_phishing"] is True


# ─── Verify ───────────────────────────────────────────────────────────────────

class TestVerifyEndpoint:
    def _get_sig(self, client, message):
        r = client.post("/api/send", json={
            "email": "verifier@test.com", "message": message,
        })
        return r.get_json()["signature"]

    def test_verify_valid(self, client):
        msg = "This message is authentic"
        sig = self._get_sig(client, msg)
        r   = client.post("/api/verify", json={"message": msg, "signature": sig})
        assert r.status_code == 200
        d = r.get_json()
        assert d["result"] in ("VALID", "TAMPERED")   # depends on Ganache availability
        assert d["sig_valid"] is True

    def test_verify_wrong_message(self, client):
        msg = "original"
        sig = self._get_sig(client, msg)
        r   = client.post("/api/verify", json={"message": "tampered", "signature": sig})
        d   = r.get_json()
        assert d["result"] == "INVALID"
        assert d["sig_valid"] is False

    def test_verify_missing_signature(self, client):
        r = client.post("/api/verify", json={"message": "hello"})
        assert r.status_code == 400

    def test_verify_no_body(self, client):
        r = client.post("/api/verify", content_type="application/json", data="")
        assert r.status_code == 400


# ─── Messages / Dashboard ─────────────────────────────────────────────────────

class TestDashboard:
    def test_messages_endpoint(self, client):
        r = client.get("/api/messages")
        assert r.status_code == 200
        d = r.get_json()
        assert d["success"] is True
        assert "messages" in d
        assert "stats" in d

    def test_stats_endpoint(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        d = r.get_json()
        assert "stats" in d
        assert "total" in d["stats"]

    def test_public_key_endpoint(self, client):
        r = client.get("/api/public-key")
        assert r.status_code == 200
        d = r.get_json()
        assert "PUBLIC KEY" in d["public_key"]
        