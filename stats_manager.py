import os
import json
import threading
import io
import csv
from datetime import datetime, timedelta

SAVE_FILE = os.environ.get("HISTORY_SAVE_FILE", "presence_history.json")

class StatsManager:
    def __init__(self, filepath=SAVE_FILE):
        self.filepath = filepath
        self.lock = threading.Lock()
        self.data = {
            "daily_records": {},  # "YYYY-MM-DD": { "uid": seconds, ... }
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
            self.data["daily_records"][date_str][uid] = round(seconds)

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

    def get_period_stats(self, end_date, days=7, live_today_seconds=None):
        """
        Calculates aggregated stats for a date range ending at end_date for N days.
        live_today_seconds: optional dict of { uid: seconds } for current live session today.
        """
        with self.lock:
            daily_records = {k: dict(v) for k, v in self.data["daily_records"].items()}
            member_meta = {k: dict(v) for k, v in self.data["member_meta"].items()}

        today_str = end_date.strftime("%Y-%m-%d")
        if live_today_seconds:
            if today_str not in daily_records:
                daily_records[today_str] = {}
            for uid, secs in live_today_seconds.items():
                daily_records[today_str][str(uid)] = max(daily_records[today_str].get(str(uid), 0), round(secs))

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
        """Generates a downloadable CSV string for the given reporting period."""
        if end_date is None:
            end_date = datetime.now()
        
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
