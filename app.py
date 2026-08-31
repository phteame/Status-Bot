import discord
from datetime import datetime, date
import pytz
import os
import asyncio
import json

# ===== CONFIG =====
TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
REPORT_CHANNEL_ID = int(os.environ["ONLINE_REPORT_CHANNEL_ID"])
TIMEZONE = pytz.timezone("Asia/Karachi")
SAVE_FILE = "presence_tracking.json"

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

# ===== UTILS =====
def now():
    return datetime.now(TIMEZONE)

def fmt(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

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

# ===== START =====
bot.run(TOKEN)
