# Status Bot 🤖

A Discord presence tracking bot hosted on Replit with a Flask keep-alive web server.

## Features
- Tracks when members go **online / idle / dnd / offline**
- Reports session duration and away time
- Daily stats auto-reset at midnight (Asia/Karachi timezone)
- Flask web dashboard keeps the Replit project alive

## Setup on Replit

1. **Import this project** into Replit (or create a new Python Repl and upload these files).

2. **Set Secrets** (Environment Variables) in the Replit Secrets tab:

   | Key | Description |
   |-----|-------------|
   | `DISCORD_TOKEN` | Your Discord bot token |
   | `GUILD_ID` | The server (guild) ID to monitor |
   | `ONLINE_REPORT_CHANNEL_ID` | Channel ID where status updates are posted |

3. **Click Run** — the Flask server starts on port 5000 and the Discord bot connects in the background.

## Keep Alive

The Flask web server on `/` serves a small dashboard. Use [UptimeRobot](https://uptimerobot.com/) to ping the Replit URL every 5 minutes so the project stays awake.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — starts Flask + bot thread |
| `bot.py` | Discord bot logic (presence tracking) |
| `requirements.txt` | Python dependencies |
| `.replit` | Replit run configuration |

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Web dashboard with bot status |
| `GET /health` | JSON health check |
