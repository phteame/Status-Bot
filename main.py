import threading
import os
import json
from flask import Flask, jsonify, render_template_string
from bot import run_bot, get_status, get_all_stats

# ===== FLASK APP =====
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Live Discord presence tracking dashboard displaying online durations, member statuses, and daily activity metrics.">
    <title>Status Bot Dashboard - {{ stats.guild_name }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.25);
            --online: #10b981;
            --online-glow: rgba(16, 185, 129, 0.25);
            --idle: #f59e0b;
            --idle-glow: rgba(245, 158, 11, 0.25);
            --dnd: #ef4444;
            --dnd-glow: rgba(239, 68, 68, 0.25);
            --offline: #64748b;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 10% 10%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
                radial-gradient(at 90% 90%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 1rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Top Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--card-border);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .bot-logo {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            box-shadow: 0 4px 20px var(--primary-glow);
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            font-size: 0.875rem;
            color: var(--text-muted);
        }

        .header-meta {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 9999px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--card-border);
            font-size: 0.875rem;
            font-weight: 500;
        }

        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }

        .status-dot.running { background-color: var(--online); box-shadow: 0 0 10px var(--online); }
        .status-dot.starting { background-color: var(--idle); box-shadow: 0 0 10px var(--idle); }
        .status-dot.error { background-color: var(--dnd); box-shadow: 0 0 10px var(--dnd); }

        .live-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--card-border);
            padding: 6px 12px;
            border-radius: 8px;
        }

        /* KPI Grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }

        .kpi-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .kpi-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-muted);
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
        }

        .kpi-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
        }

        .kpi-icon.members { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
        .kpi-icon.online { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .kpi-icon.idle { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
        .kpi-icon.time { background: rgba(168, 85, 247, 0.15); color: #c084fc; }

        .kpi-value {
            font-family: 'Outfit', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .kpi-sub {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }

        /* Metadata banner */
        .info-bar {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 0.875rem 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            font-size: 0.825rem;
            color: var(--text-muted);
            margin-bottom: 2rem;
        }

        .info-item strong {
            color: var(--text-main);
            font-weight: 600;
        }

        /* Controls / Search / Filter */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1.25rem;
        }

        .section-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            font-weight: 600;
        }

        .controls {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }

        .search-box {
            position: relative;
        }

        .search-box input {
            background: rgba(17, 24, 39, 0.9);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 8px 14px 8px 36px;
            color: var(--text-main);
            font-size: 0.875rem;
            outline: none;
            width: 220px;
            transition: border-color 0.2s ease, width 0.2s ease;
        }

        .search-box input:focus {
            border-color: var(--primary);
            width: 260px;
        }

        .search-box svg {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            width: 16px;
            height: 16px;
            fill: var(--text-muted);
        }

        .filter-btn {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 7px 12px;
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .filter-btn:hover, .filter-btn.active {
            background: rgba(99, 102, 241, 0.2);
            border-color: var(--primary);
            color: var(--text-main);
        }

        /* Members Table / Grid */
        .table-container {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            overflow: hidden;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.875rem;
        }

        th {
            background: rgba(255, 255, 255, 0.02);
            padding: 1rem 1.25rem;
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--card-border);
        }

        td {
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--card-border);
            vertical-align: middle;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .user-cell {
            display: flex;
            align-items: center;
            gap: 0.875rem;
        }

        .avatar {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: linear-gradient(135deg, #475569, #334155);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 0.9rem;
            color: #fff;
            object-fit: cover;
        }

        .user-names {
            display: flex;
            flex-direction: column;
        }

        .user-name {
            font-weight: 600;
            color: var(--text-main);
        }

        .user-handle {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .badge-status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: capitalize;
        }

        .badge-status.online { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid var(--online-glow); }
        .badge-status.idle { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid var(--idle-glow); }
        .badge-status.dnd { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid var(--dnd-glow); }
        .badge-status.offline { background: rgba(100, 116, 139, 0.15); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.05); }

        .time-pill {
            display: inline-block;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--card-border);
            padding: 4px 10px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .empty-state {
            padding: 3rem;
            text-align: center;
            color: var(--text-muted);
        }

        .empty-icon {
            font-size: 2.5rem;
            margin-bottom: 0.75rem;
        }

        footer {
            margin-top: 3rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        @media (max-width: 768px) {
            header { flex-direction: column; align-items: flex-start; }
            .search-box input { width: 100%; }
            .search-box input:focus { width: 100%; }
            th:nth-child(4), td:nth-child(4), th:nth-child(5), td:nth-child(5) { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="brand">
                <div class="bot-logo">🤖</div>
                <div>
                    <h1 id="guild-title">{{ stats.guild_name }}</h1>
                    <div class="subtitle">Discord Presence & Activity Dashboard</div>
                </div>
            </div>
            <div class="header-meta">
                <div class="status-badge">
                    <span class="status-dot {{ stats.bot_status }}" id="bot-status-dot"></span>
                    <span id="bot-status-text">Bot {{ stats.bot_status | capitalize }}</span>
                </div>
                <div class="live-pill">
                    <span>⚡ Live Auto-Refresh (5s)</span>
                </div>
            </div>
        </header>

        <!-- KPI Grid -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-header">
                    <span>Total Members</span>
                    <div class="kpi-icon members">👥</div>
                </div>
                <div class="kpi-value" id="kpi-total">{{ stats.total_members }}</div>
                <div class="kpi-sub">Tracked in Server</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-header">
                    <span>Online Now</span>
                    <div class="kpi-icon online">🟢</div>
                </div>
                <div class="kpi-value" id="kpi-online" style="color: #34d399;">{{ stats.online_count }}</div>
                <div class="kpi-sub">Active right now</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-header">
                    <span>Away / DnD</span>
                    <div class="kpi-icon idle">🌙</div>
                </div>
                <div class="kpi-value" id="kpi-away" style="color: #fbbf24;">{{ stats.idle_count + stats.dnd_count }}</div>
                <div class="kpi-sub"><span id="kpi-idle-sub">{{ stats.idle_count }}</span> Idle • <span id="kpi-dnd-sub">{{ stats.dnd_count }}</span> DND</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-header">
                    <span>Server Online Today</span>
                    <div class="kpi-icon time">⏳</div>
                </div>
                <div class="kpi-value" id="kpi-server-time" style="background: linear-gradient(135deg, #a855f7, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    {{ stats.total_server_online_fmt }}
                </div>
                <div class="kpi-sub">Accumulated today</div>
            </div>
        </div>

        <!-- Info bar -->
        <div class="info-bar">
            <div class="info-item">Timezone: <strong id="info-tz">{{ stats.timezone }}</strong></div>
            <div class="info-item">Daily Reset Date: <strong id="info-reset">{{ stats.last_reset_date }}</strong></div>
            <div class="info-item">Bot User: <strong id="info-bot-user">{{ stats.bot_user }}</strong></div>
            <div class="info-item">Last Updated: <strong id="info-last-updated">{{ stats.current_time }}</strong></div>
        </div>

        <!-- Controls & Table -->
        <div class="section-header">
            <div class="section-title">Member Statistics</div>
            <div class="controls">
                <div class="search-box">
                    <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                    <input type="text" id="searchInput" placeholder="Search members..." oninput="filterMembers()">
                </div>
                <button class="filter-btn active" data-filter="all" onclick="setFilter('all')">All</button>
                <button class="filter-btn" data-filter="online" onclick="setFilter('online')">Online</button>
                <button class="filter-btn" data-filter="idle" onclick="setFilter('idle')">Idle</button>
                <button class="filter-btn" data-filter="dnd" onclick="setFilter('dnd')">DND</button>
                <button class="filter-btn" data-filter="offline" onclick="setFilter('offline')">Offline</button>
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Member</th>
                        <th>Status</th>
                        <th>Online Today</th>
                        <th>Current Session</th>
                        <th>Last Change</th>
                    </tr>
                </thead>
                <tbody id="membersBody">
                    {% for m in stats.members %}
                    <tr class="member-row" data-name="{{ m.name | lower }}" data-username="{{ m.username | lower }}" data-status="{{ m.status }}">
                        <td>
                            <div class="user-cell">
                                {% if m.avatar_url %}
                                <img src="{{ m.avatar_url }}" alt="{{ m.name }}" class="avatar">
                                {% else %}
                                <div class="avatar">{{ m.name[0] | upper }}</div>
                                {% endif %}
                                <div class="user-names">
                                    <span class="user-name">{{ m.name }}</span>
                                    <span class="user-handle">{{ m.username }}</span>
                                </div>
                            </div>
                        </td>
                        <td>
                            <span class="badge-status {{ m.status }}">
                                <span class="status-dot {{ m.status }}"></span>
                                {{ m.status }}
                            </span>
                        </td>
                        <td>
                            <span class="time-pill">{{ m.online_today_formatted }}</span>
                        </td>
                        <td>
                            <span class="time-pill">{{ m.current_session_formatted }}</span>
                        </td>
                        <td style="color: var(--text-muted); font-size: 0.8rem;">
                            {{ m.last_change_time }}
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5">
                            <div class="empty-state">
                                <div class="empty-icon">📡</div>
                                <div>No member presence statistics recorded yet.</div>
                                <div style="font-size: 0.8rem; margin-top: 0.5rem; color: var(--text-muted);">
                                    Stats will populate automatically as Discord members change presence.
                                </div>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <footer>
            Status-Bot Dashboard • Real-time Discord Presence Tracking
        </footer>
    </div>

    <script>
        let currentFilter = 'all';

        function setFilter(filter) {
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.filter === filter);
            });
            filterMembers();
        }

        function filterMembers() {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const rows = document.querySelectorAll('.member-row');

            rows.forEach(row => {
                const name = row.dataset.name || '';
                const username = row.dataset.username || '';
                const status = row.dataset.status || '';

                const matchesSearch = name.includes(query) || username.includes(query);
                const matchesFilter = (currentFilter === 'all') || (status === currentFilter);

                row.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
            });
        }

        async function refreshStats() {
            try {
                const res = await fetch('/api/stats');
                if (!res.ok) return;
                const stats = await res.json();

                // Update Header & KPIs
                document.getElementById('guild-title').textContent = stats.guild_name;
                
                const dot = document.getElementById('bot-status-dot');
                dot.className = 'status-dot ' + stats.bot_status;
                document.getElementById('bot-status-text').textContent = 'Bot ' + stats.bot_status.charAt(0).toUpperCase() + stats.bot_status.slice(1);

                document.getElementById('kpi-total').textContent = stats.total_members;
                document.getElementById('kpi-online').textContent = stats.online_count;
                document.getElementById('kpi-away').textContent = stats.idle_count + stats.dnd_count;
                document.getElementById('kpi-idle-sub').textContent = stats.idle_count;
                document.getElementById('kpi-dnd-sub').textContent = stats.dnd_count;
                document.getElementById('kpi-server-time').textContent = stats.total_server_online_fmt;

                document.getElementById('info-tz').textContent = stats.timezone;
                document.getElementById('info-reset').textContent = stats.last_reset_date;
                document.getElementById('info-bot-user').textContent = stats.bot_user;
                document.getElementById('info-last-updated').textContent = stats.current_time;

                // Update Member rows
                const tbody = document.getElementById('membersBody');
                if (!stats.members || stats.members.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="5">
                                <div class="empty-state">
                                    <div class="empty-icon">📡</div>
                                    <div>No member presence statistics recorded yet.</div>
                                    <div style="font-size: 0.8rem; margin-top: 0.5rem; color: var(--text-muted);">
                                        Stats will populate automatically as Discord members change presence.
                                    </div>
                                </div>
                            </td>
                        </tr>`;
                    return;
                }

                let html = '';
                stats.members.forEach(m => {
                    const avatarHtml = m.avatar_url 
                        ? `<img src="${m.avatar_url}" alt="${m.name}" class="avatar">`
                        : `<div class="avatar">${(m.name[0] || '?').toUpperCase()}</div>`;

                    html += `
                        <tr class="member-row" data-name="${m.name.toLowerCase()}" data-username="${m.username.toLowerCase()}" data-status="${m.status}">
                            <td>
                                <div class="user-cell">
                                    ${avatarHtml}
                                    <div class="user-names">
                                        <span class="user-name">${m.name}</span>
                                        <span class="user-handle">${m.username}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="badge-status ${m.status}">
                                    <span class="status-dot ${m.status}"></span>
                                    ${m.status}
                                </span>
                            </td>
                            <td>
                                <span class="time-pill">${m.online_today_formatted}</span>
                            </td>
                            <td>
                                <span class="time-pill">${m.current_session_formatted}</span>
                            </td>
                            <td style="color: var(--text-muted); font-size: 0.8rem;">
                                ${m.last_change_time}
                            </td>
                        </tr>`;
                });
                tbody.innerHTML = html;
                filterMembers();
            } catch (err) {
                console.error('Failed to fetch stats:', err);
            }
        }

        // Auto refresh every 5 seconds
        setInterval(refreshStats, 5000);
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    stats = get_all_stats()
    return render_template_string(DASHBOARD_HTML, stats=stats)

@app.route("/api/stats")
def api_stats():
    return jsonify(get_all_stats())

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
