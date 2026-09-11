from datetime import datetime
from app.extensions import db


class AIInteraction(db.Model):
    __tablename__ = "ai_interactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_summary = db.Column(db.String(255), nullable=False)
    response_snippet = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(50), default="gemini-2.5-flash")
    tokens_approx = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "prompt_summary": self.prompt_summary,
            "response_snippet": self.response_snippet,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
