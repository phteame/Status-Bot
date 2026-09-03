import threading
import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from flask import Flask, jsonify, render_template_string, request, Response
from bot import run_bot, get_status, get_all_stats, stats_manager, now, trigger_sync

# ===== FLASK APP =====
app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Executive Discord presence & activity reporting dashboard with Today, Yesterday, Weekly, Monthly, and Custom Date/Team statistics.">
    <title>Status Bot Analytics & Reports - {{ stats.guild_name }}</title>
    
    <!-- Inline Theme Script to prevent flash of wrong theme -->
    <script>
        (function() {
            const savedTheme = localStorage.getItem('statusbot_theme') || 'auto';
            let effectiveTheme = savedTheme;
            if (savedTheme === 'auto') {
                effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            }
            document.documentElement.setAttribute('data-theme', effectiveTheme);
            document.documentElement.setAttribute('data-theme-setting', savedTheme);
        })();
    </script>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
    <!-- Chart.js for interactive reporting visualizations -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* Dark Theme Variables (Default) */
        html[data-theme="dark"] {
            --bg-color: #080c14;
            --bg-radial-1: rgba(99, 102, 241, 0.15);
            --bg-radial-2: rgba(139, 92, 246, 0.12);
            --bg-radial-3: rgba(16, 185, 129, 0.08);
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
            --input-bg: rgba(15, 23, 42, 0.9);
            --pill-bg: rgba(255, 255, 255, 0.04);
            --table-hover: rgba(255, 255, 255, 0.025);
            --tabs-bg: rgba(15, 23, 42, 0.6);
            --theme-selector-bg: rgba(15, 23, 42, 0.8);
            --title-gradient: linear-gradient(135deg, #ffffff 30%, #cbd5e1);
        }

        /* Light Theme Variables */
        html[data-theme="light"] {
            --bg-color: #f1f5f9;
            --bg-radial-1: rgba(99, 102, 241, 0.12);
            --bg-radial-2: rgba(139, 92, 246, 0.10);
            --bg-radial-3: rgba(16, 185, 129, 0.08);
            --card-bg: rgba(255, 255, 255, 0.9);
            --card-border: rgba(203, 213, 225, 0.85);
            --card-hover: rgba(148, 163, 184, 0.4);
            --text-main: #0f172a;
            --text-muted: #64748b;
            --primary: #4f46e5;
            --primary-glow: rgba(79, 70, 229, 0.2);
            --accent: #7c3aed;
            --online: #059669;
            --online-glow: rgba(5, 150, 105, 0.25);
            --idle: #d97706;
            --idle-glow: rgba(217, 119, 6, 0.25);
            --dnd: #dc2626;
            --dnd-glow: rgba(220, 38, 38, 0.25);
            --offline: #64748b;
            --input-bg: rgba(255, 255, 255, 0.95);
            --pill-bg: rgba(241, 245, 249, 0.9);
            --table-hover: rgba(241, 245, 249, 0.7);
            --tabs-bg: rgba(226, 232, 240, 0.8);
            --theme-selector-bg: rgba(226, 232, 240, 0.9);
            --title-gradient: linear-gradient(135deg, #0f172a 30%, #334155);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, var(--bg-radial-1) 0px, transparent 45%),
                radial-gradient(at 100% 0%, var(--bg-radial-2) 0px, transparent 40%),
                radial-gradient(at 50% 100%, var(--bg-radial-3) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 1.25rem 4rem 1.25rem;
            transition: background-color 0.3s ease, color 0.3s ease;
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
            background: var(--title-gradient);
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

        /* Theme Switcher Control */
        .theme-switcher {
            display: inline-flex;
            align-items: center;
            background: var(--theme-selector-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 3px;
            gap: 2px;
        }

        .theme-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 0.825rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            transition: all 0.2s ease;
        }

        .theme-btn:hover { color: var(--text-main); }

        .theme-btn.active {
            background: var(--card-bg);
            color: var(--text-main);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            border: 1px solid var(--card-border);
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 9999px;
            background: var(--pill-bg);
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
            color: var(--text-main);
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
            background: var(--tabs-bg);
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
            padding: 10px 18px;
            border-radius: 10px;
            font-size: 0.875rem;
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
            background: var(--pill-bg);
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
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
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
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
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
            font-size: 1.85rem;
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
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
            flex-wrap: wrap;
            gap: 0.75rem;
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

        /* Leaderboard List */
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
            background: var(--pill-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            transition: all 0.2s ease;
        }

        .leader-item:hover {
            background: var(--table-hover);
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

        .rank-1 { background: rgba(234, 179, 8, 0.2); color: #eab308; }
        .rank-2 { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
        .rank-3 { background: rgba(180, 83, 9, 0.2); color: #ea580c; }
        .rank-other { background: var(--pill-bg); color: var(--text-muted); }

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
            color: #fff;
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
            color: #8b5cf6;
        }

        /* Controls & Filter Bar */
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
            background: var(--input-bg);
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
            background: var(--pill-bg);
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
            color: var(--text-main);
        }

        /* Custom Report Controls */
        .report-filter-bar {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 1.25rem;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.25rem;
        }

        .report-inputs-group {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .custom-date-input {
            background: var(--input-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 8px 12px;
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            font-size: 0.875rem;
            font-weight: 600;
            outline: none;
            cursor: pointer;
        }

        .custom-date-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 10px var(--primary-glow);
        }

        .custom-select {
            background: var(--input-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 8px 14px;
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            font-size: 0.875rem;
            font-weight: 500;
            outline: none;
            cursor: pointer;
        }

        .quick-date-pills {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .date-pill {
            background: var(--pill-bg);
            border: 1px solid var(--card-border);
            color: var(--text-muted);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .date-pill:hover, .date-pill.active {
            background: rgba(99, 102, 241, 0.2);
            color: var(--text-main);
            border-color: var(--primary);
        }

        .btn-sync {
            background: var(--pill-bg);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }

        .btn-sync:hover {
            background: rgba(99, 102, 241, 0.15);
            border-color: var(--primary);
        }

        .btn-sync.spinning span {
            animation: spin 1s linear infinite;
        }

        @keyframes spin { 100% { transform: rotate(360deg); } }

        /* Timeline Feed */
        .timeline-container {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 1.5rem;
            margin-top: 2rem;
        }

        .timeline-list {
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
            max-height: 400px;
            overflow-y: auto;
            padding-right: 6px;
        }

        .timeline-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: var(--pill-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            transition: all 0.2s ease;
            gap: 12px;
        }

        .timeline-item:hover {
            background: var(--table-hover);
            transform: translateX(2px);
        }

        .timeline-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .timeline-time {
            font-family: monospace;
            font-size: 0.8rem;
            color: var(--text-muted);
            white-space: nowrap;
        }

        .timeline-body {
            font-size: 0.875rem;
            color: var(--text-main);
        }

        /* Enhanced Data Table */
        .table-container {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            overflow: hidden;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.875rem;
        }

        th {
            background: var(--pill-bg);
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
        tr:hover td { background: var(--table-hover); }

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

        .badge-status.online { background: rgba(16, 185, 129, 0.15); color: var(--online); border: 1px solid var(--online-glow); }
        .badge-status.idle { background: rgba(245, 158, 11, 0.15); color: var(--idle); border: 1px solid var(--idle-glow); }
        .badge-status.dnd { background: rgba(239, 68, 68, 0.15); color: var(--dnd); border: 1px solid var(--dnd-glow); }
        .badge-status.offline { background: rgba(100, 116, 139, 0.15); color: var(--offline); border: 1px solid var(--card-border); }

        .time-pill {
            display: inline-block;
            background: var(--pill-bg);
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
            color: var(--primary);
        }

        .progress-bar-bg {
            width: 100px;
            height: 6px;
            background: var(--pill-bg);
            border-radius: 99px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-right: 8px;
            border: 1px solid var(--card-border);
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #6366f1, #10b981);
            border-radius: 99px;
        }

        .info-bar {
            background: var(--card-bg);
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
                <!-- Theme Switcher -->
                <div class="theme-switcher" id="theme-switcher">
                    <button class="theme-btn" data-theme-val="dark" onclick="setTheme('dark')" title="Dark Mode">
                        <span>🌙</span> Dark
                    </button>
                    <button class="theme-btn" data-theme-val="light" onclick="setTheme('light')" title="Light Mode">
                        <span>☀️</span> Light
                    </button>
                    <button class="theme-btn" data-theme-val="auto" onclick="setTheme('auto')" title="System Automatic Theme">
                        <span>💻</span> Auto
                    </button>
                </div>

                <div class="status-badge">
                    <span class="status-dot {{ stats.bot_status }}" id="bot-status-dot"></span>
                    <span id="bot-status-text">Bot {{ stats.bot_status | capitalize }}</span>
                </div>
                <a href="/api/export/csv?period=today" class="btn-export" id="btn-export-csv" title="Download spreadsheet report">
                    📥 Export CSV
                </a>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <div class="tabs-nav">
            <button class="tab-btn active" onclick="switchTab('overview')">
                <span>📈</span> Overview Analytics
            </button>
            <button class="tab-btn" onclick="switchTab('today')">
                <span>⚡</span> Today
            </button>
            <button class="tab-btn" onclick="switchTab('yesterday')">
                <span>⏮️</span> Yesterday
            </button>
            <button class="tab-btn" onclick="switchTab('weekly')">
                <span>📅</span> Weekly (7d)
            </button>
            <button class="tab-btn" onclick="switchTab('monthly')">
                <span>🗓️</span> Monthly (30d)
            </button>
            <button class="tab-btn" onclick="switchTab('report')">
                <span>📋</span> Report (Filter by Day & Team)
            </button>
            <button class="tab-btn" onclick="switchTab('live')">
                <span>📡</span> Live Monitor
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
                    <div class="kpi-value" id="ov-today-time" style="color: var(--online);">
                        {{ stats.total_server_online_fmt }}
                    </div>
                    <div class="kpi-sub"><span id="ov-online-count">{{ stats.online_count }}</span> active members right now</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Yesterday Online Time</span>
                        <div class="kpi-icon amber">⏮️</div>
                    </div>
                    <div class="kpi-value" id="ov-yesterday-time" style="color: var(--idle);">
                        {{ stats.yesterday.total_server_formatted }}
                    </div>
                    <div class="kpi-sub">{{ stats.yesterday.active_team_count }} active members yesterday</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>This Week (7 Days)</span>
                        <div class="kpi-icon indigo">📅</div>
                    </div>
                    <div class="kpi-value" id="ov-week-time" style="color: var(--primary);">
                        {{ stats.weekly.total_server_formatted }}
                    </div>
                    <div class="kpi-sub">Avg <span id="ov-week-avg">{{ stats.weekly.avg_server_daily_formatted }}</span> / day • {{ stats.weekly.total_server_hours }} hrs</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>This Month (30 Days)</span>
                        <div class="kpi-icon purple">🗓️</div>
                    </div>
                    <div class="kpi-value" id="ov-month-time" style="color: var(--accent);">
                        {{ stats.monthly.total_server_formatted }}
                    </div>
                    <div class="kpi-sub">Avg <span id="ov-month-avg">{{ stats.monthly.avg_server_daily_formatted }}</span> / day • {{ stats.monthly.total_server_hours }} hrs</div>
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
                        <a href="#" onclick="switchTab('weekly'); return false;" style="font-size: 0.8rem; color: var(--primary); text-decoration: none;">View All</a>
                    </div>
                    <div class="leaderboard-list" id="ov-leaderboard">
                        {% for item in stats.weekly.members[:5] %}
                        <div class="leader-item">
                            <div class="leader-left">
                                <span class="leader-rank {% if loop.index == 1 %}rank-1{% elif loop.index == 2 %}rank-2{% elif loop.index == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ loop.index }}
                                </span>
                                {% if item.avatar_url %}
                                <img src="{{ item.avatar_url }}" alt="{{ item.name }}" class="leader-avatar">
                                {% else %}
                                <div class="leader-avatar">{{ item.name[0] | upper }}</div>
                                {% endif %}
                                <div>
                                    <div class="leader-name">{{ item.name }}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted);">{{ item.active_days }} / 7 days active</div>
                                </div>
                            </div>
                            <div class="leader-score">{{ item.total_formatted }}</div>
                        </div>
                        {% else %}
                        <div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center;">No activity recorded yet.</div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>

        <!-- ==================== TAB 2: TODAY REPORT ==================== -->
        <div id="pane-today" class="tab-pane">
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Today Total Tracked</span>
                        <div class="kpi-icon green">⚡</div>
                    </div>
                    <div class="kpi-value" id="td-total-time" style="color: var(--online);">{{ stats.today.total_server_formatted }}</div>
                    <div class="kpi-sub" id="td-total-hrs">{{ stats.today.total_server_hours }} hours accumulated today</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Today's Top Contributor</span>
                        <div class="kpi-icon amber">👑</div>
                    </div>
                    <div class="kpi-value" id="td-top-name" style="font-size: 1.5rem; color: var(--idle);">
                        {{ stats.today.top_contributor.name if stats.today.top_contributor else "None" }}
                    </div>
                    <div class="kpi-sub" id="td-top-time">
                        {{ stats.today.top_contributor.total_formatted if stats.today.top_contributor else "-" }}
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Active Team Today</span>
                        <div class="kpi-icon indigo">👥</div>
                    </div>
                    <div class="kpi-value" id="td-part-rate" style="color: var(--primary);">{{ stats.today.active_rate_percentage }}%</div>
                    <div class="kpi-sub" id="td-part-sub">{{ stats.today.active_team_count }} active out of {{ stats.today.team_size }}</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Today's Status Changes</span>
                        <div class="kpi-icon purple">📝</div>
                    </div>
                    <div class="kpi-value" id="td-events-count" style="color: var(--accent);">{{ stats.today.total_events_count }}</div>
                    <div class="kpi-sub">Events logged in #online-report</div>
                </div>
            </div>

            <!-- Today Hourly Chart -->
            <div class="card-panel" style="margin-bottom: 2rem;">
                <div class="panel-header">
                    <div class="panel-title"><span>⚡</span> Today's Hourly Activity Breakdown (24h)</div>
                    <a href="/api/export/csv?period=today" class="btn-export" style="font-size: 0.8rem; padding: 6px 12px;">Download Today's CSV</a>
                </div>
                <div class="chart-wrapper">
                    <canvas id="todayHourlyChart"></canvas>
                </div>
            </div>

            <!-- Today Member Table -->
            <div class="section-header">
                <div class="section-title">Today's Team Performance & Attendance</div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Member</th>
                            <th>Today Online Time</th>
                            <th>Total Hours</th>
                            <th>Share %</th>
                            <th>Status Changes</th>
                        </tr>
                    </thead>
                    <tbody id="todayTableBody">
                        {% for mem in stats.today.members %}
                        <tr>
                            <td>
                                <span class="leader-rank {% if mem.rank == 1 %}rank-1{% elif mem.rank == 2 %}rank-2{% elif mem.rank == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ mem.rank }}
                                </span>
                            </td>
                            <td>
                                <div class="user-cell">
                                    {% if mem.avatar_url %}
                                    <img src="{{ mem.avatar_url }}" alt="{{ mem.name }}" class="avatar">
                                    {% else %}
                                    <div class="avatar">{{ mem.name[0] | upper }}</div>
                                    {% endif %}
                                    <div class="user-names">
                                        <span class="user-name">{{ mem.name }}</span>
                                        <span class="user-handle">{{ mem.username }}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="time-pill highlight">{{ mem.total_formatted }}</span>
                            </td>
                            <td>
                                <strong>{{ mem.total_hours }}</strong> hrs
                            </td>
                            <td>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: {{ mem.share_percentage }}%;"></div>
                                </div>
                                <span style="font-weight: 600; font-size: 0.8rem;">{{ mem.share_percentage }}%</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.events_count }} events</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ==================== TAB 3: YESTERDAY REPORT ==================== -->
        <div id="pane-yesterday" class="tab-pane">
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Yesterday Total Tracked</span>
                        <div class="kpi-icon amber">⏮️</div>
                    </div>
                    <div class="kpi-value" id="yd-total-time" style="color: var(--idle);">{{ stats.yesterday.total_server_formatted }}</div>
                    <div class="kpi-sub" id="yd-total-hrs">{{ stats.yesterday.total_server_hours }} hours accumulated yesterday</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Yesterday's Top Contributor</span>
                        <div class="kpi-icon green">👑</div>
                    </div>
                    <div class="kpi-value" id="yd-top-name" style="font-size: 1.5rem; color: var(--online);">
                        {{ stats.yesterday.top_contributor.name if stats.yesterday.top_contributor else "None" }}
                    </div>
                    <div class="kpi-sub" id="yd-top-time">
                        {{ stats.yesterday.top_contributor.total_formatted if stats.yesterday.top_contributor else "-" }}
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Active Team Yesterday</span>
                        <div class="kpi-icon indigo">👥</div>
                    </div>
                    <div class="kpi-value" id="yd-part-rate" style="color: var(--primary);">{{ stats.yesterday.active_rate_percentage }}%</div>
                    <div class="kpi-sub" id="yd-part-sub">{{ stats.yesterday.active_team_count }} active out of {{ stats.yesterday.team_size }}</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Yesterday's Status Changes</span>
                        <div class="kpi-icon purple">📝</div>
                    </div>
                    <div class="kpi-value" id="yd-events-count" style="color: var(--accent);">{{ stats.yesterday.total_events_count }}</div>
                    <div class="kpi-sub">Events logged in #online-report</div>
                </div>
            </div>

            <!-- Yesterday Hourly Chart -->
            <div class="card-panel" style="margin-bottom: 2rem;">
                <div class="panel-header">
                    <div class="panel-title"><span>⏮️</span> Yesterday's Hourly Activity Breakdown ({{ stats.yesterday.display_date }})</div>
                    <a href="/api/export/csv?period=yesterday" class="btn-export" style="font-size: 0.8rem; padding: 6px 12px;">Download Yesterday's CSV</a>
                </div>
                <div class="chart-wrapper">
                    <canvas id="yesterdayHourlyChart"></canvas>
                </div>
            </div>

            <!-- Yesterday Member Table -->
            <div class="section-header">
                <div class="section-title">Yesterday's Team Performance & Attendance</div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Member</th>
                            <th>Yesterday Online Time</th>
                            <th>Total Hours</th>
                            <th>Share %</th>
                            <th>Status Changes</th>
                        </tr>
                    </thead>
                    <tbody id="yesterdayTableBody">
                        {% for mem in stats.yesterday.members %}
                        <tr>
                            <td>
                                <span class="leader-rank {% if mem.rank == 1 %}rank-1{% elif mem.rank == 2 %}rank-2{% elif mem.rank == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ mem.rank }}
                                </span>
                            </td>
                            <td>
                                <div class="user-cell">
                                    {% if mem.avatar_url %}
                                    <img src="{{ mem.avatar_url }}" alt="{{ mem.name }}" class="avatar">
                                    {% else %}
                                    <div class="avatar">{{ mem.name[0] | upper }}</div>
                                    {% endif %}
                                    <div class="user-names">
                                        <span class="user-name">{{ mem.name }}</span>
                                        <span class="user-handle">{{ mem.username }}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="time-pill highlight">{{ mem.total_formatted }}</span>
                            </td>
                            <td>
                                <strong>{{ mem.total_hours }}</strong> hrs
                            </td>
                            <td>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: {{ mem.share_percentage }}%;"></div>
                                </div>
                                <span style="font-weight: 600; font-size: 0.8rem;">{{ mem.share_percentage }}%</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.events_count }} events</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ==================== TAB 4: WEEKLY REPORT ==================== -->
        <div id="pane-weekly" class="tab-pane">
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>7-Day Total Hours</span>
                        <div class="kpi-icon indigo">⏳</div>
                    </div>
                    <div class="kpi-value" id="wk-total-time" style="color: var(--primary);">{{ stats.weekly.total_server_formatted }}</div>
                    <div class="kpi-sub">{{ stats.weekly.total_server_hours }} total hours accumulated</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Daily Average</span>
                        <div class="kpi-icon green">📊</div>
                    </div>
                    <div class="kpi-value" id="wk-daily-avg" style="color: var(--online);">{{ stats.weekly.avg_server_daily_formatted }}</div>
                    <div class="kpi-sub">Across 7 days</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Top Contributor</span>
                        <div class="kpi-icon amber">👑</div>
                    </div>
                    <div class="kpi-value" id="wk-top-name" style="font-size: 1.5rem; color: var(--idle);">
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
                    <div class="kpi-value" id="wk-part-rate" style="color: var(--accent);">{{ stats.weekly.active_rate_percentage }}%</div>
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
                        {% for mem in stats.weekly.members %}
                        <tr>
                            <td>
                                <span class="leader-rank {% if mem.rank == 1 %}rank-1{% elif mem.rank == 2 %}rank-2{% elif mem.rank == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ mem.rank }}
                                </span>
                            </td>
                            <td>
                                <div class="user-cell">
                                    {% if mem.avatar_url %}
                                    <img src="{{ mem.avatar_url }}" alt="{{ mem.name }}" class="avatar">
                                    {% else %}
                                    <div class="avatar">{{ mem.name[0] | upper }}</div>
                                    {% endif %}
                                    <div class="user-names">
                                        <span class="user-name">{{ mem.name }}</span>
                                        <span class="user-handle">{{ mem.username }}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="time-pill highlight">{{ mem.total_formatted }}</span>
                                <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 6px;">({{ mem.total_hours }} hrs)</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.avg_daily_formatted }}</span>
                            </td>
                            <td>
                                <strong>{{ mem.active_days }}</strong> / 7 Days
                            </td>
                            <td>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: {{ mem.active_days_percentage }}%;"></div>
                                </div>
                                <span style="font-weight: 600; font-size: 0.8rem;">{{ mem.active_days_percentage }}%</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ==================== TAB 5: MONTHLY REPORT ==================== -->
        <div id="pane-monthly" class="tab-pane">
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>30-Day Total Hours</span>
                        <div class="kpi-icon purple">🗓️</div>
                    </div>
                    <div class="kpi-value" id="mo-total-time" style="color: var(--accent);">{{ stats.monthly.total_server_formatted }}</div>
                    <div class="kpi-sub">{{ stats.monthly.total_server_hours }} total hours recorded</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Daily Average</span>
                        <div class="kpi-icon green">📈</div>
                    </div>
                    <div class="kpi-value" id="mo-daily-avg" style="color: var(--online);">{{ stats.monthly.avg_server_daily_formatted }}</div>
                    <div class="kpi-sub">Across 30 days</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Monthly Top Contributor</span>
                        <div class="kpi-icon amber">🌟</div>
                    </div>
                    <div class="kpi-value" id="mo-top-name" style="font-size: 1.5rem; color: var(--idle);">
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
                    <div class="kpi-value" id="mo-part-rate" style="color: var(--primary);">{{ stats.monthly.active_rate_percentage }}%</div>
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
                        {% for mem in stats.monthly.members %}
                        <tr>
                            <td>
                                <span class="leader-rank {% if mem.rank == 1 %}rank-1{% elif mem.rank == 2 %}rank-2{% elif mem.rank == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ mem.rank }}
                                </span>
                            </td>
                            <td>
                                <div class="user-cell">
                                    {% if mem.avatar_url %}
                                    <img src="{{ mem.avatar_url }}" alt="{{ mem.name }}" class="avatar">
                                    {% else %}
                                    <div class="avatar">{{ mem.name[0] | upper }}</div>
                                    {% endif %}
                                    <div class="user-names">
                                        <span class="user-name">{{ mem.name }}</span>
                                        <span class="user-handle">{{ mem.username }}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="time-pill highlight">{{ mem.total_formatted }}</span>
                                <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 6px;">({{ mem.total_hours }} hrs)</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.avg_daily_formatted }}</span>
                            </td>
                            <td>
                                <strong>{{ mem.active_days }}</strong> / 30 Days
                            </td>
                            <td>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: {{ mem.active_days_percentage }}%;"></div>
                                </div>
                                <span style="font-weight: 600; font-size: 0.8rem;">{{ mem.active_days_percentage }}%</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ==================== TAB 6: CUSTOM REPORT (DATE & TEAM FILTER) ==================== -->
        <div id="pane-report" class="tab-pane">
            <!-- Filter Bar -->
            <div class="report-filter-bar">
                <div class="report-inputs-group">
                    <div>
                        <label style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 4px; font-weight: 600;">SELECT DATE</label>
                        <input type="date" id="reportDatePicker" class="custom-date-input" value="{{ stats.today.date }}" onchange="handleDateChange(this.value)">
                    </div>

                    <div>
                        <label style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 4px; font-weight: 600;">FILTER TEAM / MEMBER</label>
                        <select id="reportMemberFilter" class="custom-select" onchange="handleMemberFilterChange(this.value)">
                            <option value="all">👥 All Team Members</option>
                            {% for mem in stats.members %}
                            <option value="{{ mem.id }}">{{ mem.name }} (@{{ mem.username }})</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="quick-date-pills" style="margin-top: 18px;">
                        <button class="date-pill active" onclick="setQuickDate(0, this)">Today</button>
                        <button class="date-pill" onclick="setQuickDate(1, this)">Yesterday</button>
                        <button class="date-pill" onclick="setQuickDate(2, this)">2d Ago</button>
                        <button class="date-pill" onclick="setQuickDate(3, this)">3d Ago</button>
                        <button class="date-pill" onclick="setQuickDate(7, this)">7d Ago</button>
                    </div>
                </div>

                <div style="display: flex; gap: 8px; align-items: center; margin-top: 10px;">
                    <button class="btn-sync" id="btn-sync-channel" onclick="syncChannelHistoryNow()" title="Scan & parse messages from Discord #online-report channel">
                        <span>🔄</span> Sync Discord Channel
                    </button>
                    <a href="/api/export/csv?period=today" id="btn-report-export-csv" class="btn-export" style="font-size: 0.825rem; padding: 8px 14px;">
                        📥 Download Day CSV
                    </a>
                </div>
            </div>

            <!-- Date Header -->
            <div style="margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                <div>
                    <h2 id="reportDateHeading" style="font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 700; color: var(--text-main);">
                        {{ stats.today.display_date }}
                    </h2>
                    <div id="reportSubheading" style="font-size: 0.85rem; color: var(--text-muted); margin-top: 2px;">
                        Showing presence statistics from Discord channel #online-report
                    </div>
                </div>
                <div id="reportFilteredMemberBadge" style="display: none;" class="status-badge">
                    <span>👤 Filtered: <strong id="reportFilteredMemberName"></strong></span>
                    <button onclick="clearMemberFilter()" style="background: none; border: none; color: var(--dnd); cursor: pointer; font-weight: bold; margin-left: 6px;">✕</button>
                </div>
            </div>

            <!-- Report KPI Cards -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Total Tracked Hours</span>
                        <div class="kpi-icon indigo">⏳</div>
                    </div>
                    <div class="kpi-value" id="rep-total-time" style="color: var(--primary);">{{ stats.today.total_server_formatted }}</div>
                    <div class="kpi-sub" id="rep-total-hrs">{{ stats.today.total_server_hours }} total hours</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Active Team Members</span>
                        <div class="kpi-icon green">👥</div>
                    </div>
                    <div class="kpi-value" id="rep-active-count" style="color: var(--online);">{{ stats.today.active_team_count }}</div>
                    <div class="kpi-sub" id="rep-active-rate">{{ stats.today.active_rate_percentage }}% participation (out of {{ stats.today.team_size }})</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Top Performer on Date</span>
                        <div class="kpi-icon amber">👑</div>
                    </div>
                    <div class="kpi-value" id="rep-top-name" style="font-size: 1.5rem; color: var(--idle);">
                        {{ stats.today.top_contributor.name if stats.today.top_contributor else "None" }}
                    </div>
                    <div class="kpi-sub" id="rep-top-time">
                        {{ stats.today.top_contributor.total_formatted if stats.today.top_contributor else "-" }}
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-header">
                        <span>Status Events Recorded</span>
                        <div class="kpi-icon purple">📝</div>
                    </div>
                    <div class="kpi-value" id="rep-events-count" style="color: var(--accent);">{{ stats.today.total_events_count }}</div>
                    <div class="kpi-sub">Online / offline transitions</div>
                </div>
            </div>

            <!-- Report Chart -->
            <div class="card-panel" style="margin-bottom: 2rem;">
                <div class="panel-header">
                    <div class="panel-title"><span>📊</span> 24-Hour Activity & Event Distribution</div>
                    <span id="reportChartSub" style="font-size: 0.8rem; color: var(--text-muted);">Hourly event activity across 00:00 - 23:00</span>
                </div>
                <div class="chart-wrapper">
                    <canvas id="reportHourlyChart"></canvas>
                </div>
            </div>

            <!-- Member Performance Table -->
            <div class="section-header">
                <div class="section-title">Team Performance on Selected Date</div>
            </div>
            <div class="table-container" style="margin-bottom: 2rem;">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Member</th>
                            <th>Online Time on Date</th>
                            <th>Total Hours</th>
                            <th>Share %</th>
                            <th>Status Changes</th>
                        </tr>
                    </thead>
                    <tbody id="reportTableBody">
                        {% for mem in stats.today.members %}
                        <tr>
                            <td>
                                <span class="leader-rank {% if mem.rank == 1 %}rank-1{% elif mem.rank == 2 %}rank-2{% elif mem.rank == 3 %}rank-3{% else %}rank-other{% endif %}">
                                    {{ mem.rank }}
                                </span>
                            </td>
                            <td>
                                <div class="user-cell">
                                    {% if mem.avatar_url %}
                                    <img src="{{ mem.avatar_url }}" alt="{{ mem.name }}" class="avatar">
                                    {% else %}
                                    <div class="avatar">{{ mem.name[0] | upper }}</div>
                                    {% endif %}
                                    <div class="user-names">
                                        <span class="user-name">{{ mem.name }}</span>
                                        <span class="user-handle">{{ mem.username }}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="time-pill highlight">{{ mem.total_formatted }}</span>
                            </td>
                            <td>
                                <strong>{{ mem.total_hours }}</strong> hrs
                            </td>
                            <td>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: {{ mem.share_percentage }}%;"></div>
                                </div>
                                <span style="font-weight: 600; font-size: 0.8rem;">{{ mem.share_percentage }}%</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.events_count }} events</span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            <!-- Timeline Event Feed -->
            <div class="timeline-container">
                <div class="panel-header">
                    <div class="panel-title"><span>📜</span> Detailed Status Change Timeline (from #online-report)</div>
                    <span style="font-size: 0.8rem; color: var(--text-muted);" id="timelineCountText">
                        {{ stats.today.events | length }} events logged
                    </span>
                </div>
                <div class="timeline-list" id="reportTimelineList">
                    {% for ev in stats.today.events %}
                    <div class="timeline-item">
                        <div class="timeline-left">
                            <span class="badge-status {{ ev.type }}">{{ ev.type }}</span>
                            <span class="timeline-time">{{ ev.time_str }}</span>
                            <span class="timeline-body"><strong>{{ ev.name }}</strong>: {{ ev.text }}</span>
                        </div>
                        {% if ev.duration_fmt %}
                        <span class="time-pill highlight">{{ ev.duration_fmt }}</span>
                        {% endif %}
                    </div>
                    {% else %}
                    <div style="color: var(--text-muted); font-size: 0.85rem; padding: 1.5rem; text-align: center;">No status changes recorded for this date.</div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- ==================== TAB 7: LIVE MONITOR ==================== -->
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
                            <th>Yesterday</th>
                            <th>Week (7d)</th>
                            <th>Month (30d)</th>
                            <th>Current Session</th>
                            <th>Last Activity</th>
                        </tr>
                    </thead>
                    <tbody id="membersBody">
                        {% for mem in stats.members %}
                        <tr class="member-row" data-name="{{ mem.name | lower }}" data-username="{{ mem.username | lower }}" data-status="{{ mem.status }}">
                            <td>
                                <div class="user-cell">
                                    {% if mem.avatar_url %}
                                    <img src="{{ mem.avatar_url }}" alt="{{ mem.name }}" class="avatar">
                                    {% else %}
                                    <div class="avatar">{{ mem.name[0] | upper }}</div>
                                    {% endif %}
                                    <div class="user-names">
                                        <span class="user-name">{{ mem.name }}</span>
                                        <span class="user-handle">{{ mem.username }}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="badge-status {{ mem.status }}">
                                    <span class="status-dot {{ mem.status }}"></span>
                                    {{ mem.status }}
                                </span>
                            </td>
                            <td>
                                <span class="time-pill highlight">{{ mem.online_today_formatted }}</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.online_yesterday_formatted }}</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.online_week_formatted }}</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.online_month_formatted }}</span>
                            </td>
                            <td>
                                <span class="time-pill">{{ mem.current_session_formatted }}</span>
                            </td>
                            <td style="color: var(--text-muted); font-size: 0.8rem;">
                                {{ mem.last_change_time }}
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
            Status Bot • Executive Discord Presence, Daily, Weekly & Monthly Reporting System
        </footer>
    </div>

    <!-- JavaScript logic & Chart.js initialization -->
    <script>
        let currentFilter = 'all';
        let currentTab = 'overview';
        let selectedReportDate = '{{ stats.today.date }}';
        let selectedReportMember = 'all';

        let overviewChart, todayChart, yesterdayChart, weeklyChart, monthlyChart, reportChart;

        // Data from Flask
        const initialWeeklyTrends = {{ stats.weekly.daily_trends | tojson }};
        const initialMonthlyTrends = {{ stats.monthly.daily_trends | tojson }};
        const initialTodayHourly = {{ stats.today.hourly_distribution | tojson }};
        const initialYesterdayHourly = {{ stats.yesterday.hourly_distribution | tojson }};

        // Theme Management
        function setTheme(theme) {
            localStorage.setItem('statusbot_theme', theme);
            document.documentElement.setAttribute('data-theme-setting', theme);
            
            let effectiveTheme = theme;
            if (theme === 'auto') {
                effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            }
            document.documentElement.setAttribute('data-theme', effectiveTheme);
            updateThemeUI(theme);
            updateChartsTheme(effectiveTheme);
        }

        function updateThemeUI(selectedSetting) {
            document.querySelectorAll('.theme-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.themeVal === selectedSetting);
            });
        }

        // Listen for OS color scheme change when in 'auto' mode
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            const currentSetting = localStorage.getItem('statusbot_theme') || 'auto';
            if (currentSetting === 'auto') {
                const effective = e.matches ? 'dark' : 'light';
                document.documentElement.setAttribute('data-theme', effective);
                updateChartsTheme(effective);
            }
        });

        function updateChartsTheme(theme) {
            const isDark = theme === 'dark';
            const gridColor = isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)';
            const textColor = isDark ? '#94a3b8' : '#64748b';

            Chart.defaults.color = textColor;

            [overviewChart, todayChart, yesterdayChart, weeklyChart, monthlyChart, reportChart].forEach(chart => {
                if (!chart) return;
                if (chart.options.scales && chart.options.scales.y) {
                    chart.options.scales.y.grid.color = gridColor;
                    chart.options.scales.y.ticks.color = textColor;
                }
                if (chart.options.scales && chart.options.scales.x) {
                    chart.options.scales.x.ticks.color = textColor;
                }
                chart.update('none');
            });
        }

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
            if (tabId === 'today') {
                exportBtn.href = '/api/export/csv?period=today';
                exportBtn.textContent = '📥 Export Today CSV';
            } else if (tabId === 'yesterday') {
                exportBtn.href = '/api/export/csv?period=yesterday';
                exportBtn.textContent = '📥 Export Yesterday CSV';
            } else if (tabId === 'monthly') {
                exportBtn.href = '/api/export/csv?period=monthly';
                exportBtn.textContent = '📥 Export Monthly CSV';
            } else if (tabId === 'report') {
                exportBtn.href = `/api/export/csv?period=${selectedReportDate}`;
                exportBtn.textContent = '📥 Export Day CSV';
            } else {
                exportBtn.href = '/api/export/csv?period=weekly';
                exportBtn.textContent = '📥 Export Weekly CSV';
            }

            // Trigger chart resize if needed
            if (tabId === 'overview' && overviewChart) overviewChart.resize();
            if (tabId === 'today' && todayChart) todayChart.resize();
            if (tabId === 'yesterday' && yesterdayChart) yesterdayChart.resize();
            if (tabId === 'weekly' && weeklyChart) weeklyChart.resize();
            if (tabId === 'monthly' && monthlyChart) monthlyChart.resize();
            if (tabId === 'report' && reportChart) reportChart.resize();
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

        // Quick date picker chips
        function setQuickDate(daysAgo, btnElem) {
            document.querySelectorAll('.date-pill').forEach(b => b.classList.remove('active'));
            if (btnElem) btnElem.classList.add('active');

            const d = new Date();
            d.setDate(d.getDate() - daysAgo);
            const dateStr = d.toISOString().split('T')[0];
            
            document.getElementById('reportDatePicker').value = dateStr;
            handleDateChange(dateStr);
        }

        function handleDateChange(val) {
            selectedReportDate = val;
            document.getElementById('btn-report-export-csv').href = `/api/export/csv?period=${selectedReportDate}`;
            fetchCustomReport();
        }

        function handleMemberFilterChange(val) {
            selectedReportMember = val;
            const selectElem = document.getElementById('reportMemberFilter');
            const selectedText = selectElem.options[selectElem.selectedIndex].text;
            
            const badge = document.getElementById('reportFilteredMemberBadge');
            const nameSpan = document.getElementById('reportFilteredMemberName');
            
            if (val !== 'all') {
                badge.style.display = 'inline-flex';
                nameSpan.textContent = selectedText;
            } else {
                badge.style.display = 'none';
            }
            fetchCustomReport();
        }

        function clearMemberFilter() {
            document.getElementById('reportMemberFilter').value = 'all';
            handleMemberFilterChange('all');
        }

        async function syncChannelHistoryNow() {
            const btn = document.getElementById('btn-sync-channel');
            btn.classList.add('spinning');
            btn.innerHTML = '<span>🔄</span> Syncing...';
            try {
                const res = await fetch('/api/sync', { method: 'POST' });
                const data = await res.json();
                setTimeout(async () => {
                    await refreshStats();
                    await fetchCustomReport();
                    btn.classList.remove('spinning');
                    btn.innerHTML = '<span>✓</span> Synced!';
                    setTimeout(() => {
                        btn.innerHTML = '<span>🔄</span> Sync Discord Channel';
                    }, 2500);
                }, 1500);
            } catch (err) {
                btn.classList.remove('spinning');
                btn.innerHTML = '<span>⚠️</span> Error';
            }
        }

        // Fetch custom day stats via AJAX
        async function fetchCustomReport() {
            try {
                const url = `/api/stats/day?date=${selectedReportDate}&member=${selectedReportMember}`;
                const res = await fetch(url);
                if (!res.ok) return;
                const data = await res.json();

                // Update Headings
                document.getElementById('reportDateHeading').textContent = data.display_date;
                document.getElementById('rep-total-time').textContent = data.total_server_formatted;
                document.getElementById('rep-total-hrs').textContent = `${data.total_server_hours} total hours`;
                document.getElementById('rep-active-count').textContent = data.active_team_count;
                document.getElementById('rep-active-rate').textContent = `${data.active_rate_percentage}% participation (out of ${data.team_size})`;
                
                if (data.top_contributor) {
                    document.getElementById('rep-top-name').textContent = data.top_contributor.name;
                    document.getElementById('rep-top-time').textContent = data.top_contributor.total_formatted;
                } else {
                    document.getElementById('rep-top-name').textContent = 'None';
                    document.getElementById('rep-top-time').textContent = '-';
                }
                document.getElementById('rep-events-count').textContent = data.total_events_count;

                // Update Hourly Chart
                if (reportChart && data.hourly_distribution) {
                    reportChart.data.labels = data.hourly_distribution.map(h => h.hour);
                    reportChart.data.datasets[0].data = data.hourly_distribution.map(h => h.events_count);
                    reportChart.data.datasets[1].data = data.hourly_distribution.map(h => h.active_members_count);
                    reportChart.update();
                }

                // Update Table
                const tbody = document.getElementById('reportTableBody');
                if (tbody && data.members) {
                    tbody.innerHTML = data.members.map((mem, idx) => {
                        const rankClass = mem.rank === 1 ? 'rank-1' : (mem.rank === 2 ? 'rank-2' : (mem.rank === 3 ? 'rank-3' : 'rank-other'));
                        const avatarHtml = mem.avatar_url 
                            ? `<img src="${mem.avatar_url}" alt="${mem.name}" class="avatar">`
                            : `<div class="avatar">${(mem.name[0] || '?').toUpperCase()}</div>`;

                        return `
                        <tr>
                            <td><span class="leader-rank ${rankClass}">${mem.rank}</span></td>
                            <td>
                                <div class="user-cell">
                                    ${avatarHtml}
                                    <div class="user-names">
                                        <span class="user-name">${mem.name}</span>
                                        <span class="user-handle">${mem.username}</span>
                                    </div>
                                </div>
                            </td>
                            <td><span class="time-pill highlight">${mem.total_formatted}</span></td>
                            <td><strong>${mem.total_hours}</strong> hrs</td>
                            <td>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" style="width: ${mem.share_percentage}%;"></div>
                                </div>
                                <span style="font-weight: 600; font-size: 0.8rem;">${mem.share_percentage}%</span>
                            </td>
                            <td><span class="time-pill">${mem.events_count} events</span></td>
                        </tr>`;
                    }).join('') || '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No member data recorded for this date.</td></tr>';
                }

                // Update Timeline List
                const timelineContainer = document.getElementById('reportTimelineList');
                const countText = document.getElementById('timelineCountText');
                if (countText) countText.textContent = `${data.events ? data.events.length : 0} events logged`;

                if (timelineContainer) {
                    if (data.events && data.events.length > 0) {
                        timelineContainer.innerHTML = data.events.map(ev => `
                            <div class="timeline-item">
                                <div class="timeline-left">
                                    <span class="badge-status ${ev.type}">${ev.type}</span>
                                    <span class="timeline-time">${ev.time_str}</span>
                                    <span class="timeline-body"><strong>${ev.name}</strong>: ${ev.text}</span>
                                </div>
                                ${ev.duration_fmt ? `<span class="time-pill highlight">${ev.duration_fmt}</span>` : ''}
                            </div>
                        `).join('');
                    } else {
                        timelineContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1.5rem; text-align: center;">No status changes recorded in #online-report for this date.</div>';
                    }
                }

            } catch (err) {
                console.error('Error fetching custom report:', err);
            }
        }

        // Initialize Charts
        function initCharts() {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const isDark = currentTheme === 'dark';
            const gridColor = isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)';
            const textColor = isDark ? '#94a3b8' : '#64748b';

            Chart.defaults.color = textColor;
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
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } },
                        x: { grid: { display: false }, ticks: { color: textColor } }
                    }
                }
            });

            // 2. Today Hourly Chart
            const ctxTd = document.getElementById('todayHourlyChart').getContext('2d');
            todayChart = new Chart(ctxTd, {
                type: 'bar',
                data: {
                    labels: initialTodayHourly.map(h => h.hour),
                    datasets: [
                        {
                            label: 'Status Changes Logged',
                            data: initialTodayHourly.map(h => h.events_count),
                            backgroundColor: 'rgba(16, 185, 129, 0.7)',
                            borderColor: '#10b981',
                            borderWidth: 1,
                            borderRadius: 6
                        },
                        {
                            label: 'Active Members in Hour',
                            data: initialTodayHourly.map(h => h.active_members_count),
                            backgroundColor: 'rgba(99, 102, 241, 0.5)',
                            borderColor: '#6366f1',
                            borderWidth: 1,
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true, position: 'top' } },
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1, color: textColor }, grid: { color: gridColor } },
                        x: { grid: { display: false }, ticks: { color: textColor } }
                    }
                }
            });

            // 3. Yesterday Hourly Chart
            const ctxYd = document.getElementById('yesterdayHourlyChart').getContext('2d');
            yesterdayChart = new Chart(ctxYd, {
                type: 'bar',
                data: {
                    labels: initialYesterdayHourly.map(h => h.hour),
                    datasets: [
                        {
                            label: 'Status Changes Logged',
                            data: initialYesterdayHourly.map(h => h.events_count),
                            backgroundColor: 'rgba(245, 158, 11, 0.7)',
                            borderColor: '#f59e0b',
                            borderWidth: 1,
                            borderRadius: 6
                        },
                        {
                            label: 'Active Members in Hour',
                            data: initialYesterdayHourly.map(h => h.active_members_count),
                            backgroundColor: 'rgba(99, 102, 241, 0.5)',
                            borderColor: '#6366f1',
                            borderWidth: 1,
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true, position: 'top' } },
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1, color: textColor }, grid: { color: gridColor } },
                        x: { grid: { display: false }, ticks: { color: textColor } }
                    }
                }
            });

            // 4. Weekly Bar Chart
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
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } },
                        x: { grid: { display: false }, ticks: { color: textColor } }
                    }
                }
            });

            // 5. Monthly Line Trend Chart
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
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } },
                        x: { grid: { display: false }, ticks: { maxTicksLimit: 10, color: textColor } }
                    }
                }
            });

            // 6. Report Hourly Chart
            const ctxRep = document.getElementById('reportHourlyChart').getContext('2d');
            reportChart = new Chart(ctxRep, {
                type: 'bar',
                data: {
                    labels: initialTodayHourly.map(h => h.hour),
                    datasets: [
                        {
                            label: 'Status Changes Logged',
                            data: initialTodayHourly.map(h => h.events_count),
                            backgroundColor: 'rgba(99, 102, 241, 0.7)',
                            borderColor: '#6366f1',
                            borderWidth: 1,
                            borderRadius: 6
                        },
                        {
                            label: 'Active Members in Hour',
                            data: initialTodayHourly.map(h => h.active_members_count),
                            backgroundColor: 'rgba(16, 185, 129, 0.6)',
                            borderColor: '#10b981',
                            borderWidth: 1,
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true, position: 'top' } },
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1, color: textColor }, grid: { color: gridColor } },
                        x: { grid: { display: false }, ticks: { color: textColor } }
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
                document.getElementById('ov-yesterday-time').textContent = stats.yesterday.total_server_formatted;
                document.getElementById('ov-week-time').textContent = stats.weekly.total_server_formatted;
                document.getElementById('ov-week-avg').textContent = stats.weekly.avg_server_daily_formatted;
                document.getElementById('ov-month-time').textContent = stats.monthly.total_server_formatted;
                document.getElementById('ov-month-avg').textContent = stats.monthly.avg_server_daily_formatted;

                // Today KPIs
                document.getElementById('td-total-time').textContent = stats.today.total_server_formatted;
                document.getElementById('td-total-hrs').textContent = `${stats.today.total_server_hours} hours accumulated today`;
                if (stats.today.top_contributor) {
                    document.getElementById('td-top-name').textContent = stats.today.top_contributor.name;
                    document.getElementById('td-top-time').textContent = stats.today.top_contributor.total_formatted;
                }
                document.getElementById('td-part-rate').textContent = stats.today.active_rate_percentage + '%';
                document.getElementById('td-part-sub').textContent = `${stats.today.active_team_count} active out of ${stats.today.team_size}`;
                document.getElementById('td-events-count').textContent = stats.today.total_events_count;

                // Info bar
                document.getElementById('info-tz').textContent = stats.timezone;
                document.getElementById('info-server').textContent = stats.guild_name;
                document.getElementById('info-bot-user').textContent = stats.bot_user;
                document.getElementById('info-last-updated').textContent = stats.current_time;

                // Update Live Members Table
                const tbody = document.getElementById('membersBody');
                if (tbody && stats.members) {
                    tbody.innerHTML = stats.members.map(u => {
                        const avatarHtml = u.avatar_url 
                            ? `<img src="${u.avatar_url}" alt="${u.name}" class="avatar">`
                            : `<div class="avatar">${(u.name[0] || '?').toUpperCase()}</div>`;

                        return `
                        <tr class="member-row" data-name="${u.name.toLowerCase()}" data-username="${u.username.toLowerCase()}" data-status="${u.status}">
                            <td>
                                <div class="user-cell">
                                    ${avatarHtml}
                                    <div class="user-names">
                                        <span class="user-name">${u.name}</span>
                                        <span class="user-handle">${u.username}</span>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="badge-status ${u.status}">
                                    <span class="status-dot ${u.status}"></span>
                                    ${u.status}
                                </span>
                            </td>
                            <td><span class="time-pill highlight">${u.online_today_formatted}</span></td>
                            <td><span class="time-pill">${u.online_yesterday_formatted || '-'}</span></td>
                            <td><span class="time-pill">${u.online_week_formatted}</span></td>
                            <td><span class="time-pill">${u.online_month_formatted}</span></td>
                            <td><span class="time-pill">${u.current_session_formatted}</span></td>
                            <td style="color: var(--text-muted); font-size: 0.8rem;">${u.last_change_time}</td>
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
            const savedSetting = localStorage.getItem('statusbot_theme') || 'auto';
            updateThemeUI(savedSetting);
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

@app.route("/api/stats/day")
def api_stats_day():
    date_str = request.args.get("date", now().strftime("%Y-%m-%d"))
    member_filter = request.args.get("member", "all")
    
    current_time = now()
    all_stats = get_all_stats()
    live_today_map = {m["id"]: m["online_today_seconds"] for m in all_stats.get("members", [])}
    
    is_today = (date_str == current_time.strftime("%Y-%m-%d"))
    day_stats = stats_manager.get_day_stats(
        date_str=date_str,
        live_today_seconds=live_today_map if is_today else None,
        member_filter=member_filter
    )
    return jsonify(day_stats)

@app.route("/api/stats/weekly")
def api_stats_weekly():
    all_stats = get_all_stats()
    return jsonify(all_stats.get("weekly", {}))

@app.route("/api/stats/monthly")
def api_stats_monthly():
    all_stats = get_all_stats()
    return jsonify(all_stats.get("monthly", {}))

@app.route("/api/sync", methods=["GET", "POST"])
def api_sync():
    success = trigger_sync()
    return jsonify({"success": success, "message": "Channel sync triggered"})

@app.route("/api/export/csv")
def api_export_csv():
    period = request.args.get("period", "weekly").lower()
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
