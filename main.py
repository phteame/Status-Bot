import threading
import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from flask import Flask, jsonify, render_template_string, request, Response
from bot import run_bot, get_status, get_all_stats, stats_manager, now

# ===== FLASK APP =====
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Executive Discord presence & activity reporting dashboard with weekly and monthly statistics.">
    <title>Status Bot Analytics & Reports - {{ stats.guild_name }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
    <!-- Chart.js for interactive reporting visualizations -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #080c14;
            --card-bg: rgba(15, 23, 42, 0.75);
            --card-border: rgba(255, 255, 255, 0.08);
            --card-hover: rgba(255, 255, 255, 0.14);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.3);
            --accent: #8b5cf6;
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
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 45%),
                radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.12) 0px, transparent 40%),
                radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 1.25rem 4rem 1.25rem;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
        }

        /* Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--card-border);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 1.25rem;
        }

        .bot-logo {
            width: 52px;
            height: 52px;
            border-radius: 16px;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.75rem;
            box-shadow: 0 4px 24px var(--primary-glow);
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #ffffff 30%, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 0.85rem;
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

        .status-dot.running { background-color: var(--online); box-shadow: 0 0 12px var(--online); }
        .status-dot.starting { background-color: var(--idle); box-shadow: 0 0 12px var(--idle); }
        .status-dot.error { background-color: var(--dnd); box-shadow: 0 0 12px var(--dnd); }

        .btn-export {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.25));
            border: 1px solid rgba(99, 102, 241, 0.4);
            color: #c7d2fe;
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
        }

        .btn-export:hover {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: #ffffff;
            box-shadow: 0 4px 16px var(--primary-glow);
            transform: translateY(-1px);
        }

        /* Navigation Tabs */
        .tabs-nav {
            display: flex;
            gap: 0.5rem;
            background: rgba(15, 23, 42, 0.6);
            padding: 6px;
            border-radius: 14px;
            border: 1px solid var(--card-border);
            margin-bottom: 2rem;
            overflow-x: auto;
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            white-space: nowrap;
        }

        .tab-btn:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.04);
        }

        .tab-btn.active {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: #ffffff;
            box-shadow: 0 4px 16px var(--primary-glow);
        }

        /* Tab Content */
        .tab-pane {
            display: none;
            animation: fadeIn 0.25s ease forwards;
        }

        .tab-pane.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
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
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 1.5rem;
            transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
            position: relative;
            overflow: hidden;
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        }

        .kpi-card:hover {
            transform: translateY(-3px);
            border-color: var(--card-hover);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
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
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }

        .kpi-icon.indigo { background: rgba(99, 102, 241, 0.18); color: #818cf8; }
        .kpi-icon.green { background: rgba(16, 185, 129, 0.18); color: #34d399; }
        .kpi-icon.amber { background: rgba(245, 158, 11, 0.18); color: #fbbf24; }
        .kpi-icon.purple { background: rgba(168, 85, 247, 0.18); color: #c084fc; }

        .kpi-value {
            font-family: 'Outfit', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-main);
            line-height: 1.2;
        }

        .kpi-sub {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.4rem;
        }

        /* Visual Chart Sections */
        .chart-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        @media (max-width: 960px) {
            .chart-grid { grid-template-columns: 1fr; }
        }

        .card-panel {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 1.5rem;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
        }

        .panel-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.15rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .chart-wrapper {
            position: relative;
            height: 260px;
            width: 100%;
        }

        /* Leaderboard Podium & List */
        .leaderboard-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .leader-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            transition: all 0.2s ease;
        }

        .leader-item:hover {
            background: rgba(255, 255, 255, 0.05);
            transform: translateX(3px);
        }

        .leader-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .leader-rank {
            font-weight: 700;
            font-size: 0.9rem;
            width: 24px;
            height: 24px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .rank-1 { background: rgba(234, 179, 8, 0.2); color: #facc15; }
        .rank-2 { background: rgba(148, 163, 184, 0.2); color: #cbd5e1; }
        .rank-3 { background: rgba(180, 83, 9, 0.2); color: #fb923c; }
        .rank-other { background: rgba(255, 255, 255, 0.05); color: var(--text-muted); }

        .leader-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #334155;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: 600;
            object-fit: cover;
        }

        .leader-name {
            font-size: 0.875rem;
            font-weight: 600;
        }

        .leader-score {
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            font-weight: 700;
            color: #a855f7;
        }

        /* Controls / Search */
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
            font-size: 1.3rem;
            font-weight: 700;
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
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 8px 14px 8px 36px;
            color: var(--text-main);
            font-size: 0.875rem;
            outline: none;
            width: 230px;
            transition: all 0.2s ease;
        }

        .search-box input:focus {
            border-color: var(--primary);
            width: 270px;
            box-shadow: 0 0 12px var(--primary-glow);
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
            padding: 7px 14px;
            color: var(--text-muted);
            font-size: 0.825rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .filter-btn:hover, .filter-btn.active {
            background: rgba(99, 102, 241, 0.2);
            border-color: var(--primary);
            color: #ffffff;
        }

        /* Enhanced Data Table */
        .table-container {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 20px;
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
            padding: 1.1rem 1.25rem;
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            border-bottom: 1px solid var(--card-border);
        }

        td {
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--card-border);
            vertical-align: middle;
        }

        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(255, 255, 255, 0.025); }

        .user-cell {
            display: flex;
            align-items: center;
            gap: 0.875rem;
        }

        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #475569, #334155);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 0.95rem;
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

        .time-pill.highlight {
            background: rgba(99, 102, 241, 0.15);
            border-color: rgba(99, 102, 241, 0.35);
            color: #a5b4fc;
        }

        .progress-bar-bg {
            width: 100px;
            height: 6px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 99px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-right: 8px;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #6366f1, #10b981);
            border-radius: 99px;
        }

        .info-bar {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 0.875rem 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            font-size: 0.825rem;
            color: var(--text-muted);
            margin-top: 2.5rem;
        }

        .info-item strong {
            color: var(--text-main);
            font-weight: 600;
        }

        footer {
            margin-top: 2rem;
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
        <!-- Top Header -->
        <header>
            <div class="brand">
                <div class="bot-logo">📊</div>
                <div>
                    <h1 id="guild-title">{{ stats.guild_name }}</h1>
                    <div class="subtitle">Presence Analytics & Activity Reporting System</div>
                </div>
            </div>
            <div class="header-actions">
                <div class="status-badge">
                    <span class="status-dot {{ stats.bot_status }}" id="bot-status-dot"></span>
                    <span id="bot-status-text">Bot {{ stats.bot_status | capitalize }}</span>
                </div>
                <a href="/api/export/csv?period=weekly" class="btn-export" id="btn-export-csv" title="Download spreadsheet report">
                    📥 Export CSV
                </a>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <div class="tabs-nav">
            <button class="tab-btn active" onclick="switchTab('overview')">
                <span>📈</span> Overview Analytics
            </button>
            <button class="tab-btn" onclick="switchTab('weekly')">
                <span>📅</span> Weekly Report (7 Days)
            </button>
            <button class="tab-btn" onclick="switchTab('monthly')">
                <span>🗓️</span> Monthly Report (30 Days)
            </button>
            <button class="tab-btn" onclick="switchTab('live')">
                <span>⚡</span> Live Monitor
            </button>
        </div>

        <!-- ==================== TAB 1: OVERVIEW ==================== -->
        <div id="pane-overview" class="tab-pane active">
            <!-- KPI Summary Cards -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Today Online Time</span>
                        <div class="kpi-icon green">⚡</div>
                    </div>
                    <div class="kpi-value" id="ov-today-time" style="color: #34d399;">
                        {{ stats.total_server_online_fmt }}
                    </div>
                    <div class="kpi-sub"><span id="ov-online-count">{{ stats.online_count }}</span> active members right now</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>This Week (7 Days)</span>
                        <div class="kpi-icon indigo">📅</div>
                    </div>
                    <div class="kpi-value" id="ov-week-time" style="color: #818cf8;">
                        {{ stats.weekly.total_server_formatted }}
                    </div>
                    <div class="kpi-sub">Avg <span id="ov-week-avg">{{ stats.weekly.avg_server_daily_formatted }}</span> / day • {{ stats.weekly.total_server_hours }} hrs</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>This Month (30 Days)</span>
                        <div class="kpi-icon purple">🗓️</div>
                    </div>
                    <div class="kpi-value" id="ov-month-time" style="background: linear-gradient(135deg, #c084fc, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        {{ stats.monthly.total_server_formatted }}
                    </div>
                    <div class="kpi-sub">Avg <span id="ov-month-avg">{{ stats.monthly.avg_server_daily_formatted }}</span> / day • {{ stats.monthly.total_server_hours }} hrs</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Team Participation</span>
                        <div class="kpi-icon amber">👥</div>
                    </div>
                    <div class="kpi-value" id="ov-active-rate" style="color: #fbbf24;">
                        {{ stats.weekly.active_rate_percentage }}%
                    </div>
                    <div class="kpi-sub"><span id="ov-active-count">{{ stats.weekly.active_team_count }}</span> of {{ stats.weekly.team_size }} members active this week</div>
                </div>
            </div>

            <!-- Charts and Quick Leaderboard -->
            <div class="chart-grid">
                <div class="card-panel">
                    <div class="panel-header">
                        <div class="panel-title"><span>📊</span> 7-Day Server Activity Trend</div>
                        <span style="font-size: 0.8rem; color: var(--text-muted);">Hours tracked per day</span>
                    </div>
                    <div class="chart-wrapper">
                        <canvas id="overviewWeeklyChart"></canvas>
                    </div>
                </div>

                <div class="card-panel">
                    <div class="panel-header">
                        <div class="panel-title"><span>🏆</span> Weekly Top Performers</div>
                        <a href="#" onclick="switchTab('weekly'); return false;" style="font-size: 0.8rem; color: #818cf8; text-decoration: none;">View All</a>
                    </div>
                    <div class="leaderboard-list" id="ov-leaderboard">
                        {% for m in stats.weekly.members[:5] %}
                        <div class="leader-item">
                            <div class="leader-left">
                                <span class="leader-rank {% if loop.index == 1 %}rank-1{% elif loop.index == 2 %}rank-2{% elif loop.index == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ loop.index }}
                                </span>
                                {% if m.avatar_url %}
                                <img src="{{ m.avatar_url }}" alt="{{ m.name }}" class="leader-avatar">
                                {% else %}
                                <div class="leader-avatar">{{ m.name[0] | upper }}</div>
                                {% endif %}
                                <div>
                                    <div class="leader-name">{{ m.name }}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted);">{{ m.active_days }} / 7 days active</div>
                                </div>
                            </div>
                            <div class="leader-score">{{ m.total_formatted }}</div>
                        </div>
                        {% else %}
                        <div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center;">No activity recorded yet.</div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>

        <!-- ==================== TAB 2: WEEKLY REPORT ==================== -->
        <div id="pane-weekly" class="tab-pane">
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>7-Day Total Hours</span>
                        <div class="kpi-icon indigo">⏳</div>
                    </div>
                    <div class="kpi-value" id="wk-total-time" style="color: #818cf8;">{{ stats.weekly.total_server_formatted }}</div>
                    <div class="kpi-sub">{{ stats.weekly.total_server_hours }} total hours accumulated</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Daily Average</span>
                        <div class="kpi-icon green">📊</div>
                    </div>
                    <div class="kpi-value" id="wk-daily-avg" style="color: #34d399;">{{ stats.weekly.avg_server_daily_formatted }}</div>
                    <div class="kpi-sub">Across 7 days</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Top Contributor</span>
                        <div class="kpi-icon amber">👑</div>
                    </div>
                    <div class="kpi-value" id="wk-top-name" style="font-size: 1.5rem; color: #fbbf24;">
                        {{ stats.weekly.top_contributor.name if stats.weekly.top_contributor else "None" }}
                    </div>
                    <div class="kpi-sub" id="wk-top-time">
                        {{ stats.weekly.top_contributor.total_formatted if stats.weekly.top_contributor else "-" }}
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Active Team Rate</span>
                        <div class="kpi-icon purple">🎯</div>
                    </div>
                    <div class="kpi-value" id="wk-part-rate" style="color: #c084fc;">{{ stats.weekly.active_rate_percentage }}%</div>
                    <div class="kpi-sub" id="wk-part-sub">{{ stats.weekly.active_team_count }} active out of {{ stats.weekly.team_size }}</div>
                </div>
            </div>

            <!-- Weekly Chart -->
            <div class="card-panel" style="margin-bottom: 2rem;">
                <div class="panel-header">
                    <div class="panel-title"><span>📅</span> Day-by-Day Activity (Last 7 Days)</div>
                    <a href="/api/export/csv?period=weekly" class="btn-export" style="font-size: 0.8rem; padding: 6px 12px;">Download Weekly CSV</a>
                </div>
                <div class="chart-wrapper">
                    <canvas id="weeklyBarChart"></canvas>
                </div>
            </div>

            <!-- Weekly Table -->
            <div class="section-header">
                <div class="section-title">Weekly Member Performance & Attendance</div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Member</th>
                            <th>Weekly Online Time</th>
                            <th>Daily Average</th>
                            <th>Days Active</th>
                            <th>Attendance %</th>
                        </tr>
                    </thead>
                    <tbody id="weeklyTableBody">
                        {% for m in stats.weekly.members %}
                        <tr>
                            <td>
                                <span class="leader-rank {% if m.rank == 1 %}rank-1{% elif m.rank == 2 %}rank-2{% elif m.rank == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ m.rank }}
                                </span>
                            </td>
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
                                <span class="time-pill highlight">{{ m.total_formatted }}</span>
                                <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 6px;">({{ m.total_hours }} hrs)</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ m.avg_daily_formatted }}</span>
                            </td>
                            <td>
                                <strong>{{ m.active_days }}</strong> / 7 Days
                            </td>
                            <td>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: {{ m.active_days_percentage }}%;"></div>
                                </div>
                                <span style="font-weight: 600; font-size: 0.8rem;">{{ m.active_days_percentage }}%</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ==================== TAB 3: MONTHLY REPORT ==================== -->
        <div id="pane-monthly" class="tab-pane">
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>30-Day Total Hours</span>
                        <div class="kpi-icon purple">🗓️</div>
                    </div>
                    <div class="kpi-value" id="mo-total-time" style="color: #c084fc;">{{ stats.monthly.total_server_formatted }}</div>
                    <div class="kpi-sub">{{ stats.monthly.total_server_hours }} total hours recorded</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Daily Average</span>
                        <div class="kpi-icon green">📈</div>
                    </div>
                    <div class="kpi-value" id="mo-daily-avg" style="color: #34d399;">{{ stats.monthly.avg_server_daily_formatted }}</div>
                    <div class="kpi-sub">Across 30 days</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Monthly Top Contributor</span>
                        <div class="kpi-icon amber">🌟</div>
                    </div>
                    <div class="kpi-value" id="mo-top-name" style="font-size: 1.5rem; color: #fbbf24;">
                        {{ stats.monthly.top_contributor.name if stats.monthly.top_contributor else "None" }}
                    </div>
                    <div class="kpi-sub" id="mo-top-time">
                        {{ stats.monthly.top_contributor.total_formatted if stats.monthly.top_contributor else "-" }}
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Active Team Size</span>
                        <div class="kpi-icon indigo">👥</div>
                    </div>
                    <div class="kpi-value" id="mo-part-rate" style="color: #818cf8;">{{ stats.monthly.active_rate_percentage }}%</div>
                    <div class="kpi-sub" id="mo-part-sub">{{ stats.monthly.active_team_count }} active out of {{ stats.monthly.team_size }}</div>
                </div>
            </div>

            <!-- Monthly Chart -->
            <div class="card-panel" style="margin-bottom: 2rem;">
                <div class="panel-header">
                    <div class="panel-title"><span>🗓️</span> 30-Day Activity Trend Line</div>
                    <a href="/api/export/csv?period=monthly" class="btn-export" style="font-size: 0.8rem; padding: 6px 12px;">Download Monthly CSV</a>
                </div>
                <div class="chart-wrapper">
                    <canvas id="monthlyTrendChart"></canvas>
                </div>
            </div>

            <!-- Monthly Table -->
            <div class="section-header">
                <div class="section-title">Monthly Member Attendance & Consistency</div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Member</th>
                            <th>Monthly Online Time</th>
                            <th>Daily Average</th>
                            <th>Days Active</th>
                            <th>Monthly Attendance %</th>
                        </tr>
                    </thead>
                    <tbody id="monthlyTableBody">
                        {% for m in stats.monthly.members %}
                        <tr>
                            <td>
                                <span class="leader-rank {% if m.rank == 1 %}rank-1{% elif m.rank == 2 %}rank-2{% elif m.rank == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ m.rank }}
                                </span>
                            </td>
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
                                <span class="time-pill highlight">{{ m.total_formatted }}</span>
                                <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 6px;">({{ m.total_hours }} hrs)</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ m.avg_daily_formatted }}</span>
                            </td>
                            <td>
                                <strong>{{ m.active_days }}</strong> / 30 Days
                            </td>
                            <td>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: {{ m.active_days_percentage }}%;"></div>
                                </div>
                                <span style="font-weight: 600; font-size: 0.8rem;">{{ m.active_days_percentage }}%</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ==================== TAB 4: LIVE MONITOR ==================== -->
        <div id="pane-live" class="tab-pane">
            <div class="section-header">
                <div class="section-title">Real-Time Presence Tracker</div>
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
                            <th>Week (7d)</th>
                            <th>Month (30d)</th>
                            <th>Current Session</th>
                            <th>Last Activity</th>
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
                                <span class="time-pill highlight">{{ m.online_today_formatted }}</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ m.online_week_formatted }}</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ m.online_month_formatted }}</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ m.current_session_formatted }}</span>
                            </td>
                            <td style="color: var(--text-muted); font-size: 0.8rem;">
                                {{ m.last_change_time }}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Info Bar -->
        <div class="info-bar">
            <div class="info-item">Timezone: <strong id="info-tz">{{ stats.timezone }}</strong></div>
            <div class="info-item">Tracking Server: <strong id="info-server">{{ stats.guild_name }}</strong></div>
            <div class="info-item">Bot User: <strong id="info-bot-user">{{ stats.bot_user }}</strong></div>
            <div class="info-item">Live Updated: <strong id="info-last-updated">{{ stats.current_time }}</strong></div>
        </div>

        <footer>
            Status Bot • Executive Discord Presence, Weekly & Monthly Reporting System
        </footer>
    </div>

    <!-- JavaScript logic & Chart.js initialization -->
    <script>
        let currentFilter = 'all';
        let currentTab = 'overview';
        let overviewChart, weeklyChart, monthlyChart;

        // Initialize Data passed from Flask
        const initialWeeklyTrends = {{ stats.weekly.daily_trends | tojson }};
        const initialMonthlyTrends = {{ stats.monthly.daily_trends | tojson }};

        function switchTab(tabId) {
            currentTab = tabId;
            document.querySelectorAll('.tab-btn').forEach(btn => {
                const isActive = btn.getAttribute('onclick').includes(tabId);
                btn.classList.toggle('active', isActive);
            });
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.toggle('active', pane.id === 'pane-' + tabId);
            });

            // Update CSV export button href based on tab
            const exportBtn = document.getElementById('btn-export-csv');
            if (tabId === 'monthly') {
                exportBtn.href = '/api/export/csv?period=monthly';
                exportBtn.textContent = '📥 Export Monthly CSV';
            } else {
                exportBtn.href = '/api/export/csv?period=weekly';
                exportBtn.textContent = '📥 Export Weekly CSV';
            }

            // Trigger chart resize if needed
            if (tabId === 'overview' && overviewChart) overviewChart.resize();
            if (tabId === 'weekly' && weeklyChart) weeklyChart.resize();
            if (tabId === 'monthly' && monthlyChart) monthlyChart.resize();
        }

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

        // Initialize Charts
        function initCharts() {
            Chart.defaults.color = '#94a3b8';
            Chart.defaults.font.family = "'Inter', sans-serif";

            // 1. Overview Weekly Chart (Line Area)
            const ctxOv = document.getElementById('overviewWeeklyChart').getContext('2d');
            overviewChart = new Chart(ctxOv, {
                type: 'line',
                data: {
                    labels: initialWeeklyTrends.map(d => d.display_date),
                    datasets: [{
                        label: 'Online Hours',
                        data: initialWeeklyTrends.map(d => d.total_hours),
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.15)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#818cf8'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.parsed.y} Hours`
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });

            // 2. Weekly Bar Chart
            const ctxWk = document.getElementById('weeklyBarChart').getContext('2d');
            weeklyChart = new Chart(ctxWk, {
                type: 'bar',
                data: {
                    labels: initialWeeklyTrends.map(d => `${d.day_name} (${d.display_date})`),
                    datasets: [{
                        label: 'Total Hours Tracked',
                        data: initialWeeklyTrends.map(d => d.total_hours),
                        backgroundColor: 'rgba(99, 102, 241, 0.7)',
                        borderColor: '#6366f1',
                        borderWidth: 1,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.parsed.y} Total Hours`
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });

            // 3. Monthly Line Trend Chart
            const ctxMo = document.getElementById('monthlyTrendChart').getContext('2d');
            monthlyChart = new Chart(ctxMo, {
                type: 'line',
                data: {
                    labels: initialMonthlyTrends.map(d => d.display_date),
                    datasets: [{
                        label: 'Daily Online Hours',
                        data: initialMonthlyTrends.map(d => d.total_hours),
                        borderColor: '#a855f7',
                        backgroundColor: 'rgba(168, 85, 247, 0.15)',
                        borderWidth: 2.5,
                        fill: true,
                        tension: 0.35,
                        pointRadius: 2,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.parsed.y} Hours`
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.05)' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { maxTicksLimit: 10 }
                        }
                    }
                }
            });
        }

        // Live Poll Function
        async function refreshStats() {
            try {
                const res = await fetch('/api/stats');
                if (!res.ok) return;
                const stats = await res.json();

                // Header
                document.getElementById('guild-title').textContent = stats.guild_name;
                const dot = document.getElementById('bot-status-dot');
                dot.className = 'status-dot ' + stats.bot_status;
                document.getElementById('bot-status-text').textContent = 'Bot ' + stats.bot_status.charAt(0).toUpperCase() + stats.bot_status.slice(1);

                // Overview KPIs
                document.getElementById('ov-today-time').textContent = stats.total_server_online_fmt;
                document.getElementById('ov-online-count').textContent = stats.online_count;
                document.getElementById('ov-week-time').textContent = stats.weekly.total_server_formatted;
                document.getElementById('ov-week-avg').textContent = stats.weekly.avg_server_daily_formatted;
                document.getElementById('ov-month-time').textContent = stats.monthly.total_server_formatted;
                document.getElementById('ov-month-avg').textContent = stats.monthly.avg_server_daily_formatted;
                document.getElementById('ov-active-rate').textContent = stats.weekly.active_rate_percentage + '%';
                document.getElementById('ov-active-count').textContent = stats.weekly.active_team_count;

                // Weekly KPIs
                document.getElementById('wk-total-time').textContent = stats.weekly.total_server_formatted;
                document.getElementById('wk-daily-avg').textContent = stats.weekly.avg_server_daily_formatted;
                if (stats.weekly.top_contributor) {
                    document.getElementById('wk-top-name').textContent = stats.weekly.top_contributor.name;
                    document.getElementById('wk-top-time').textContent = stats.weekly.top_contributor.total_formatted;
                }
                document.getElementById('wk-part-rate').textContent = stats.weekly.active_rate_percentage + '%';
                document.getElementById('wk-part-sub').textContent = `${stats.weekly.active_team_count} active out of ${stats.weekly.team_size}`;

                // Monthly KPIs
                document.getElementById('mo-total-time').textContent = stats.monthly.total_server_formatted;
                document.getElementById('mo-daily-avg').textContent = stats.monthly.avg_server_daily_formatted;
                if (stats.monthly.top_contributor) {
                    document.getElementById('mo-top-name').textContent = stats.monthly.top_contributor.name;
                    document.getElementById('mo-top-time').textContent = stats.monthly.top_contributor.total_formatted;
                }
                document.getElementById('mo-part-rate').textContent = stats.monthly.active_rate_percentage + '%';
                document.getElementById('mo-part-sub').textContent = `${stats.monthly.active_team_count} active out of ${stats.monthly.team_size}`;

                // Info bar
                document.getElementById('info-tz').textContent = stats.timezone;
                document.getElementById('info-server').textContent = stats.guild_name;
                document.getElementById('info-bot-user').textContent = stats.bot_user;
                document.getElementById('info-last-updated').textContent = stats.current_time;

                // Update Charts
                if (overviewChart && stats.weekly.daily_trends) {
                    overviewChart.data.labels = stats.weekly.daily_trends.map(d => d.display_date);
                    overviewChart.data.datasets[0].data = stats.weekly.daily_trends.map(d => d.total_hours);
                    overviewChart.update('none');
                }
                if (weeklyChart && stats.weekly.daily_trends) {
                    weeklyChart.data.labels = stats.weekly.daily_trends.map(d => `${d.day_name} (${d.display_date})`);
                    weeklyChart.data.datasets[0].data = stats.weekly.daily_trends.map(d => d.total_hours);
                    weeklyChart.update('none');
                }
                if (monthlyChart && stats.monthly.daily_trends) {
                    monthlyChart.data.labels = stats.monthly.daily_trends.map(d => d.display_date);
                    monthlyChart.data.datasets[0].data = stats.monthly.daily_trends.map(d => d.total_hours);
                    monthlyChart.update('none');
                }

                // Update Overview Podium List
                const ovPodium = document.getElementById('ov-leaderboard');
                if (ovPodium && stats.weekly.members) {
                    const top5 = stats.weekly.members.slice(0, 5);
                    ovPodium.innerHTML = top5.map((m, idx) => {
                        const rankClass = idx === 0 ? 'rank-1' : (idx === 1 ? 'rank-2' : (idx === 2 ? 'rank-3' : 'rank-other'));
                        const avatar = m.avatar_url 
                            ? `<img src="${m.avatar_url}" alt="${m.name}" class="leader-avatar">`
                            : `<div class="leader-avatar">${(m.name[0] || '?').toUpperCase()}</div>`;
                        return `
                        <div class="leader-item">
                            <div class="leader-left">
                                <span class="leader-rank ${rankClass}">${idx + 1}</span>
                                ${avatar}
                                <div>
                                    <div class="leader-name">${m.name}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted);">${m.active_days} / 7 days active</div>
                                </div>
                            </div>
                            <div class="leader-score">${m.total_formatted}</div>
                        </div>`;
                    }).join('') || '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center;">No activity recorded yet.</div>';
                }

                // Update Live Members Table
                const tbody = document.getElementById('membersBody');
                if (tbody && stats.members) {
                    tbody.innerHTML = stats.members.map(m => {
                        const avatarHtml = m.avatar_url 
                            ? `<img src="${m.avatar_url}" alt="${m.name}" class="avatar">`
                            : `<div class="avatar">${(m.name[0] || '?').toUpperCase()}</div>`;

                        return `
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
                                <span class="time-pill highlight">${m.online_today_formatted}</span>
                            </td>
                            <td>
                                <span class="time-pill">${m.online_week_formatted}</span>
                            </td>
                            <td>
                                <span class="time-pill">${m.online_month_formatted}</span>
                            </td>
                            <td>
                                <span class="time-pill">${m.current_session_formatted}</span>
                            </td>
                            <td style="color: var(--text-muted); font-size: 0.8rem;">
                                ${m.last_change_time}
                            </td>
                        </tr>`;
                    }).join('');
                    filterMembers();
                }

            } catch (err) {
                console.error('Error refreshing stats:', err);
            }
        }

        // Initialize on load
        window.addEventListener('DOMContentLoaded', () => {
            initCharts();
            setInterval(refreshStats, 5000);
        });
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

@app.route("/api/stats/weekly")
def api_stats_weekly():
    all_stats = get_all_stats()
    return jsonify(all_stats.get("weekly", {}))

@app.route("/api/stats/monthly")
def api_stats_monthly():
    all_stats = get_all_stats()
    return jsonify(all_stats.get("monthly", {}))

@app.route("/api/export/csv")
def api_export_csv():
    period = request.args.get("period", "weekly").lower()
    if period not in ["weekly", "monthly"]:
        period = "weekly"
    
    current_time = now()
    all_stats = get_all_stats()
    live_today_map = {m["id"]: m["online_today_seconds"] for m in all_stats.get("members", [])}
    
    csv_content = stats_manager.generate_csv_report(
        period_type=period,
        end_date=current_time,
        live_today_seconds=live_today_map
    )
    
    filename = f"discord_presence_{period}_{current_time.strftime('%Y%m%d')}.csv"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route("/health")
def health():
    return jsonify({"status": get_status(), "ok": True})

# ===== START BOT IN BACKGROUND =====
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

# ===== LOCAL DEV =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
