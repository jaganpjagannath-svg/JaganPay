import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import create_app

env_name = os.environ.get("FLASK_ENV", "development")
app = create_app(env_name)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
    print(f"[*] JaganPay Payment Simulation Server running at http://127.0.0.1:{port}")
    print("[!] DEMO SIMULATOR MODE ACTIVE -- NO REAL FINANCIAL TRANSACTIONS")
    app.run(host="0.0.0.0", port=port, debug=debug)
