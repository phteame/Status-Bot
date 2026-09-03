import os
import json
import threading
import io
import csv
import re
from datetime import datetime, timedelta

SAVE_FILE = os.environ.get("HISTORY_SAVE_FILE", "presence_history.json")

def parse_duration_str(text):
    """
    Parses strings like '2h 15m 30s', '45m 12s', '1h', '30s', '2h 15m' into total seconds.
    """
    if not text:
        return 0
    
    # Strip markdown and whitespace
    clean = re.sub(r'[*_`]', '', str(text)).strip()
    
    hours = 0
    minutes = 0
    seconds = 0
    
    h_match = re.search(r'(\d+)\s*h(?:ours?|rs?)?', clean, re.IGNORECASE)
    if h_match:
        hours = int(h_match.group(1))
        
    m_match = re.search(r'(\d+)\s*m(?:inutes?|ins?)?', clean, re.IGNORECASE)
    if m_match:
        minutes = int(m_match.group(1))
        
    s_match = re.search(r'(\d+)\s*s(?:econds?|ecs?)?', clean, re.IGNORECASE)
    if s_match:
        seconds = int(s_match.group(1))
        
    # If no standard h/m/s pattern matched, check if it's plain numbers e.g. "120"
    if not h_match and not m_match and not s_match:
        if clean.isdigit():
            return int(clean)
        # Check colon format "01:23:45"
        parts = clean.split(':')
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2 and all(p.isdigit() for p in parts):
            return int(parts[0]) * 60 + int(parts[1])

    return hours * 3600 + minutes * 60 + seconds

class StatsManager:
    def __init__(self, filepath=SAVE_FILE):
        self.filepath = filepath
        self.lock = threading.Lock()
        self.data = {
            "daily_records": {},  # "YYYY-MM-DD": { "uid": seconds, ... }
            "daily_events": {},   # "YYYY-MM-DD": [ { timestamp, time_str, hour, uid, name, type, text, duration_sec } ]
            "member_meta": {}     # "uid": { "name": str, "username": str, "avatar_url": str, "last_seen": str }
        }
        self.load()

    def load(self):
        with self.lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            self.data["daily_records"] = loaded.get("daily_records", {})
                            self.data["daily_events"] = loaded.get("daily_events", {})
                            self.data["member_meta"] = loaded.get("member_meta", {})
                except Exception as e:
                    print(f"[StatsManager] Error loading {self.filepath}: {e}")

    def save(self):
        with self.lock:
            try:
                temp_path = self.filepath + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
                if os.path.exists(temp_path):
                    if os.path.exists(self.filepath):
                        os.replace(temp_path, self.filepath)
                    else:
                        os.rename(temp_path, self.filepath)
            except Exception as e:
                print(f"[StatsManager] Error saving {self.filepath}: {e}")

    def update_member_meta(self, uid, name=None, username=None, avatar_url=None, last_seen=None):
        uid = str(uid)
        with self.lock:
            if uid not in self.data["member_meta"]:
                self.data["member_meta"][uid] = {
                    "name": name or f"User {uid}",
                    "username": username or f"user_{uid}",
                    "avatar_url": avatar_url,
                    "last_seen": last_seen
                }
            else:
                meta = self.data["member_meta"][uid]
                if name: meta["name"] = name
                if username: meta["username"] = username
                if avatar_url is not None: meta["avatar_url"] = avatar_url
                if last_seen: meta["last_seen"] = last_seen

    def set_daily_seconds(self, date_str, uid, seconds):
        uid = str(uid)
        with self.lock:
            if date_str not in self.data["daily_records"]:
                self.data["daily_records"][date_str] = {}
            self.data["daily_records"][date_str][uid] = max(
                self.data["daily_records"][date_str].get(uid, 0),
                round(seconds)
            )

    def add_daily_seconds(self, date_str, uid, seconds):
        uid = str(uid)
        with self.lock:
            if date_str not in self.data["daily_records"]:
                self.data["daily_records"][date_str] = {}
            prev = self.data["daily_records"][date_str].get(uid, 0)
            self.data["daily_records"][date_str][uid] = round(prev + seconds)

    def get_daily_seconds(self, date_str, uid):
        uid = str(uid)
        with self.lock:
            day_data = self.data["daily_records"].get(date_str, {})
            return day_data.get(uid, 0)

    def add_event(self, date_str, timestamp_str, time_str, hour, uid, name, event_type, text, duration_sec=0):
        """Records an event in the timeline for the given date, avoiding exact duplicates."""
        uid = str(uid)
        with self.lock:
            if "daily_events" not in self.data:
                self.data["daily_events"] = {}
            if date_str not in self.data["daily_events"]:
                self.data["daily_events"][date_str] = []
            
            events = self.data["daily_events"][date_str]
            # Avoid duplicate if text and time_str already match
            for ev in events:
                if ev.get("time_str") == time_str and ev.get("text") == text:
                    return
            
            events.append({
                "timestamp": timestamp_str,
                "time_str": time_str,
                "hour": int(hour),
                "uid": uid,
                "name": name,
                "type": event_type,
                "text": text,
                "duration_sec": round(duration_sec),
                "duration_fmt": self.fmt_duration(duration_sec) if duration_sec > 0 else ""
            })

    def get_day_stats(self, date_str, live_today_seconds=None, member_filter=None):
        """
        Calculates comprehensive single-day stats for date_str (format 'YYYY-MM-DD').
        Includes KPI metrics, hourly distribution, member breakdown & ranking, and event timeline.
        """
        with self.lock:
            daily_records = {k: dict(v) for k, v in self.data.get("daily_records", {}).items()}
            daily_events = {k: list(v) for k, v in self.data.get("daily_events", {}).items()}
            member_meta = {k: dict(v) for k, v in self.data.get("member_meta", {}).items()}

        try:
            d_obj = datetime.strptime(date_str, "%Y-%m-%d")
            display_date = d_obj.strftime("%A, %b %d, %Y")
            day_name = d_obj.strftime("%a")
        except Exception:
            display_date = date_str
            day_name = ""

        # Apply live session seconds if querying today
        if live_today_seconds:
            if date_str not in daily_records:
                daily_records[date_str] = {}
            for uid, secs in live_today_seconds.items():
                daily_records[date_str][str(uid)] = max(
                    daily_records[date_str].get(str(uid), 0),
                    round(secs)
                )

        day_record = daily_records.get(date_str, {})
        day_events_raw = daily_events.get(date_str, [])

        # Filter events if member_filter is specified
        if member_filter and member_filter != "all":
            day_events = [ev for ev in day_events_raw if ev.get("uid") == str(member_filter) or ev.get("name") == str(member_filter)]
        else:
            day_events = day_events_raw

        # Sort events by timestamp descending (newest first)
        day_events = sorted(day_events, key=lambda x: x.get("timestamp", ""), reverse=True)

        # 24-Hour Distribution (00:00 to 23:00)
        hourly_map = {h: {"events_count": 0, "active_uids": set()} for h in range(24)}
        for ev in day_events_raw:
            h = ev.get("hour", 0)
            if 0 <= h <= 23:
                hourly_map[h]["events_count"] += 1
                if ev.get("uid"):
                    hourly_map[h]["active_uids"].add(ev.get("uid"))

        hourly_distribution = []
        for h in range(24):
            time_label = f"{h:02d}:00"
            hourly_distribution.append({
                "hour": time_label,
                "hour_num": h,
                "events_count": hourly_map[h]["events_count"],
                "active_members_count": len(hourly_map[h]["active_uids"])
            })

        # Member list & ranking
        all_uids = set(member_meta.keys()) | set(day_record.keys())
        members_summary = []
        total_server_seconds = 0

        for uid in all_uids:
            secs = day_record.get(str(uid), 0)
            total_server_seconds += secs

            meta = member_meta.get(str(uid), {
                "name": f"User {uid}",
                "username": f"user_{uid}",
                "avatar_url": None,
                "last_seen": "-"
            })

            # Count events for this user on this day
            user_ev_count = sum(1 for ev in day_events_raw if ev.get("uid") == str(uid))

            members_summary.append({
                "id": str(uid),
                "name": meta.get("name", f"User {uid}"),
                "username": meta.get("username", f"user_{uid}"),
                "avatar_url": meta.get("avatar_url"),
                "last_seen": meta.get("last_seen", "-"),
                "total_seconds": round(secs),
                "total_hours": round(secs / 3600, 2),
                "total_formatted": self.fmt_duration(secs),
                "events_count": user_ev_count,
                "is_active": secs > 0 or user_ev_count > 0
            })

        # Sort members by total time descending, then events count
        members_summary.sort(key=lambda x: (-x["total_seconds"], -x["events_count"], x["name"].lower()))

        # Assign rank
        for idx, m in enumerate(members_summary):
            m["rank"] = idx + 1
            if total_server_seconds > 0:
                m["share_percentage"] = round((m["total_seconds"] / total_server_seconds) * 100, 1)
            else:
                m["share_percentage"] = 0

        # Filter members summary if filter requested
        if member_filter and member_filter != "all":
            displayed_members = [m for m in members_summary if m["id"] == str(member_filter) or m["name"] == str(member_filter)]
        else:
            displayed_members = members_summary

        active_team_count = sum(1 for m in members_summary if m["total_seconds"] > 0 or m["events_count"] > 0)
        team_size = len(members_summary)
        active_rate = round((active_team_count / team_size) * 100, 1) if team_size > 0 else 0
        top_contributor = members_summary[0] if members_summary and members_summary[0]["total_seconds"] > 0 else None

        return {
            "date": date_str,
            "day_name": day_name,
            "display_date": display_date,
            "total_server_seconds": round(total_server_seconds),
            "total_server_hours": round(total_server_seconds / 3600, 2),
            "total_server_formatted": self.fmt_duration(total_server_seconds),
            "active_team_count": active_team_count,
            "team_size": team_size,
            "active_rate_percentage": active_rate,
            "total_events_count": len(day_events_raw),
            "top_contributor": top_contributor,
            "hourly_distribution": hourly_distribution,
            "members": displayed_members,
            "all_members_count": len(members_summary),
            "events": day_events
        }

    def get_period_stats(self, end_date, days=7, live_today_seconds=None):
        """
        Calculates aggregated stats for a date range ending at end_date for N days.
        live_today_seconds: optional dict of { uid: seconds } for current live session today.
        """
        with self.lock:
            daily_records = {k: dict(v) for k, v in self.data.get("daily_records", {}).items()}
            member_meta = {k: dict(v) for k, v in self.data.get("member_meta", {}).items()}

        today_str = end_date.strftime("%Y-%m-%d")
        if live_today_seconds:
            if today_str not in daily_records:
                daily_records[today_str] = {}
            for uid, secs in live_today_seconds.items():
                daily_records[today_str][str(uid)] = max(
                    daily_records[today_str].get(str(uid), 0),
                    round(secs)
                )

        date_list = [(end_date - timedelta(days=i)) for i in range(days - 1, -1, -1)]
        date_strs = [d.strftime("%Y-%m-%d") for d in date_list]

        # Daily Trend Data
        daily_trends = []
        member_totals = {}       # uid -> total_seconds
        member_active_days = {}   # uid -> count of days with > 0 seconds

        total_server_seconds = 0

        for d, d_str in zip(date_list, date_strs):
            day_record = daily_records.get(d_str, {})
            day_server_secs = 0
            day_active_users = 0

            for uid, secs in day_record.items():
                if secs > 0:
                    day_server_secs += secs
                    day_active_users += 1
                    member_totals[uid] = member_totals.get(uid, 0) + secs
                    member_active_days[uid] = member_active_days.get(uid, 0) + 1

            total_server_seconds += day_server_secs
            daily_trends.append({
                "date": d_str,
                "day_name": d.strftime("%a"),
                "display_date": d.strftime("%b %d"),
                "total_seconds": round(day_server_secs),
                "total_hours": round(day_server_secs / 3600, 2),
                "active_members_count": day_active_users
            })

        # Compile member ranking & stats
        all_uids = set(member_meta.keys()) | set(member_totals.keys())
        members_summary = []

        for uid in all_uids:
            meta = member_meta.get(uid, {
                "name": f"User {uid}",
                "username": f"user_{uid}",
                "avatar_url": None,
                "last_seen": "-"
            })
            tot_secs = member_totals.get(uid, 0)
            act_days = member_active_days.get(uid, 0)
            avg_daily_secs = round(tot_secs / days) if days > 0 else 0

            members_summary.append({
                "id": str(uid),
                "name": meta.get("name", f"User {uid}"),
                "username": meta.get("username", f"user_{uid}"),
                "avatar_url": meta.get("avatar_url"),
                "last_seen": meta.get("last_seen", "-"),
                "total_seconds": round(tot_secs),
                "total_hours": round(tot_secs / 3600, 2),
                "total_formatted": self.fmt_duration(tot_secs),
                "active_days": act_days,
                "active_days_percentage": round((act_days / days) * 100, 1) if days > 0 else 0,
                "avg_daily_seconds": avg_daily_secs,
                "avg_daily_formatted": self.fmt_duration(avg_daily_secs)
            })

        # Sort members by total time descending
        members_summary.sort(key=lambda x: -x["total_seconds"])

        # Add rank
        for idx, m in enumerate(members_summary):
            m["rank"] = idx + 1

        avg_server_daily_secs = round(total_server_seconds / days) if days > 0 else 0
        top_contributor = members_summary[0] if members_summary and members_summary[0]["total_seconds"] > 0 else None

        active_team_count = sum(1 for m in members_summary if m["total_seconds"] > 0)
        team_size = len(members_summary)
        active_rate = round((active_team_count / team_size) * 100, 1) if team_size > 0 else 0

        return {
            "period_days": days,
            "start_date": date_strs[0] if date_strs else "",
            "end_date": date_strs[-1] if date_strs else "",
            "total_server_seconds": round(total_server_seconds),
            "total_server_hours": round(total_server_seconds / 3600, 2),
            "total_server_formatted": self.fmt_duration(total_server_seconds),
            "avg_server_daily_seconds": avg_server_daily_secs,
            "avg_server_daily_hours": round(avg_server_daily_secs / 3600, 2),
            "avg_server_daily_formatted": self.fmt_duration(avg_server_daily_secs),
            "active_team_count": active_team_count,
            "team_size": team_size,
            "active_rate_percentage": active_rate,
            "top_contributor": top_contributor,
            "daily_trends": daily_trends,
            "members": members_summary
        }

    def generate_csv_report(self, period_type="weekly", end_date=None, live_today_seconds=None):
        """
        Generates a downloadable CSV string for the given reporting period or single date.
        period_type can be 'today', 'yesterday', 'weekly', 'monthly', or 'YYYY-MM-DD'.
        """
        if end_date is None:
            end_date = datetime.now()

        # Handle Single-Day CSV Export
        if period_type in ["today", "yesterday"] or re.match(r'^\d{4}-\d{2}-\d{2}$', period_type):
            if period_type == "today":
                target_date_str = end_date.strftime("%Y-%m-%d")
            elif period_type == "yesterday":
                target_date_str = (end_date - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                target_date_str = period_type

            day_stats = self.get_day_stats(target_date_str, live_today_seconds=live_today_seconds)

            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow([f"Discord Presence Daily Report - {day_stats['display_date']}"])
            writer.writerow(["Date", day_stats["date"]])
            writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(["Total Server Online Time", day_stats["total_server_formatted"], f"({day_stats['total_server_hours']} hours)"])
            writer.writerow(["Active Team Participation", f"{day_stats['active_team_count']} / {day_stats['team_size']} ({day_stats['active_rate_percentage']}%)"])
            writer.writerow(["Total Status Events", day_stats["total_events_count"]])
            writer.writerow([])

            # Member Table
            writer.writerow(["--- MEMBER PERFORMANCE & ATTENDANCE ---"])
            writer.writerow(["Rank", "Member Name", "Username", "Discord ID", "Total Online Time", "Total Hours", "Share %", "Status Events Count", "Last Seen"])
            for m in day_stats["members"]:
                writer.writerow([
                    m["rank"],
                    m["name"],
                    m["username"],
                    m["id"],
                    m["total_formatted"],
                    m["total_hours"],
                    f"{m.get('share_percentage', 0)}%",
                    m["events_count"],
                    m["last_seen"]
                ])
            writer.writerow([])

            # Events Log
            if day_stats["events"]:
                writer.writerow(["--- STATUS EVENTS TIMELINE ---"])
                writer.writerow(["Time", "Member", "Status Event", "Duration Recorded", "Raw Message"])
                for ev in day_stats["events"]:
                    writer.writerow([
                        ev.get("time_str", ""),
                        ev.get("name", ""),
                        ev.get("type", "").upper(),
                        ev.get("duration_fmt", "-"),
                        ev.get("text", "")
                    ])

            return output.getvalue()

        # Multi-day period CSV Export (weekly / monthly)
        days = 7 if period_type == "weekly" else 30
        stats = self.get_period_stats(end_date=end_date, days=days, live_today_seconds=live_today_seconds)

        output = io.StringIO()
        writer = csv.writer(output)

        title = "Weekly Discord Presence Report" if period_type == "weekly" else "Monthly Discord Presence Report"
        writer.writerow([title])
        writer.writerow(["Period Range", f"{stats['start_date']} to {stats['end_date']} ({days} Days)"])
        writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["Total Server Online Time", stats["total_server_formatted"], f"({stats['total_server_hours']} hours)"])
        writer.writerow(["Average Daily Server Time", stats["avg_server_daily_formatted"]])
        writer.writerow(["Active Team Participation", f"{stats['active_team_count']} / {stats['team_size']} ({stats['active_rate_percentage']}%)"])
        writer.writerow([])

        # Daily Trend Summary
        writer.writerow(["--- DAILY ACTIVITY BREAKDOWN ---"])
        writer.writerow(["Date", "Day", "Total Online Hours", "Active Members"])
        for day in stats["daily_trends"]:
            writer.writerow([day["date"], day["day_name"], day["total_hours"], day["active_members_count"]])
        writer.writerow([])

        # Member Rankings Table
        writer.writerow(["--- MEMBER PERFORMANCE & ATTENDANCE ---"])
        writer.writerow(["Rank", "Member Name", "Username", "Discord ID", "Total Online Time", "Total Hours", "Active Days", "Attendance Rate (%)", "Avg Daily Time", "Last Seen"])
        
        for m in stats["members"]:
            writer.writerow([
                m["rank"],
                m["name"],
                m["username"],
                m["id"],
                m["total_formatted"],
                m["total_hours"],
                f"{m['active_days']}/{days}",
                f"{m['active_days_percentage']}%",
                m["avg_daily_formatted"],
                m["last_seen"]
            ])

        return output.getvalue()

    @staticmethod
    def fmt_duration(seconds):
        seconds = int(seconds or 0)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"

# Global singleton
stats_manager = StatsManager()
