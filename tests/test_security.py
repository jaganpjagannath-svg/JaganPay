from app.services.audit_service import sanitize_dict


def test_audit_log_redaction():
    payload = {
        "user_email": "demo@jaganpay.com",
        "password": "SuperSecretPassword!",
        "confirm_password": "SuperSecretPassword!",
        "demo_pin": "1234",
        "otp": "654321",
        "amount": 500.0,
    }
    cleaned = sanitize_dict(payload)
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["confirm_password"] == "[REDACTED]"
    assert cleaned["demo_pin"] == "[REDACTED]"
    assert cleaned["otp"] == "[REDACTED]"
    assert cleaned["amount"] == 500.0
    assert cleaned["user_email"] == "demo@jaganpay.com"


def test_rbac_admin_restriction(client, test_user, test_admin):
    # 1. Unauthenticated -> redirect to login
    res = client.get("/admin/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

    # 2. Authenticated as regular USER -> redirected to /dashboard
    login_user_res = client.post("/api/auth/login", json={
        "identifier": "tester@jaganpay.com",
        "password": "TestPass123!"
    })
    assert login_user_res.status_code == 200

    res_user = client.get("/admin/")
    assert res_user.status_code == 302
    assert "/dashboard" in res_user.headers["Location"]

    # 3. Logout
    client.post("/api/auth/logout")

    # 4. Authenticated as ADMIN -> 200 OK
    login_admin_res = client.post("/api/auth/login", json={
        "identifier": "admin@jaganpay.com",
        "password": "AdminPass123!"
    })
    assert login_admin_res.status_code == 200

    res_admin = client.get("/admin/")
    assert res_admin.status_code == 200
