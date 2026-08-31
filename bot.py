import discord
from datetime import datetime
import pytz
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

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

def get_all_stats():
    """Compiles and returns a comprehensive status & presence dictionary."""
    reset_if_new_day()
    current_time = now()

    guild = None
    if bot.is_ready():
        if GUILD_ID:
            guild = bot.get_guild(GUILD_ID)
        if not guild and bot.guilds:
            guild = bot.guilds[0]

    members_map = {}
    
    if guild:
        for member in guild.members:
            if member.bot:
                continue
            uid = member.id
            status = str(member.status).lower()
            avatar_url = str(member.display_avatar.url) if member.display_avatar else None
            members_map[uid] = {
                "id": str(uid),
                "name": member.display_name,
                "username": str(member),
                "avatar_url": avatar_url,
                "status": status,
            }

    # Include any tracked UIDs that might not be in guild.members list
    all_tracked_uids = set(members_map.keys()) | set(online_seconds_today.keys()) | set(last_status.keys()) | set(online_since.keys())

    members_list = []
    total_online_secs_sum = 0
    online_count = 0
    idle_count = 0
    dnd_count = 0
    offline_count = 0

    for uid in all_tracked_uids:
        m_info = members_map.get(uid, {
            "id": str(uid),
            "name": f"User {uid}",
            "username": f"User {uid}",
            "avatar_url": None,
            "status": last_status.get(uid, "offline"),
        })

        status = last_status.get(uid, m_info["status"])
        m_info["status"] = status

        today_secs = online_seconds_today.get(uid, 0)
        curr_session_secs = 0

        start_time = online_since.get(uid)
        if status == "online" and start_time:
            curr_session_secs = max(0, (current_time - start_time).total_seconds())
            today_secs += curr_session_secs

        total_online_secs_sum += today_secs

        last_change = last_change_time.get(uid)

        m_info["online_today_seconds"] = round(today_secs)
        m_info["online_today_formatted"] = fmt(today_secs)
        m_info["current_session_seconds"] = round(curr_session_secs)
        m_info["current_session_formatted"] = fmt(curr_session_secs) if curr_session_secs > 0 else "-"
        m_info["last_change_time"] = last_change.strftime("%Y-%m-%d %H:%M:%S %Z") if last_change else "-"

        if status == "online":
            online_count += 1
        elif status == "idle":
            idle_count += 1
        elif status == "dnd":
            dnd_count += 1
        else:
            offline_count += 1

        members_list.append(m_info)

    status_order = {"online": 0, "idle": 1, "dnd": 2, "offline": 3, "unknown": 4}
    members_list.sort(key=lambda x: (status_order.get(x["status"], 99), -x["online_today_seconds"], x["name"].lower()))

    return {
        "bot_status": _bot_status,
        "bot_user": str(bot.user) if bot.user else "Not logged in",
        "guild_name": guild.name if guild else ("Monitored Server" if GUILD_ID else "Status Bot Server"),
        "guild_id": str(GUILD_ID) if GUILD_ID else "-",
        "report_channel_id": str(REPORT_CHANNEL_ID) if REPORT_CHANNEL_ID else "-",
        "timezone": "Asia/Karachi",
        "last_reset_date": str(last_reset_date) if last_reset_date else str(current_time.date()),
        "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "total_members": len(members_list),
        "online_count": online_count,
        "idle_count": idle_count,
        "dnd_count": dnd_count,
        "offline_count": offline_count,
        "total_server_online_seconds": round(total_online_secs_sum),
        "total_server_online_fmt": fmt(total_online_secs_sum),
        "members": members_list
    }


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
