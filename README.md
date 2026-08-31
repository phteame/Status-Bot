# Status Bot 🤖

A Discord presence tracking bot hosted with a modern Flask dashboard and real-time statistics monitoring.

## Features
- Tracks when members go **online / idle / dnd / offline**
- Real-time web dashboard displaying all server statistics, member activity, current sessions, and total online duration
- Live auto-refreshing dashboard with search & status filters
- Reports session duration and away time to Discord channels
- Daily stats auto-reset at midnight (Asia/Karachi timezone)
- REST API endpoint `/api/stats` for programmatic status retrieval
- Flask web dashboard keeps the host/project alive (e.g. Replit, Railway, Render)

## Setup

1. **Set Environment Variables**:

   | Key | Description |
   |-----|-------------|
   | `DISCORD_TOKEN` | Your Discord bot token |
   | `GUILD_ID` | The server (guild) ID to monitor |
   | `ONLINE_REPORT_CHANNEL_ID` | Channel ID where status updates are posted |

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
| `main.py` | Entry point — starts Flask app + bot background thread |
| `bot.py` | Discord bot logic & stats aggregation |
| `requirements.txt` | Python dependencies |
| `railway.toml` / `.replit` | Deployment configurations |

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Live stats dashboard with member activity & metrics |
| `GET /api/stats` | JSON endpoint with comprehensive server & member statistics |
| `GET /health` | Health check endpoint |
