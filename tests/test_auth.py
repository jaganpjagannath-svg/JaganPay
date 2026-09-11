from app.extensions import db
from app.models.user import User
from app.models.otp import OTPPurpose
from app.services.auth_service import request_otp, verify_user_otp
from app.services.otp_service import OTPService


def test_registration_flow(client):
    res = client.post("/api/auth/register", json={
        "full_name": "Newbie Tester",
        "email": "newbie@jaganpay.com",
        "phone": "+919888888888",
        "password": "Password123!"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "user_id" in data["data"]

    # Assert ZERO OTP leakage
    assert "demo_otp_helper" not in data.get("data", {})
    assert "otp" not in data
    assert "otp" not in data.get("data", {})

    # Verify user created with is_verified=False
    user = User.query.filter_by(email="newbie@jaganpay.com").first()
    assert user is not None
    assert user.is_verified is False
    assert user.total_demo_balance == 25000.0


def test_correct_otp_verification(app, monkeypatch):
    # Fix the generated OTP to test verification deterministically
    monkeypatch.setattr(OTPService, "generate_otp", lambda: "123456")

    with app.app_context():
        user = User(
            full_name="OTP Candidate",
            email="candidate@jaganpay.com",
            phone="+919777777777",
            password_hash="fakehash",
            is_verified=False,
        )
        db.session.add(user)
        db.session.commit()

        success, msg, dev_otp = request_otp(user, purpose=OTPPurpose.REGISTRATION)
        assert success is True
        # Plaintext OTP is NEVER returned to callers
        assert dev_otp is None

        # Verify with correct code
        v_success, v_msg = verify_user_otp(user, "123456", purpose=OTPPurpose.REGISTRATION)
        assert v_success is True
        assert user.is_verified is True


def test_wrong_otp_and_max_attempts(app, monkeypatch):
    monkeypatch.setattr(OTPService, "generate_otp", lambda: "654321")

    with app.app_context():
        user = User(
            full_name="Brute Attacker",
            email="brute@jaganpay.com",
            phone="+919666666666",
            password_hash="fakehash",
            is_verified=False,
        )
        db.session.add(user)
        db.session.commit()

        success, msg, dev_otp = request_otp(user, purpose=OTPPurpose.REGISTRATION)
        assert dev_otp is None

        # 5 consecutive wrong attempts
        for i in range(5):
            ok, _ = verify_user_otp(user, f"00000{i}")
            assert ok is False

        # Attempt 6 (even if code is correct now, max attempts lockout blocks it)
        ok, lockout_msg = verify_user_otp(user, "654321")
        assert ok is False
        assert "exceeded" in lockout_msg.lower() or "invalidated" in lockout_msg.lower()


def test_login_api(client, test_user):
    # Correct password
    res = client.post("/api/auth/login", json={
        "identifier": "tester@jaganpay.com",
        "password": "TestPass123!"
    })
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    # Incorrect password
    res_bad = client.post("/api/auth/login", json={
        "identifier": "tester@jaganpay.com",
        "password": "WrongPassword!"
    })
    assert res_bad.status_code == 401
    assert res_bad.get_json()["success"] is False
