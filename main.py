import threading
import os
from flask import Flask, jsonify, render_template_string
from bot import run_bot, get_status

# ===== FLASK APP =====
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Status Bot Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a2e;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        .status-dot {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        .status-dot.online { background: #43b581; box-shadow: 0 0 10px #43b581; }
        .status-dot.offline { background: #747f8d; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p { color: #a0a0b0; margin-top: 0.5rem; }
        .badge {
            display: inline-flex;
            align-items: center;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 999px;
            padding: 6px 16px;
            margin-top: 1rem;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Status Bot</h1>
        <p>Discord presence tracking bot is running.</p>
        <div class="badge">
            <span class="status-dot {{ 'online' if status == 'running' else 'offline' }}"></span>
            {{ status | capitalize }}
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    status = get_status()
    return render_template_string(DASHBOARD_HTML, status=status)

@app.route("/health")
def health():
    return jsonify({"status": get_status(), "ok": True})

# ===== START BOT IN BACKGROUND =====
# Starts at import time so it works with both:
#   - `python main.py`  (development)
#   - `gunicorn main:app` (production / Railway)
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

# ===== LOCAL DEV =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
