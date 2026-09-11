import os
from app import create_app

# Root entrypoint for servers configured with `gunicorn main:app`
env = os.environ.get("FLASK_ENV", "production")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
