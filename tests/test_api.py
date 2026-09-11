def test_health_check_api(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "UP"
    assert data["real_financial_transactions"] is False


def test_qr_parse_api(client):
    res = client.post("/api/payments/qr", json={
        "payload": "upi://pay?pa=jagancafe@jaganpay&pn=JaganCafe&am=180.00&tn=Coffee"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["upi_id"] == "jagancafe@jaganpay"
    assert data["data"]["amount"] == 180.00
