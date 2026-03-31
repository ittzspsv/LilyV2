import LilyLogging.sLilyLogging as LilyLogging
import LilyManagement.db.sLilyStaffDatabaseAccess as LSDA
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from typing import Tuple

from typing import Dict, Any

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict

import json

async def fetch_mod_stats(payload: dict):
    guild_id: int = payload.get("guild_id")
    moderator_id: int = payload.get("moderator_id")
    page_start: int = payload.get("page_start")
    page_end: int = payload.get("page_end")

    async with LilyLogging.mdb.execute("""
        WITH action_count_per_hour AS (
            SELECT 
                CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
                COUNT(*) AS action_count
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ?
            GROUP BY hour
        ),
        average_activity AS (
            SELECT AVG(action_count) AS avg_count
            FROM action_count_per_hour
        )
        SELECT hour, action_count
        FROM action_count_per_hour
        WHERE action_count >= (SELECT avg_count FROM average_activity)
        ORDER BY hour
    """, (guild_id, moderator_id)) as cursor:

        peak_hours = await cursor.fetchall()

    async with LilyLogging.mdb.execute("""
        SELECT 
            target_user_id,
            mod_type,
            reason,
            timestamp
        FROM modlogs
        WHERE guild_id = ? AND moderator_id = ?
        ORDER BY timestamp DESC
    """, (guild_id, moderator_id)) as cursor:

        rows = await cursor.fetchall()

    if not rows:
        return {
            "success": False,
            "message": "No Logs Found",
            "logs": [],
            "stats": {}
        }

    all_logs = []

    for row in rows:
        ts = int(datetime.fromisoformat(row[3]).replace(tzinfo=timezone.utc).timestamp())

        all_logs.append({
            "target_user_id": row[0],
            "mod_type": row[1].lower(),
            "reason": row[2],
            "timestamp": ts
        })

    clusters = []
    current_cluster = []
    last_hour = None

    for hour, count in peak_hours:
        if last_hour is None or hour == last_hour + 1:
            current_cluster.append((hour, count))
        else:
            clusters.append(current_cluster)
            current_cluster = [(hour, count)]

        last_hour = hour

    if current_cluster:
        clusters.append(current_cluster)

    best_cluster = max(clusters, key=lambda c: sum(x[1] for x in c)) if clusters else []

    if best_cluster:
        start_hour = best_cluster[0][0]
        end_hour = best_cluster[-1][0] + 1
    else:
        start_hour = None
        end_hour = None

    now = datetime.now(timezone.utc)

    if best_cluster:
        start_hour = best_cluster[0][0]

        start_dt = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)

        end_dt = start_dt + timedelta(hours=len(best_cluster))

        min_timestamp = int(start_dt.timestamp())
        max_timestamp = int(end_dt.timestamp())
    else:
        min_timestamp = None
        max_timestamp = None

    start_today = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    period_7d = int((now - timedelta(days=7)).timestamp())
    period_30d = int((now - timedelta(days=30)).timestamp())

    stats = defaultdict(lambda: {"today": 0, "7d": 0, "30d": 0, "total": 0})

    for log in all_logs:
        action = log["mod_type"]
        ts = log["timestamp"]

        stats[action]["total"] += 1

        if ts >= period_7d:
            stats[action]["7d"] += 1

        if ts >= period_30d:
            stats[action]["30d"] += 1

        if ts >= start_today:
            stats[action]["today"] += 1

    shown_logs = all_logs[page_start:page_end]

    return {
        "success": True,
        "logs": shown_logs,
        "total_logs": len(all_logs),
        "stats": stats,
        "now": now,
        "average_active_moderation_timestamp_range": [min_timestamp, max_timestamp]
    }

async def fetch_mod_logs(payload: dict):
    guild_id: int = payload.get("guild_id")
    target_user_id: int = payload.get("target_user_id")
    moderator_id: int = payload.get("moderator_id")
    mod_type: str = payload.get("mod_type", "all")
    page_start: int = payload.get("page_start")
    page_end: int = payload.get("page_end")

    DEFAULT_FETCH_LIMIT = 5

    count_query = "SELECT COUNT(*) FROM modlogs WHERE guild_id = ? AND target_user_id = ?"
    count_params = [guild_id, target_user_id]

    if moderator_id:
        count_query += " AND moderator_id = ?"
        count_params.append(moderator_id)

    if mod_type.lower() != "all":
        count_query += " AND lower(mod_type) = ?"
        count_params.append(mod_type.lower())

    async with LilyLogging.mdb.execute(count_query, tuple(count_params)) as cursor:
        row = await cursor.fetchone()

    total_count = row[0] if row else 0

    if total_count == 0:
        return {"success": False, "message": "No logs found"}

    type_query = "SELECT lower(mod_type), COUNT(*) FROM modlogs WHERE guild_id = ? AND target_user_id = ?"
    type_params = [guild_id, target_user_id]
    if moderator_id:
        type_query += " AND moderator_id = ?"
        type_params.append(moderator_id)
    type_query += " GROUP BY lower(mod_type)"

    async with LilyLogging.mdb.execute(type_query, tuple(type_params)) as cursor:
        rows = await cursor.fetchall()
    mod_type_counts = {row[0]: row[1] for row in rows}

    select_query = "SELECT mod_type, reason, timestamp, moderator_id FROM modlogs WHERE guild_id = ? AND target_user_id = ?"
    select_params = [guild_id, target_user_id]
    if moderator_id:
        select_query += " AND moderator_id = ?"
        select_params.append(moderator_id)
    if mod_type.lower() != "all":
        select_query += " AND lower(mod_type) = ?"
        select_params.append(mod_type.lower())
    select_query += " ORDER BY timestamp DESC"

    start = 0
    limit = DEFAULT_FETCH_LIMIT
    if page_start is not None:
        start = page_start
    if page_end is not None:
        limit = page_end - start

    select_query += " LIMIT ? OFFSET ?"
    select_params.extend([limit, start])

    async with LilyLogging.mdb.execute(select_query, tuple(select_params)) as cursor:
        rows = await cursor.fetchall()

    logs = [
        {
            "moderator_id": row[3],
            "mod_type": row[0].lower(),
            "reason": row[1],
            "timestamp": row[2],
        }
        for row in rows
    ]

    return {
        "success": True,
        "total_logs": total_count,
        "counts": mod_type_counts,
        "logs": logs
    }

async def fetch_moderation_leaderboard(guild_id: int, lb_type: str = "total") -> Dict:
    valid_types = {"total", "daily", "weekly", "monthly"}
    if lb_type not in valid_types:
        lb_type = "total"

    data = {}

    cursor = await LSDA.sdb.execute(
        "SELECT staff_id FROM staffs WHERE guild_id = ? AND retired = 0 AND on_loa = 0",
        (guild_id,)
    )
    rows = await cursor.fetchall()

    active_staff_id = tuple(row[0] for row in rows) or (-1,)

    cursor = await LilyLogging.mdb.execute(
        f"""
        SELECT 
            moderator_id,
            COUNT(*) AS total,
            COUNT(CASE 
                WHEN datetime(replace(substr(timestamp,1,19),'T',' ')) >= datetime('now','-1 day') 
                THEN 1 END) AS daily,
            COUNT(CASE 
                WHEN datetime(replace(substr(timestamp,1,19),'T',' ')) >= datetime('now','-7 days') 
                THEN 1 END) AS weekly,
            COUNT(CASE 
                WHEN datetime(replace(substr(timestamp,1,19),'T',' ')) >= datetime('now','-30 days') 
                THEN 1 END) AS monthly
        FROM modlogs
        WHERE moderator_id IN ({','.join(['?']*len(active_staff_id))})
          AND guild_id = ?
        GROUP BY moderator_id
        ORDER BY {lb_type} DESC
        """,
        (*active_staff_id, guild_id)
    )

    rows = await cursor.fetchall()

    data["moderator_statistics_leaderboard"] = []
    for moderator_id, total, daily, weekly, monthly in rows:
        stats = {
            "total": total,
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly
        }

        value = stats[lb_type]

        data["moderator_statistics_leaderboard"].append({
            "moderator_id": moderator_id,
            "ms": value
        })

    return data