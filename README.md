# Status Bot 🤖

A Discord presence tracking bot hosted with a modern Flask dashboard and real-time statistics monitoring.

## Features
- Tracks when members go **online / idle / dnd / offline**
- **Executive Reporting Dashboard**:
  - **Overview Analytics**: High-level KPIs, activity trend curves, and top performers podium.
  - **Weekly Report (7 Days)**: 7-day day-by-day activity bar chart, weekly hours, daily average, and weekly leaderboard.
  - **Monthly Report (30 Days)**: 30-day activity trend line, monthly totals, and member attendance consistency rates (% active days).
  - **Live Real-time Monitor**: Live status cards, current session timers, member search and filtering (Online, Idle, DnD, Offline).
  - **Theme Modes**: Support for **🌙 Dark**, **☀️ Light**, and **💻 Auto (System)** theme options with real-time Chart.js color synchronization.
- **Persistent Data Storage**: Automatically persists daily activity records to `presence_history.json` so data is preserved across days and server restarts.
- **1-Click CSV Export**: Download complete weekly or monthly attendance & hours reports as formatted CSV spreadsheets.
- **REST API Endpoints**: `/api/stats`, `/api/stats/weekly`, `/api/stats/monthly`, and `/api/export/csv`.
- **Discord Channel Updates**: Reports session duration and away time directly to Discord channels.
- Daily stats auto-reset at midnight (Asia/Karachi timezone).

## Setup

1. **Set Environment Variables**:

   | Key | Description |
   |-----|-------------|
   | `DISCORD_TOKEN` | Your Discord bot token |
   | `GUILD_ID` | The server (guild) ID to monitor |
   | `ONLINE_REPORT_CHANNEL_ID` | Channel ID where status updates are posted |
   | `HISTORY_SAVE_FILE` | (Optional) Path to persistent history JSON file (default: `presence_history.json`) |

2. **Run Application**:
   ```bash
   python main.py
   ```
   Or using Gunicorn:
   ```bash
   gunicorn main:app
   ```

## Keep Alive

The Flask web server on `/` serves a full stats dashboard. Use [UptimeRobot](https://uptimerobot.com/) to ping the URL every 5 minutes so the deployment stays active.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — starts Flask web dashboard + bot background thread |
| `bot.py` | Discord bot event tracking & presence session management |
| `stats_manager.py` | Thread-safe historical data persistence, aggregation (7d/30d), and CSV reporting |
| `requirements.txt` | Python dependencies |
| `railway.toml` / `.replit` | Deployment configurations |

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Executive stats dashboard with Overview, Weekly, Monthly, and Live tabs |
| `GET /api/stats` | JSON endpoint with live, weekly, and monthly server & member statistics |
| `GET /api/stats/weekly` | JSON endpoint for 7-day reporting breakdown |
| `GET /api/stats/monthly` | JSON endpoint for 30-day reporting breakdown |
| `GET /api/export/csv?period=weekly|monthly` | Download complete attendance & hours report in CSV format |
| `GET /health` | Health check endpoint |
