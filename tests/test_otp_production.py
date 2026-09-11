import io
import sys
from datetime import datetime, timedelta
from app.extensions import db
from app.models.user import User, Role
from app.models.otp import OTPChallenge, OTPPurpose, OTPChannel
from app.services.otp_service import OTPService, MockSMSProvider, RealSMSProvider, get_sms_provider


def test_send_otp_api_contract_zero_leakage(client):
    """Verify /api/auth/send-otp follows exact specification and NEVER leaks OTP."""
    res = client.post("/api/auth/send-otp", json={
        "identifier": "+919876543210",
        "channel": "SMS",
        "purpose": "REGISTRATION"
    })
    assert res.status_code == 200
    data = res.get_json()

    # Exact required contract
    assert data["success"] is True
    assert data["message"] == "OTP sent successfully"
    assert data["otp_required"] is True
    assert data["expires_in"] == 300

    # ZERO LEAKAGE ASSERTIONS
    assert "otp" not in data
    assert "code" not in data
    assert "raw_otp" not in data
    assert "demo_otp_helper" not in data
    assert "Set-Cookie" not in res.headers or "otp" not in res.headers.get("Set-Cookie", "")


def test_verify_otp_api_contract(client, monkeypatch):
    """Verify /api/auth/verify-otp endpoint accepts identifier and 6-digit code."""
    monkeypatch.setattr(OTPService, "generate_otp", lambda: "888999")

    # 1. Send OTP
    send_res = client.post("/api/auth/send-otp", json={
        "identifier": "+919111222333",
        "channel": "SMS",
        "purpose": "LOGIN"
    })
    assert send_res.status_code == 200

    # 2. Verify with correct code
    verify_res = client.post("/api/auth/verify-otp", json={
        "identifier": "+919111222333",
        "otp": "888999",
        "purpose": "LOGIN"
    })
    assert verify_res.status_code == 200
    v_data = verify_res.get_json()
    assert v_data["success"] is True
    assert v_data["message"] == "OTP verified successfully"

    # 3. Verify that re-using the same code fails (already verified)
    reuse_res = client.post("/api/auth/verify-otp", json={
        "identifier": "+919111222333",
        "otp": "888999",
        "purpose": "LOGIN"
    })
    assert reuse_res.status_code == 400
    assert reuse_res.get_json()["success"] is False


def test_resend_otp_rate_limiting_and_invalidation(client, app, monkeypatch):
    """Test that resending within cooldown is rejected (429) and allowed after cooldown."""
    monkeypatch.setattr(OTPService, "generate_otp", lambda: "555666")

    # First request
    res1 = client.post("/api/auth/send-otp", json={
        "identifier": "+919999888877",
        "channel": "SMS"
    })
    assert res1.status_code == 200

    # Immediate resend (should trigger 429 cooldown active)
    res_immediate = client.post("/api/auth/resend-otp", json={
        "identifier": "+919999888877"
    })
    assert res_immediate.status_code == 429
    data_rate = res_immediate.get_json()
    assert data_rate["success"] is False
    assert "COOLDOWN_ACTIVE" == data_rate["error_code"]
    assert "wait" in data_rate["message"].lower()

    # Fast-forward cooldown by updating resend_available_at in database
    with app.app_context():
        challenge = OTPChallenge.query.filter_by(identifier="+919999888877").first()
        challenge.resend_available_at = datetime.utcnow() - timedelta(seconds=5)
        db.session.commit()

    # Second resend should now succeed
    monkeypatch.setattr(OTPService, "generate_otp", lambda: "777888")
    res_after = client.post("/api/auth/resend-otp", json={
        "identifier": "+919999888877"
    })
    assert res_after.status_code == 200
    data_after = res_after.get_json()
    assert data_after["success"] is True
    assert data_after["message"] == "New OTP sent"
    assert data_after["expires_in"] == 300
    assert "otp" not in data_after

    # Verify that the old challenge code '555666' was invalidated
    v_old = client.post("/api/auth/verify-otp", json={
        "identifier": "+919999888877",
        "otp": "555666"
    })
    assert v_old.status_code == 400


def test_database_stores_only_salted_hash(app):
    """Verify that plaintext OTP never enters the database."""
    with app.app_context():
        challenge, _ = OTPService.create_challenge(
            identifier="+919222333444",
            channel=OTPChannel.SMS,
            purpose=OTPPurpose.REGISTRATION
        )
        db_record = OTPChallenge.query.get(challenge.id)

        # Confirm otp_hash is 64 hex characters (SHA-256)
        assert len(db_record.otp_hash) == 64
        assert len(db_record.salt) == 32
        # Ensure there is no column named raw_otp or otp
        assert not hasattr(db_record, "raw_otp")
        assert not hasattr(db_record, "otp")


def test_five_wrong_attempts_lockout(app, monkeypatch):
    """Ensure max 5 failed attempts locks and invalidates the challenge."""
    monkeypatch.setattr(OTPService, "generate_otp", lambda: "112233")

    with app.app_context():
        challenge, _ = OTPService.create_challenge(
            identifier="+919444555666",
            channel=OTPChannel.SMS,
            purpose=OTPPurpose.LOGIN
        )

        # 4 wrong attempts
        for attempt in range(4):
            ok, msg, _ = OTPService.verify_challenge(
                raw_code="000000",
                identifier="+919444555666",
                purpose=OTPPurpose.LOGIN
            )
            assert ok is False
            assert f"{4 - attempt} attempt(s) remaining" in msg

        # 5th wrong attempt triggers lockout
        ok5, msg5, _ = OTPService.verify_challenge(
            raw_code="000000",
            identifier="+919444555666",
            purpose=OTPPurpose.LOGIN
        )
        assert ok5 is False
        assert "locked" in msg5.lower() or "maximum attempts exceeded" in msg5.lower()

        # Check DB challenge is invalidated
        db.session.refresh(challenge)
        assert challenge.is_invalidated is True

        # Even with correct code now, attempt must fail
        ok_after, _, _ = OTPService.verify_challenge(
            raw_code="112233",
            identifier="+919444555666",
            purpose=OTPPurpose.LOGIN
        )
        assert ok_after is False


def test_mock_provider_prints_to_terminal(capsys):
    """Verify MockSMSProvider outputs terminal log with [DEV OTP PROVIDER]."""
    provider = MockSMSProvider()
    provider.send_sms("+919876543210", "Test message", raw_otp="123456")
    captured = capsys.readouterr()
    assert "[DEV OTP PROVIDER]" in captured.out
    assert "Recipient: +919876543210" in captured.out
    assert "OTP Code: 123456" in captured.out
    assert "Channel: SMS" in captured.out
