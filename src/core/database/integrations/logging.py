from ..sLilyDatabaseAccess import LilyDatabaseAccess
from ..integrations.bot_globals import BotGlobalsDatabaseAccess

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

import pytz
import json
import aiohttp

""" data classes"""
@dataclass
class BanLimitStatus:
    exceeded: bool
    max_limit: int
    recent_ban_count: int
    remaining_count: int
    remaining_time: Optional[str]         
    cooldown_breakdown: Optional[str] 

class LoggingDatabase(LilyDatabaseAccess):
    def __init__(self) -> None:
        super().__init__()

        self.cache: dict[str, dict] = {}
        self.bot_db: Optional[BotGlobalsDatabaseAccess] = None
        self._cache_ready = False

    async def load_cache(self) -> None:
        self._cache_ready = True

    async def write_log(self, guild_id: int ,user_id: int, log_txt: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        await self.execute("""
            INSERT INTO botlogs (guild_id, user_id, timestamp, log)
            VALUES (?, ?, ?, ?)
        """, (guild_id, user_id, timestamp, log_txt))

    async def log_moderation_action(
            self,
            guild_id: int,
            moderator_id: int,
            target_user_id: int,
            mod_type: str,
            reason: str = "No reason provided"
        ) -> Optional[int]:
        timestamp = datetime.now(pytz.utc).isoformat()
        row_id = await self.execute("""
            INSERT INTO modlogs 
                (guild_id, moderator_id, target_user_id, mod_type, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            guild_id,
            moderator_id,
            target_user_id,
            mod_type.lower(),
            reason,
            timestamp
        ))

        return row_id

    async def log_proof_action(
        self,
        case_id: int,
        proofs_reference: int,
        author: int
    ):
        await self.execute("""
        INSERT INTO proofs 
            (case_id, proof_reference, author)
        VALUES (?, ?, ?)""", (case_id, proofs_reference, author))

    async def retrieve_proofs(
        self,
        case_id: int
    ) -> list[int]:
        rows = await self.fetch_all(
            """
            SELECT proof_reference
            FROM proofs
            WHERE case_id = ?
            """,
            (case_id,)
        )

        return [row[0] for row in rows]

    """ Moderation Actions """
    async def get_ban_limit_status(
        self,
        guild_id: int,
        moderator_id: int,
        moderator_role_ids: list[int]
    ) -> BanLimitStatus:
        _default = BanLimitStatus(
            exceeded=True,
            max_limit=0,
            recent_ban_count=0,
            remaining_count=0,
            remaining_time=None,
            cooldown_breakdown=None,
        )

        if self.bot_db is None:
            return _default

        if not moderator_role_ids:
            return _default

        now = datetime.now(pytz.utc)
        past_24h = (now - timedelta(hours=24)).isoformat()

        try:
            max_limit = self.bot_db.get_ban_limit(guild_id, moderator_role_ids)
            if max_limit == 0:
                return _default

            bans = await self.fetch_all(
                """
                SELECT timestamp
                FROM   modlogs
                WHERE  guild_id = ?
                AND  moderator_id = ?
                AND  mod_type     IN ('ban', 'quarantine')
                AND  timestamp    >= ?
                ORDER BY timestamp ASC
                """,
                (guild_id, moderator_id, past_24h),
            )

            bans = list(bans)
            recent_ban_count = len(bans)
            exceeded = recent_ban_count >= max_limit
            remaining_count = max(0, max_limit - recent_ban_count)

            remaining_time: Optional[str] = None
            cooldown_breakdown: Optional[str] = None

            if exceeded and bans:
                trigger_ts = datetime.fromisoformat(bans[max_limit - 1][0])
                cooldown_end = trigger_ts + timedelta(hours=24)

                if cooldown_end > now:
                    remaining = cooldown_end - now
                    hours, rem = divmod(int(remaining.total_seconds()), 3600)
                    minutes = rem // 60
                    remaining_time = f"You can ban again in {hours}h {minutes}m"

                lines = []
                for index, (ts,) in enumerate(bans, start=1):
                    ban_time = datetime.fromisoformat(ts)
                    cooldown_end = ban_time + timedelta(hours=24)
                    if cooldown_end > now:
                        remaining = cooldown_end - now
                        hours, rem = divmod(int(remaining.total_seconds()), 3600)
                        minutes = rem // 60
                        lines.append(f"{index}. Recovery in **{hours}h {minutes}m**")

                if lines:
                    cooldown_breakdown = "**Ban's Cooldown State.**\n" + "\n".join(lines)

            return BanLimitStatus(
                exceeded=exceeded,
                max_limit=max_limit,
                recent_ban_count=recent_ban_count,
                remaining_count=remaining_count,
                remaining_time=remaining_time,
                cooldown_breakdown=cooldown_breakdown,
            )

        except Exception as e:
            print("Error in get_ban_limit_status:", e)
            return _default
        
    async def get_mod_queue_entry(self, user_id: int, guild_id: int) -> dict:
        try:
            row = await self.fetch_one(
                "SELECT moderator_id FROM mod_logs_queue WHERE target_user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )

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
        
    async def add_mod_queue(
            self, 
            guild_id: int, 
            moderator_id: int, 
            target_user_id: int, 
            mod_type: str, 
            reason: str, 
            message_source: str
        ) -> Dict[str, Any]:
        try:
            await self.execute("""
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

            return {
                "success": True,
                "message": "Moderation action added to queue.",
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add moderation action: {str(e)}",
                "error": type(e).__name__
            }
        
    async def fetch_mod_stats(
            self, 
            guild_id: int, 
            moderator_id: int, 
            page_start: int, 
            page_end: int
        ) -> Dict[str, Any]:
        rows = await self.fetch_all("""
            SELECT 
                target_user_id,
                mod_type,
                reason,
                timestamp
            FROM modlogs
            WHERE guild_id = ? AND moderator_id = ?
            ORDER BY timestamp DESC
        """, (guild_id, moderator_id))


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
    
    async def fetch_mod_logs(
        self,
        guild_id: int,
        target_user_id: int,
        moderator_id: int,
        mod_type: str = "all",
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> Dict[str, Any]:
        DEFAULT_FETCH_LIMIT = 5

        base_condition = "WHERE guild_id = ? AND target_user_id = ?"
        base_params: list = [guild_id, target_user_id]

        if moderator_id:
            base_condition += " AND moderator_id = ?"
            base_params.append(moderator_id)

        normalized_type = mod_type.lower()
        type_filter = normalized_type != "all"

        count_params = base_params.copy()
        count_query = f"SELECT COUNT(*) FROM modlogs {base_condition}"

        if type_filter:
            count_query += " AND lower(mod_type) = ?"
            count_params.append(normalized_type)

        row = await self.fetch_one(count_query, tuple(count_params))
        total_count = row[0] if row else 0

        if not total_count:
            return {"success": False, "message": "No logs found"}

        type_rows = await self.fetch_all(
            f"SELECT lower(mod_type), COUNT(*) FROM modlogs {base_condition} GROUP BY lower(mod_type)",
            tuple(base_params),
        )
        mod_type_counts = {r[0]: r[1] for r in type_rows}

        start = page_start or 0
        limit = (page_end - start) if page_end is not None else DEFAULT_FETCH_LIMIT

        log_params = base_params.copy()
        log_query = (
            f"SELECT id, moderator_id, mod_type, reason, timestamp"
            f" FROM modlogs {base_condition}"
        )

        if type_filter:
            log_query += " AND lower(mod_type) = ?"
            log_params.append(normalized_type)

        log_query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        log_params.extend([limit, start])

        log_rows = await self.fetch_all(log_query, tuple(log_params))

        logs = [
            {
                "case_id"      : r[0],
                "moderator_id" : r[1],
                "mod_type"     : r[2].lower(),
                "reason"       : r[3],
                "timestamp"    : r[4],
            }
            for r in log_rows
        ]

        return {
            "success"    : True,
            "total_logs" : total_count,
            "counts"     : mod_type_counts,
            "logs"       : logs,
        }
    
    async def fetch_moderation_leaderboard(self, guild_id: int, lb_type: str = "total") -> Dict:
        valid_types = {"total", "daily", "weekly", "monthly"}
        if lb_type not in valid_types:
            lb_type = "total"

        data = {}

        rows = await self.fetch_all(
            "SELECT staff_id FROM staffs WHERE guild_id = ? AND retired = 0 AND on_loa = 0",
            (guild_id,)
        )

        active_staff_id = tuple(row[0] for row in rows) or (-1,)

        rows = await self.fetch_all(
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
    
    async def case_exists(self, case_id: int, guild_id: int) -> bool:
        row = await self.fetch_one(
                "SELECT moderator_id FROM modlogs WHERE id = ? AND guild_id = ?",
                (case_id, guild_id)
            )

        if row is None:
            return False
        else:
            return True

    async def edit_case(self, staff_id: int, case_id: int, case_statement: str, absolute: bool):
        try:
            row = await self.fetch_one(
                "SELECT moderator_id FROM modlogs WHERE id = ?",
                (case_id,)
            )

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

            await self.execute(
                "UPDATE modlogs SET reason = ? WHERE id = ?",
                (case_statement, case_id)
            )

            return {
                "success": True,
                "message": "Case edited successfully."
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"An error occurred: {e}"
            }
        
    async def delete_case(self, case_id: int) -> Dict[str, Any]:
        if not case_id:
            return {
                "success": False,
                "message": "Invalid case_id provided.",
                "case_id": case_id
            }

        try:
            cursor = await self.execute(
                "DELETE FROM modlogs WHERE id = ?", 
                (case_id,)
            )

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
        
    async def clear_mod_queue(self, guild_id: int):
        try:
            await self.execute("DELETE FROM mod_logs_queue WHERE guild_id = ?", (guild_id,))
            return {
                "success": True,
                "message": "Successfully cleared queue"
            }
        except Exception as e:
            return {
                "success": False,
                "message": "Failed to clear the queue"
            }
        
    async def clear_mod_queue_particular(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        try:
            await self.execute("DELETE FROM mod_logs_queue WHERE guild_id = ? AND target_user_id = ?", (guild_id, user_id))

            return {
                "success": True,
                "message": "Successfully removed member from the queue"
            }
        except Exception as e:
            return {
                "success": False,
                "message": "Failed to remove the member from queue"
            }
        
    async def fetch_mod_queue(self, guild_id: int) -> dict:
        rows = await self.fetch_all("""
            SELECT 
                mod_type,
                moderator_id,
                target_user_id,
                reason,
                message_source
            FROM mod_logs_queue
            WHERE guild_id = ?
        """, (guild_id,))

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

    
    """ Tickets Database """
    async def get_ticket_by_id(self, ticket_id: int) -> Optional[Tuple]:
        row = await self.fetch_one(
            """
            SELECT opened_user_id, ticket_type, log_channel_id, submission_json
            FROM tickets
            WHERE ticket_id = ?;
            """,
            (ticket_id,)
        )
        
        if row is None:
            return None

        return tuple(row)
    
    async def get_ticket_by_opener(self, opener_id: int, guild_id: int) -> List[Tuple]:
        rows = await self.fetch_all(
            """
            SELECT ticket_id
            FROM tickets
            WHERE opened_user_id = ?
            AND guild_id = ?
            """,
            (opener_id, guild_id)
        )

        if not rows:
            return []

        return [tuple(row) for row in rows]
    
    async def get_ticket_owner(self, ticket_id: int) -> Optional[int]:
        row = await self.fetch_one(
            """
            SELECT opened_user_id
            FROM tickets
            WHERE ticket_id = ?;
            """,
            (ticket_id,)
        )
        return row[0] if row else None
    
    async def get_guild_tickets(self, guild_id: int) -> List[Tuple]:
        rows = await self.fetch_all(
            """
            SELECT ticket_id, opened_user_id, submission_json, message_id
            FROM tickets
            WHERE guild_id = ?;
            """,
            (guild_id,)
        )
        if rows is None:
            return []

        return [tuple(row) for row in rows]
    
    async def delete_ticket(self, ticket_id: int):
        await self.execute(
            "DELETE FROM tickets WHERE ticket_id = ?",
            (ticket_id,)
        )

    async def create_ticket(
        self,
        ticket_id: int,
        guild_id: int,
        opened_user_id: int,
        ticket_type: str,
        log_channel_id: int,
        submission_json: dict,
        message_id: Optional[int] = None
    ):
        await self.execute(
            """
            INSERT INTO tickets (
                ticket_id,
                guild_id,
                opened_user_id,
                ticket_type,
                log_channel_id,
                submission_json,
                message_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                guild_id,
                opened_user_id,
                ticket_type,
                log_channel_id,
                json.dumps(submission_json),
                message_id
            )
        )

    async def update_ticket_message_id(self, ticket_id: int, message_id: int):
        await self.execute(
            """
            UPDATE tickets
            SET message_id = ?
            WHERE ticket_id = ?
            """,
            (message_id, ticket_id)
        )

    async def update_ticket_submission(self, ticket_id: int, submission_json: dict):
        await self.execute(
            """
            UPDATE tickets
            SET submission_json = ?
            WHERE ticket_id = ?
            """,
            (json.dumps(submission_json), ticket_id)
        )