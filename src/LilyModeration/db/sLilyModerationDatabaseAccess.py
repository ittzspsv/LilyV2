import LilyLogging.sLilyLogging as LilyLogging
import LilyManagement.db.sLilyStaffDatabaseAccess as LSDA
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict


async def fetch_mod_stats(payload: dict):
    guild_id: int = payload.get("guild_id")
    moderator_id: int = payload.get("moderator_id")
    page_start: int = payload.get("page_start")
    page_end: int = payload.get("page_end")

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

    now = datetime.now(timezone.utc)

    start_today = int(
        now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    )

    start_week = int(
        (now - timedelta(days=now.weekday()))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )

    start_month = int(
        now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )

    stats = defaultdict(lambda: {
        "today": 0,
        "7d": 0,
        "30d": 0,
        "total": 0
    })

    for log in all_logs:
        action = log["mod_type"]
        ts = log["timestamp"]

        stats[action]["total"] += 1

        if ts >= start_today:
            stats[action]["today"] += 1

        if ts >= start_week:
            stats[action]["7d"] += 1

        if ts >= start_month:
            stats[action]["30d"] += 1

    shown_logs = all_logs[page_start:page_end]

    return {
        "success": True,
        "logs": shown_logs,
        "total_logs": len(all_logs),
        "stats": stats,
        "now": now
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

    select_query = "SELECT mod_type, reason, timestamp, moderator_id, id FROM modlogs WHERE guild_id = ? AND target_user_id = ?"
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
            "case_id" : row[4],
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
                WHEN datetime(replace(substr(timestamp,1,19),'T',' ')) 
                    >= datetime('now','start of day')
                THEN 1 END) AS daily,

            COUNT(CASE 
                WHEN datetime(replace(substr(timestamp,1,19),'T',' ')) 
                    >= datetime('now','weekday 1','start of day','-7 days')
                THEN 1 END) AS weekly,

            COUNT(CASE 
                WHEN datetime(replace(substr(timestamp,1,19),'T',' ')) 
                    >= datetime('now','start of month')
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

async def edit_case(payload: dict):
    staff_id: int = payload.get("staff_id")
    case_id: int = payload.get("case_id")
    case_statement: str = payload.get("case_statement")
    absolute: bool = payload.get("absolute", False)

    try:
        cursor = await LilyLogging.mdb.execute(
            "SELECT moderator_id FROM modlogs WHERE id = ?",
            (case_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            return {
                "success": False,
                "message": "Case not found."
            }

        if row[0] != staff_id and not absolute:
            return {
                "success": False,
                "message": f"This case cannot be modified. Only <@{row[0]}> can modify it."
            }

        await LilyLogging.mdb.execute(
            "UPDATE modlogs SET reason = ? WHERE id = ?",
            (case_statement, case_id)
        )
        await LilyLogging.mdb.commit()

        return {
            "success": True,
            "message": "Case edited successfully."
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"An error occurred: {e}"
        }
    
async def delete_case(payload: dict) -> Dict[str, Any]:
    case_id: int = payload.get("case_id")

    if not case_id:
        return {
            "success": False,
            "message": "Invalid case_id provided.",
            "case_id": case_id
        }

    try:
        cursor = await LilyLogging.mdb.execute(
            "DELETE FROM modlogs WHERE id = ?", 
            (case_id,)
        )
        await LilyLogging.mdb.commit()

        if cursor.rowcount == 0:
            return {
                "success": False,
                "message": "No case found with the given ID.",
                "case_id": case_id
            }

        return {
            "success": True,
            "message": "Case deleted successfully.",
            "case_id": case_id
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to delete case: {str(e)}",
            "case_id": case_id
        }

async def add_mod_queue(payload: dict):
    try:
        guild_id: int = payload.get("guild_id", 0)
        moderator_id: int = payload.get("moderator_id", 0)
        target_user_id: int = payload.get("target_user_id", 0)
        mod_type: str = payload.get("mod_type", "default")
        reason: str = payload.get("reason", "No reason has been provided!")
        message_source: str = payload.get("message_source", "")

        cursor = await LilyLogging.mdb.execute("""
            INSERT INTO mod_logs_queue (
                guild_id,
                moderator_id,
                target_user_id,
                mod_type,
                reason,
                timestamp,
                message_source
            ) VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        """, (
            guild_id,
            moderator_id,
            target_user_id,
            mod_type,
            reason,
            message_source
        ))

        await LilyLogging.mdb.commit()

        return {
            "success": True,
            "message": "Moderation action added to queue.",
            "data": {
                "insert_id": cursor.lastrowid,
                "guild_id": guild_id,
                "target_user_id": target_user_id,
                "mod_type": mod_type
            }
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to add moderation action: {str(e)}",
            "error": type(e).__name__
        }

async def clear_mod_queue(payload: dict):
    guild_id: int = payload.get("guild_id", 0)
    try:
        await LilyLogging.mdb.execute("DELETE FROM mod_logs_queue WHERE guild_id = ?", (guild_id,))
        await LilyLogging.mdb.commit()

        return {
            "success": True,
            "message": "Successfully cleared queue"
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to clear the queue"
        }

async def clear_mod_queue_particular(payload: dict):
    guild_id: int = payload.get("guild_id", 0)
    user_id: int = payload.get("user_id", 0)
    try:
        await LilyLogging.mdb.execute("DELETE FROM mod_logs_queue WHERE guild_id = ? AND target_user_id = ?", (guild_id, user_id))
        await LilyLogging.mdb.commit()

        return {
            "success": True,
            "message": "Successfully removed member from the queue"
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to remove the member from queue"
        }

async def fetch_mod_queue(payload: dict) -> dict:
    guild_id: int = payload.get("guild_id", 0)

    cursor = await LilyLogging.mdb.execute("""
        SELECT 
            mod_type,
            moderator_id,
            target_user_id,
            reason,
            message_source
        FROM mod_logs_queue
        WHERE guild_id = ?
    """, (guild_id,))

    rows = await cursor.fetchall()

    if not rows:
        return {
            "success": False,
            "message": "No moderation queue found for this guild.",
            "items": []
        }

    items = []
    for row in rows:
        items.append({
            "mod_type": row[0],
            "moderator_id": row[1],
            "target_user_id": row[2],
            "reason": row[3],
            "message_source": row[4]
        })

    return {
        "success": True,
        "message": "Successfully fetched queue.",
        "items": items
    }

async def get_mod_queue_entry(user_id: int, guild_id: int) -> dict:
    try:
        cursor = await LilyLogging.mdb.execute(
            "SELECT moderator_id FROM mod_logs_queue WHERE target_user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )

        row = await cursor.fetchone()
        await cursor.close()

        if row:
            return {
                "success": True,
                "moderator_id": row[0],
                "message": "Entry found."
            }

        return {
            "success": False,
            "moderator_id": None,
            "message": "No entry found for this user."
        }

    except Exception as e:
        return {
            "success": False,
            "moderator_id": None,
            "message": f"Error: {e}"
        }