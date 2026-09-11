from app.ai.gemini_service import GeminiAIService


def test_ai_fallback_heuristics():
    # Instantiate without API key to ensure 100% reliable offline fallback
    svc = GeminiAIService(api_key="")
    assert svc.client is None

    # Test spending question
    ctx = {"name": "Jagan", "balance": 25000.0, "spent": 1250.0, "top_category": "Food"}
    reply = svc.ask_ai("How much did I spend this month?", ctx)
    assert "₹1,250.00" in reply
    assert "Demo AI insight" in reply

    # Test UPI explanation question
    upi_reply = svc.ask_ai("What is UPI?")
    assert "Unified Payments Interface" in upi_reply


def test_ai_spending_insights_generation():
    svc = GeminiAIService(api_key="")
    metrics = {
        "total_spent": 8450.0,
        "total_received": 15000.0,
        "net_flow": 6550.0,
        "top_category": "Food & Dining",
        "txn_count": 5
    }
    insight = svc.generate_spending_insights(metrics)
    assert "Food & Dining" in insight
    assert "AI Spending Summary" in insight
