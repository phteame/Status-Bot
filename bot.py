import discord
from datetime import datetime
import pytz
import os
import asyncio

# ===== CONFIG =====
TOKEN = os.environ.get("DISCORD_TOKEN", "")
GUILD_ID = int(os.environ.get("GUILD_ID", "0"))
REPORT_CHANNEL_ID = int(os.environ.get("ONLINE_REPORT_CHANNEL_ID", "0"))
TIMEZONE = pytz.timezone("Asia/Karachi")

# ===== INTENTS =====
intents = discord.Intents.default()
intents.presences = True
intents.members = True

bot = discord.Client(intents=intents)

# ===== STATE =====
online_since = {}            # uid -> datetime
last_status = {}             # uid -> status
last_change_time = {}        # uid -> datetime
online_seconds_today = {}    # uid -> seconds
last_reset_date = None
_bot_status = "starting"

# ===== UTILS =====
def now():
    return datetime.now(TIMEZONE)

def fmt(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

def get_status():
    """Returns the current bot status string for the web dashboard."""
    return _bot_status

async def send(msg):
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    if channel:
        try:
            await channel.send(msg)
        except discord.HTTPException:
            pass

# ===== DAILY RESET =====
def reset_if_new_day():
    global last_reset_date
    today = now().date()
    if last_reset_date != today:
        online_seconds_today.clear()
        online_since.clear()
        last_reset_date = today

# ===== EVENTS =====
@bot.event
async def on_ready():
    global _bot_status
    _bot_status = "running"
    print(f"Logged in as {bot.user}")
    reset_if_new_day()

@bot.event
async def on_presence_update(before, after):
    if after.bot:
        return

    reset_if_new_day()

    uid = after.id
    prev_status = str(before.status).lower()
    curr_status = str(after.status).lower()
    current_time = now()

    if prev_status == curr_status:
        return

    # ===== ONLINE -> ANYTHING ELSE =====
    if prev_status == "online":
        start = online_since.get(uid)
        if start:
            session = (current_time - start).total_seconds()
            online_seconds_today[uid] = online_seconds_today.get(uid, 0) + session
            online_since.pop(uid, None)

            await send(
                f"🔴 {after.display_name} went **{curr_status}** | "
                f"Online today: **{fmt(online_seconds_today[uid])}**"
            )

    # ===== ANYTHING -> ONLINE =====
    if curr_status == "online":
        online_since[uid] = current_time

        if uid in last_change_time:
            away = (current_time - last_change_time[uid]).total_seconds()
            await send(
                f"🟢 {after.display_name} is **online** again after **{fmt(away)}**"
            )
        else:
            await send(f"🟢 {after.display_name} is **online**")

    # ===== IDLE / DND / OFFLINE LOGGING =====
    if curr_status in ["idle", "dnd", "offline"] and prev_status != "online":
        await send(
            f"⚪ {after.display_name} is now **{curr_status}**"
        )

    last_status[uid] = curr_status
    last_change_time[uid] = current_time

# ===== RUN (called from main.py in a thread) =====
def run_bot():
    global _bot_status
    try:
        bot.run(TOKEN)
    except Exception as e:
        _bot_status = "error"
        print(f"Bot error: {e}")
