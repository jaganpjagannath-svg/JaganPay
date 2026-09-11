# JaganPay — AI-Powered UPI Payment & Financial Automation Simulator

> **"Smart. Secure. Simple."**

![JaganPay Banner](static/images/logo.svg)

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask 3.x](https://img.shields.io/badge/Flask-3.x-black.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Simulation Status](https://img.shields.io/badge/Mode-100%25%20Offline%20Simulation-success.svg)](#important-safety-notice)
[![AI Engine](https://img.shields.io/badge/AI-Google%20GenAI%20Gemini%202.5-purple.svg)](https://ai.google.dev/)
[![Automation](https://img.shields.io/badge/Automation-n8n%20Webhooks-red.svg)](https://n8n.io/)

---

## ⚠️ Important Safety Notice

**JAGANPAY IS A SIMULATION / EDUCATIONAL DEMO ONLY.**
- **NO REAL MONEY** is transferred, stored, or processed.
- **DO NOT** connect to real UPI networks (NPCI), real bank accounts, or real payment gateways.
- All bank accounts (e.g. *Jagan Bank*, *Astra Bank*), balances (e.g. ₹25,000 demo credits), transactions, and risk scores are simulated variables created for software demonstration, college presentations, technical interviews, and portfolio display.

---

## 🌟 Executive Summary

**JaganPay** is a comprehensive, production-quality fintech application designed to demonstrate the end-to-end architecture of a modern digital payment ecosystem. It combines:
1. **Unified Payments Interface (UPI) Simulation**: Virtual payment addresses (`username@jaganpay`), dynamic scannable QR generation, atomic balance transfers, and digital receipt generation.
2. **Mandatory Multi-Factor OTP Security**: Salted SHA-256 OTP verification for account activation, sensitive transaction step-ups (≥ ₹10,000), and PIN resets.
3. **AI Financial Assistant ("JaganPay AI")**: Powered by the official Google GenAI Python SDK (`google-genai`), providing transaction categorization, spending analysis, and budgeting habits with robust offline heuristic fallback.
4. **Simulated Fraud & Risk Engine (0–100)**: Behavioral scoring of transaction velocity, amount thresholds, nocturnal timing, and recipient novelty.
5. **n8n Workflow Automation**: 8 modular webhook blueprints for registration welcome emails, payment receipts, failure alerts, high-risk escalation, and daily financial summaries.
6. **Role-Based Access Control (RBAC)**: Distinct dashboards for Users, Merchants, and System Administrators.

---

## 🏗️ System Architecture

```
                                    +-----------------------+
                                    |    Client Browsers    |
                                    |  (Desktop & Mobile)   |
                                    +-----------+-----------+
                                                |
                                                | HTTP / REST API
                                                v
+---------------------------------------------------------------------------------------+
|                               Flask Core Application Layer                            |
|                                                                                       |
|  +--------------------+   +----------------------+   +-----------------------------+  |
|  |   Auth & Guards    |   | Payment Simulation   |   | AI Copilot (Gemini GenAI)   |  |
|  |  (Salted SHA-256)  |   | (Atomic Balances)    |   | (Prompt Sanitizer/Fallback) |  |
|  +--------------------+   +----------------------+   +-----------------------------+  |
|                                                                                       |
|  +--------------------+   +----------------------+   +-----------------------------+  |
|  | Heuristic Risk     |   | Dynamic QR Engine    |   | Async Webhook Dispatcher    |  |
|  | Scoring (0 - 100)  |   | (NPCI UPI URI / PNG) |   | (Non-blocking Daemon Pool)  |  |
|  +--------------------+   +----------------------+   +-----------------------------+  |
+------------------------------------+--------------------------------+-----------------+
                                     |                                |
                        SQLAlchemy   v                   Webhooks     v
                       +-----------------------------+   +-----------------------------+
                       |    Database Persistence     |   |   n8n Automation Engine     |
                       |  PostgreSQL / Local SQLite  |   |     (8 Modular Workflows)   |
                       +-----------------------------+   +-----------------------------+
```

---

## 🛠️ Technology Stack

- **Backend Framework**: Python 3.13, Flask 3.x
- **Database / ORM**: SQLAlchemy with PostgreSQL support and automatic SQLite fallback
- **Authentication**: Flask-Login, Flask-Bcrypt (Blowfish password & PIN hashing), Salted SHA-256 for OTPs
- **Web Security**: Flask-WTF (CSRF tokens), Flask-Limiter (rate limiting), Strict CSP, X-Frame-Options, X-Content-Type-Options
- **AI Integration**: Official `google-genai` Python SDK (`from google import genai`) with smart offline heuristic fallback
- **Frontend**: HTML5, CSS3, Tailwind CSS, Bootstrap utilities, FontAwesome 6, Chart.js (Doughnut & Bar charts), QRCode generator
- **Automation**: n8n modular JSON workflows
- **Testing**: pytest suite covering authentication, payments, risk scoring, RBAC, and REST APIs
- **Deployment**: Gunicorn WSGI, Procfile, Render/Railway/Fly.io compatible

---

## 📂 Folder Structure

```
jaganpay/
├── app.py                      # Application entry point & WSGI runner
├── config.py                   # Environment configuration (Dev, Test, Prod)
├── requirements.txt            # Python dependencies
├── .env.example                # Sample environment configuration
├── .gitignore                  # Git ignore rules
├── Procfile                    # Web process for cloud deployment
├── runtime.txt                 # Python runtime version
├── pytest.ini                  # Pytest configuration
├── README.md                   # Complete documentation
│
├── app/
│   ├── __init__.py             # Flask app factory, blueprints & error handlers
│   ├── extensions.py           # db, bcrypt, login_manager, csrf, limiter
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py             # User, Role
│   │   ├── otp.py              # OTPVerification (salted SHA-256)
│   │   ├── bank_account.py     # DemoBankAccount, UPIProfile
│   │   ├── transaction.py      # Transaction, PaymentRequest
│   │   ├── merchant.py         # Merchant
│   │   ├── notification.py     # Notification
│   │   ├── security.py         # SecurityEvent, AuditLog, RiskAlert
│   │   ├── support.py          # SupportTicket, SupportMessage
│   │   └── ai_log.py           # AIInteraction audit trail
│   ├── routes/                 # Blueprint controllers
│   │   ├── main.py             # Landing page, health, about
│   │   ├── auth.py             # Register, verify-otp, login, logout
│   │   ├── dashboard.py        # User dashboard & cashflow overview
│   │   ├── payments.py         # Send, receive, request, QR pay
│   │   ├── transactions.py     # History, search, receipts
│   │   ├── analytics.py        # Financial charts & category analytics
│   │   ├── ai.py               # JaganPay AI chat endpoints
│   │   ├── security.py         # PIN update, password change, bank linking
│   │   ├── support.py          # Support ticketing & messaging
│   │   ├── merchant.py         # Merchant sales portal & refund simulation
│   │   ├── admin.py            # Admin console & system telemetry
│   │   └── api.py              # Complete JSON REST API
│   ├── services/               # Core business logic
│   │   ├── auth_service.py     # OTP generation, rate limit & verification
│   │   ├── payment_service.py  # Atomic transfers, reference generator
│   │   ├── risk_service.py     # Simulated risk evaluation (0-100)
│   │   ├── qr_service.py       # UPI URI builder & base64 QR renderer
│   │   ├── notification_service.py # In-app alert manager
│   │   ├── webhook_service.py  # Asynchronous, resilient n8n dispatcher
│   │   ├── audit_service.py    # Zero-secret audit logger
│   │   └── email_service.py    # SMTP email sender with console fallback
│   ├── ai/
│   │   ├── gemini_service.py   # Google GenAI SDK client & heuristic engine
│   │   └── templates.py        # Safety system prompts & financial templates
│   ├── middleware/
│   │   ├── auth_guard.py       # RBAC & verification decorators
│   │   └── security_headers.py # HSTS, CSP, and framing defense headers
│   └── utils/
│       ├── helpers.py          # Currency format (₹), masking, reference IDs
│       └── validators.py       # UPI ID, phone, and password strength checks
│
├── templates/                  # Jinja2 responsive templates
│   ├── base.html               # Master layout with dark mode toggle
│   ├── index.html              # High-converting landing page
│   ├── about.html              # System architecture & disclaimer
│   ├── auth/                   # Register, login, verify-otp
│   ├── dashboard/              # User dashboard
│   ├── payments/               # Send, receive, request, qr_pay, receipt
│   ├── transactions/           # History, detail
│   ├── analytics/              # Chart.js graphs & AI summaries
│   ├── ai/                     # JaganPay AI chat interface
│   ├── security/               # Security health & PIN change
│   ├── support/                # Tickets & threaded messaging
│   ├── merchant/               # Sales overview & counter QR standee
│   ├── admin/                  # Admin KPIs, users, ledger, triage, audit
│   └── errors/                 # 400, 401, 403, 404, 429, 500 error pages
│
├── static/
│   ├── css/style.css           # Glassmorphism, animations, dark/light themes
│   ├── js/main.js              # Theme manager, toasts, debounced search
│   └── images/logo.svg         # Brand vector logo
│
├── n8n/                        # 8 Production-ready n8n workflow blueprints
│   ├── registration.json       # 1. User registration automation
│   ├── otp.json                # 2. OTP notification pipeline
│   ├── payment-success.json    # 3. Payment success receipt dispatcher
│   ├── payment-failure.json    # 4. Failure diagnostics & alerts
│   ├── risk-alert.json         # 5. High-risk transaction escalation
│   ├── daily-summary.json      # 6. Scheduled 9 PM financial summary
│   ├── support.json            # 7. Support ticket triage & SLA routing
│   └── admin-report.json       # 8. Scheduled 8 AM health digest
│
├── scripts/
│   ├── seed_data.py            # Comprehensive test data generator
│   └── create_admin.py         # CLI admin provisioning script
│
└── tests/                      # Automated pytest suite
    ├── conftest.py             # Fixtures & in-memory DB configuration
    ├── test_auth.py            # Registration, OTP, login tests
    ├── test_payments.py        # Transfers, balance checks, risk scoring
    ├── test_security.py        # RBAC, audit sanitization tests
    ├── test_api.py             # REST API endpoint contracts
    └── test_ai.py              # Gemini SDK fallback & heuristic tests
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10 to 3.13 installed
- Git installed

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone https://github.com/your-username/jaganpay.git
cd jaganpay

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key settings:
- `SECRET_KEY`: Set to any secure random string.
- `DATABASE_URL`: Defaults to `sqlite:///jaganpay.db`. For PostgreSQL, set `postgresql://user:password@localhost:5432/jaganpay`.
- `GEMINI_API_KEY`: *(Optional)* Add your Gemini API key from [Google AI Studio](https://aistudio.google.com/). If left blank, the app uses its intelligent local heuristics engine so the AI assistant works 100% offline!
- `DEV_SHOW_TEST_OTP`: Set to `True` to show convenient one-click OTP auto-fill in development.

### 4. Seed Rich Demo Data
Populate demo users, merchants, transactions, and risk alerts:
```bash
python scripts/seed_data.py
```

### 5. Launch Application
```bash
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🔑 Pre-Seeded Demo Credentials

| Role | Email | Password | Demo PIN | Demo UPI ID | Starting Balance |
|---|---|---|---|---|---|
| **Admin** | `jagan@jaganpay.com` | `DemoPassword123!` | `1234` | `jagan@jaganpay` | ₹75,000.00 |
| **Demo User** | `demo@jaganpay.com` | `DemoPassword123!` | `1234` | `demo@jaganpay` | ₹25,000.00 |
| **Merchant** | `jagancafe@jaganpay.com` | `DemoPassword123!` | `1234` | `jagancafe@jaganpay` | ₹128,000.00 |

*Tip: The Sign In page contains convenient one-click quick-fill buttons for these accounts!*

---

## 🧪 Running Automated Tests

Run the complete test suite:
```bash
pytest -v
```

Tests verify:
- Registration and unverified state enforcement
- Salted SHA-256 OTP verification, expiry, and lockout after 3 failed attempts
- Atomic transfer balance deductions, insufficient funds handling, and self-transfer prevention
- Simulated Risk Engine calculations for high velocity and transactions > ₹50,000
- Role-based access control (RBAC) ensuring regular users cannot access `/admin`
- Sanitization of audit logs (redaction of passwords, PINs, OTPs)
- AI service fallback behavior without network access

---

## 🔄 n8n Webhook Automation Setup

JaganPay features 8 modular workflows designed for [n8n](https://n8n.io/):

1. **Start n8n**:
   ```bash
   npx n8n
   # Or run via Docker:
   docker run -it --rm --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n docker.n8n.io/n8nio/n8n
   ```
2. Open `http://localhost:5678`.
3. Go to **Workflows &rarr; Import from File**, and select any workflow from the `n8n/` folder:
   - `registration.json`
   - `otp.json`
   - `payment-success.json`
   - `payment-failure.json`
   - `risk-alert.json`
   - `daily-summary.json`
   - `support.json`
   - `admin-report.json`
4. Toggle each workflow to **Active**.
5. Test from JaganPay Admin Console: Navigate to **Admin Panel &rarr; n8n Webhooks** and click **Dispatch Test Webhook**.

> **Note on Fault Tolerance**: JaganPay dispatches webhooks asynchronously with a 3-second timeout in a background daemon thread. If n8n is offline or unreachable, transactions and user flows will **never** be blocked or delayed.

---

## ☁️ Cloud Deployment (Render / Railway / Heroku)

1. The project includes a production `Procfile`:
   ```Procfile
   web: gunicorn app:app
   ```
2. **Environment Variables for Production**:
   - `FLASK_ENV=production`
   - `SECRET_KEY=generate-a-strong-random-hex-key`
   - `DATABASE_URL=postgresql://user:pass@host:port/dbname`
   - `DEV_SHOW_TEST_OTP=False`
   - `GEMINI_API_KEY=your-gemini-key`
3. On **Render**:
   - Create **New Web Service**, connect repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`

---

## 🛡️ Cybersecurity & Architecture Highlights

- **Zero Plaintext Secrets**: Passwords and PINs are hashed using bcrypt. OTPs are stored with unique salts via SHA-256. Plaintext credentials are never logged or exposed in API payloads.
- **Sensitive Action Elevation**: Transfers exceeding ₹10,000 or PIN modifications trigger secondary OTP challenges.
- **Sanitized Audit Trail**: Central logger strips all sensitive keys (`password`, `pin`, `otp`, `secret`, `cvv`) before persisting to database.
- **Optimistic Concurrency**: Debit and credit operations execute inside atomic database transactions to eliminate race conditions.

---

## 📜 License & Disclaimers

Distributed under the MIT License.

**DISCLAIMER**: JaganPay is a portfolio project engineered for simulation and demonstration purposes only. It does not perform real-world financial transactions, connect to banking rails, or handle legal tender.
