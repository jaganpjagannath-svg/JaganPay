import os
import logging
from flask import current_app
from app.ai.templates import SYSTEM_INSTRUCTION, INSIGHT_PROMPT_TEMPLATE

logger = logging.getLogger("jaganpay.ai")


class GeminiAIService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Google GenAI client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize official GenAI client: {e}. Fallback active.")
                self.client = None

    def ask_ai(self, user_message: str, context_data: dict = None) -> str:
        """
        Interacts with Gemini API using Google GenAI SDK or falls back to
        smart simulated heuristic assistant when offline/unconfigured.
        """
        # Context enrichment
        context_str = ""
        if context_data:
            context_str = f"\n[User Simulated Context: Name: {context_data.get('name')}, Demo Balance: ₹{context_data.get('balance', 0):,.2f}, Total Spent: ₹{context_data.get('spent', 0):,.2f}, Top Category: {context_data.get('top_category', 'General')}]\n"

        prompt = f"{SYSTEM_INSTRUCTION}\n{context_str}\nUser Question: {user_message}"

        if self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.warning(f"GenAI API call failed ({e}). Reverting to simulated assistant response.")

        # Smart Heuristic Fallback Engine
        return self._generate_simulated_response(user_message, context_data)

    def generate_spending_insights(self, metrics: dict) -> str:
        """Generate structured financial summary and insights."""
        prompt = INSIGHT_PROMPT_TEMPLATE.format(
            total_spent=f"{metrics.get('total_spent', 0):,.2f}",
            total_received=f"{metrics.get('total_received', 0):,.2f}",
            net_flow=f"{metrics.get('net_flow', 0):,.2f}",
            top_category=metrics.get("top_category", "N/A"),
            category_breakdown=metrics.get("breakdown_text", "No categorized data"),
            txn_count=metrics.get("txn_count", 0),
        )

        if self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{SYSTEM_INSTRUCTION}\n{prompt}"
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.warning(f"GenAI insight generation failed ({e}). Reverting to simulated summary.")

        # Heuristic insight generator
        top = metrics.get("top_category", "General")
        spent = metrics.get("total_spent", 0)
        received = metrics.get("total_received", 0)
        return (
            f"### 💡 JaganPay AI Spending Summary\n\n"
            f"- **Top Spending Area**: **{top}** is currently your highest expenditure category.\n"
            f"- **Cashflow Ratio**: You've spent ₹{spent:,.2f} against ₹{received:,.2f} received in demo credits.\n"
            f"- **Optimization Tip**: Consider allocating a 50/30/20 simulated budget framework to keep discretionary expenses under 30%.\n"
            f"- **Automated Alerts**: Enable JaganPay n8n notifications to get daily transaction recaps.\n\n"
            f"> *ℹ️ AI-generated demo insight based on simulated transaction data.*"
        )

    def _generate_simulated_response(self, query: str, ctx: dict = None) -> str:
        """Local heuristic fallback when Gemini API key is absent or unreachable."""
        q = query.lower()
        ctx = ctx or {}
        name = ctx.get("name", "User")
        balance = ctx.get("balance", 25000.0)
        spent = ctx.get("spent", 0.0)
        top_cat = ctx.get("top_category", "General")

        if any(w in q for w in ["spend", "spent", "how much", "expense"]):
            return (
                f"Hello {name}! Based on your JaganPay demo transactions, your simulated total spending "
                f"is **₹{spent:,.2f}**. Your top spending category is **{top_cat}**.\n\n"
                f"💡 *Budgeting Habit*: Reviewing your transactions weekly helps identify non-essential expenses.\n\n"
                f"*ℹ️ Demo AI insight: JaganPay operates in demo mode using simulated transactions.*"
            )
        elif any(w in q for w in ["balance", "money", "funds"]):
            return (
                f"Your total simulated demo balance across all linked demo bank accounts is **₹{balance:,.2f}**.\n\n"
                f"You can use this demo balance to test sending money, paying merchants, or scanning demo QR codes.\n\n"
                f"*ℹ️ Demo AI insight: This is a simulated balance with no real monetary value.*"
            )
        elif any(w in q for w in ["what is upi", "upi", "how does upi work"]):
            return (
                f"**Unified Payments Interface (UPI)** is an instant real-time payment system developed in India by NPCI. "
                f"It allows multiple bank accounts to be merged into a single mobile application, merging several banking features, "
                f"seamless fund routing, and merchant payments into one hood using virtual IDs (e.g. `username@jaganpay`).\n\n"
                f"*ℹ️ Demo AI insight: JaganPay simulates this workflow completely offline for educational training.*"
            )
        elif any(w in q for w in ["fraud", "risk", "security"]):
            return (
                f"JaganPay uses an educational **Simulated Risk Engine** that scores transactions from 0 to 100 based on "
                f"factors like transaction velocity, unusual amounts, and new recipients. Scores above 65 are flagged as HIGH risk "
                f"for simulated administrative review.\n\n"
                f"*ℹ️ Demo AI insight: JaganPay's risk engine is an educational demonstration.*"
            )
        elif any(w in q for w in ["budget", "save", "saving", "tip"]):
            return (
                f"Here are 3 smart budgeting principles you can practice with JaganPay demo workflows:\n"
                f"1. **The 50/30/20 Rule**: Allocate 50% to needs, 30% to wants, and 20% to simulated savings.\n"
                f"2. **Monitor Velocity**: Avoid making multiple rapid impulse transfers.\n"
                f"3. **Categorize Expenses**: Keep track of Food and Shopping spikes using the Analytics tab.\n\n"
                f"*ℹ️ Demo AI insight: Educational guidance only; not regulated financial advice.*"
            )
        else:
            return (
                f"Hello {name}! I am **JaganPay AI**, your simulated financial organizer.\n\n"
                f"I can help you analyze your simulated spending (currently ₹{spent:,.2f}), inspect category trends, "
                f"explain payment mechanisms like UPI and QR protocols, or summarize your transaction history.\n\n"
                f"How can I assist your financial simulation today?\n\n"
                f"*ℹ️ Demo AI insight: JaganPay operates in demo mode using simulated transactions.*"
            )


# Global singleton instance
ai_service = GeminiAIService()
