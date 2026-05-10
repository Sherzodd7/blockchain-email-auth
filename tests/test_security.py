# tests/test_security.py
"""
Unit tests for phishing detection and trust score.
Run with:  python -m pytest tests/test_security.py -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from app.services.security_service import detect_phishing, compute_trust_score


class TestPhishingDetection:
    def test_clean_message(self):
        r = detect_phishing("Hello, how are you doing today?", "user@example.com")
        assert r["is_phishing"] is False
        assert r["risk_level"] == "low"

    def test_keyword_phishing(self):
        r = detect_phishing("Please verify your account and confirm your password immediately.", "hacker@evil.com")
        assert r["is_phishing"] is True
        assert len(r["flags"]) > 0

    def test_urgency_language(self):
        r = detect_phishing("ACT NOW! This offer EXPIRES TODAY! LAST CHANCE!", "")
        # should flag urgency + caps
        assert r["confidence"] > 0.2

    def test_suspicious_url(self):
        r = detect_phishing("Click this link: http://phishing.xyz/steal", "")
        assert r["confidence"] > 0.0
        assert any("URL" in f for f in r["flags"])

    def test_risk_level_high(self):
        msg = " ".join([
            "verify your account", "click here immediately",
            "confirm your password", "urgent action required",
        ])
        r = detect_phishing(msg, "")
        assert r["risk_level"] == "high"

    def test_returns_all_fields(self):
        r = detect_phishing("test message", "x@x.com")
        assert "is_phishing"  in r
        assert "confidence"   in r
        assert "flags"        in r
        assert "risk_level"   in r


class TestTrustScore:
    def test_new_sender_gets_50(self):
        score = compute_trust_score("brand_new_user_xyz@example.com")
        assert score == 50

    def test_score_in_range(self):
        score = compute_trust_score("anyone@test.com")
        assert 0 <= score <= 100
        