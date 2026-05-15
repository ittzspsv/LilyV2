from ..sLilyDatabaseAccess import LilyDatabaseAccess
from typing import List, Optional, Final, Set
from dataclasses import dataclass

import json

@dataclass
class GlobalConfig:
    jail: int


""" Commands that can be mapped """
COMMANDS: Final[Set[str]] = {
    "staff_data",
    "staff_list",
    "strike_add",
    "strike_remove",
    "strike_edit",
    "staff_edit",
    "staff_self_edit",
    "strike_show",
    "staff_add",
    "staff_add_batch",
    "staff_remove",
    "staff_remove_raw",
    "staff_roles",
    "dev_staff_update",
    "loa_add",
    "loa_remove",
    "rank_promote",
    "rank_promote_batch",
    "rank_demote",
    "quota_add",
    "quota_list",
    "quota_remove",
    "quota_check",
    "quota_evaluate",
    "staff_role_remove",
    "staff_role_remove_raw",
    "ban",
    "unban",
    "warn",
    "unmute",
    "ms",
    "modlogs",
    "moderation_insights",
    "case_edit",
    "case_edit_absolute",
    "case_delete",
    "queue",
    "queue_remove",
    "ticket_close",
    "ticket_rename",
    "ticket_add"
}

CHANNEL: Final[Set[str]] = {
    "bf_win_loss",
    "bf_fruit_values",
    "logs_channel",
    "staff_updates"
}

class BotGlobalsDatabaseAccess(LilyDatabaseAccess):
    def __init__(self):
        super().__init__()

        self.cache: dict[int, dict] = {}
        self._gconfig: Optional[GlobalConfig] = None
        self._cache_ready = False

    async def load_cache(self):
        """
        {
            guild_id: {
                channels: { type: [ids] },
                permissions: { cmd: [role_ids] },
                roles: { role_id: {limit, ban_queue} },
                prefix: str
            }
        }
        """

        self.cache.clear()

        guilds = await self.fetch_all("SELECT guild_id, prefix FROM data")

        for g in guilds:
            gid = g["guild_id"]

            self.cache[gid] = {
                "channels": {},
                "permissions": {},
                "roles": {},
                "prefix": g["prefix"] or ""
            }


        channel_rows = await self.fetch_all("""
            SELECT guild_id, channel_type, channel_id
            FROM guild_channels
        """)

        for row in channel_rows:
            gid = row["guild_id"]

            cache = self.cache.get(gid)
            if not cache:
                continue

            cache["channels"].setdefault(row["channel_type"], []).append(row["channel_id"])


        perm_rows = await self.fetch_all("""
            SELECT guild_id, role_id, command
            FROM permissions
        """)

        for row in perm_rows:
            gid = row["guild_id"]

            cache = self.cache.get(gid)
            if not cache:
                continue

            cache["permissions"].setdefault(row["command"], []).append(row["role_id"])


        role_rows = await self.fetch_all("""
            SELECT guild_id, role_id, ban_limit, ban_queue
            FROM roles
        """)

        for row in role_rows:
            gid = row["guild_id"]

            cache = self.cache.get(gid)
            if not cache:
                continue

            cache["roles"][row["role_id"]] = {
                "limit": row["ban_limit"] or 0,
                "ban_queue": row["ban_queue"] or 0
            }


        row = await self.fetch_one("""
            SELECT value FROM globals WHERE key = 'Jail'
        """)

        if row and row["value"]:
            self._gconfig = GlobalConfig(jail=int(row["value"]))

        self._cache_ready = True

    @property
    def global_config(self) -> Optional[GlobalConfig]:
        return self._gconfig

    def get_prefix(self, guild_id: int) -> str:
        return (
            self.cache.get(guild_id, {}).get("prefix")
            or "."
        )

    def get_channels(self, guild_id: int, channel_name: str) -> list[int]:
        guild_data = self.cache.get(guild_id)
        if not guild_data:
            return []

        return guild_data.get("channels", {}).get(channel_name, [])
    
    def get_channel(self, guild_id: int, channel_name: str) -> int | None:
        channels = self.get_channels(guild_id, channel_name)

        return channels[0] if channels else None
        
    def has_permission(self, guild_id: int, command: str | None ,roles: List[int]) -> bool:
        if command is None:
            return False
        guild_cache = self.cache.get(guild_id)
        if not guild_cache:
            return False

        allowed_roles = guild_cache["permissions"].get(command, [])

        return any(role_id in allowed_roles for role_id in roles)

    def get_permissions(self, guild_id: int ,role: int) -> List[str]:
        guild_cache = self.cache.get(guild_id)
        if not guild_cache:
            return []

        commands = []

        for key, values in guild_cache["permissions"].items():
            if role in values:
                commands.append(key)

        return commands
    
    def get_ban_limit(self, guild_id: int, role_ids: List[int]) -> int:
        guild = self.cache.get(guild_id)
        if not guild:
            return 0

        role_limits = guild.get("roles", {})

        limits = [
            role_limits[role_id]["limit"]
            for role_id in role_ids
            if role_id in role_limits
        ]

        return max(limits) if limits else 0
    
    def ban_queue(self, guild_id: int, role_ids: List[int]) -> bool:
        guild = self.cache.get(guild_id)
        if not guild:
            return False

        role_limits = guild.get("roles", {})

        return any(
            role_id in role_limits and role_limits[role_id].get("ban_queue", 0) == 1
            for role_id in role_ids
        )
    

    """ Value Assignments """
    async def set_prefix(self, guild_id: int, prefix: str):
        if guild_id not in self.cache:
            self.cache[guild_id] = {
                "channels": {},
                "permissions": {},
                "roles": {},
                "prefix": prefix
            }
        else:
            self.cache[guild_id]["prefix"] = prefix

        await self.execute(
            """
            INSERT INTO data (guild_id, prefix)
            VALUES (?, ?)
            ON CONFLICT(guild_id)
            DO UPDATE SET prefix = excluded.prefix
            """,
            (guild_id, prefix)
        )

    async def set_channel(self, guild_id: int, channel_id: int, channel_type: str):
        guild = self.cache.setdefault(guild_id, {
            "channels": {},
            "permissions": {},
            "roles": {},
            "prefix": "."
        })

        channel_list = guild["channels"].setdefault(channel_type, [])

        if channel_id not in channel_list:
            channel_list.append(channel_id)

        await self.execute(
            """
            INSERT OR IGNORE INTO guild_channels (guild_id, channel_type, channel_id)
            VALUES (?, ?, ?)
            """,
            (guild_id, channel_type, channel_id)
        )

    async def set_permission(self, guild_id: int, role_id: int, command: str):
        guild = self.cache.setdefault(guild_id, {
            "channels": {},
            "permissions": {},
            "roles": {},
            "prefix": "."
        })

        role_list = guild["permissions"].setdefault(command, [])

        if role_id not in role_list:
            role_list.append(role_id)

        await self.execute(
            """
            INSERT OR IGNORE INTO permissions (guild_id, role_id, command)
            VALUES (?, ?, ?)
            """,
            (guild_id, role_id, command)
        )

    """ Value Removals """

    async def remove_channel(
        self,
        guild_id: int,
        channel_id: int,
        channel_type: Optional[str] = None
    ):
        guild = self.cache.get(guild_id)
        if not guild:
            return

        channels = guild.get("channels", {})

        if channel_type:
            if channel_type in channels:
                if channel_id in channels[channel_type]:
                    channels[channel_type].remove(channel_id)

                if not channels[channel_type]:
                    del channels[channel_type]
        else:
            for ctype in list(channels.keys()):
                if channel_id in channels[ctype]:
                    channels[ctype].remove(channel_id)

                if not channels[ctype]:
                    del channels[ctype]

        if channel_type:
            await self.execute(
                """
                DELETE FROM guild_channels
                WHERE guild_id = ? AND channel_id = ? AND channel_type = ?
                """,
                (guild_id, channel_id, channel_type)
            )
        else:
            await self.execute(
                """
                DELETE FROM guild_channels
                WHERE guild_id = ? AND channel_id = ?
                """,
                (guild_id, channel_id)
            )

    async def remove_permission(
        self,
        guild_id: int,
        role_id: int,
        command: Optional[str] = None
    ):
        guild = self.cache.get(guild_id)
        if not guild:
            return

        permissions = guild.get("permissions", {})

        if command:
            if command in permissions:
                if role_id in permissions[command]:
                    permissions[command].remove(role_id)

                if not permissions[command]:
                    del permissions[command]
        else:
            for cmd in list(permissions.keys()):
                if role_id in permissions[cmd]:
                    permissions[cmd].remove(role_id)

                if not permissions[cmd]:
                    del permissions[cmd]

        if command:
            await self.execute(
                """
                DELETE FROM permissions
                WHERE guild_id = ? AND role_id = ? AND command = ?
                """,
                (guild_id, role_id, command)
            )
        else:
            await self.execute(
                """
                DELETE FROM permissions
                WHERE guild_id = ? AND role_id = ?
                """,
                (guild_id, role_id)
            )


    """ Ticket store """
    async def save_ticket_view(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        config: dict
    ) -> None:
        await self.execute(
            """
            INSERT OR REPLACE INTO ticket_views (
                guild_id,
                channel_id,
                message_id,
                config_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                guild_id,
                channel_id,
                message_id,
                json.dumps(config)
            )
        )

    async def get_ticket_views(self, guild_id: Optional[int] = None):
        if guild_id:
            return await self.fetch_all(
                """
                SELECT guild_id, channel_id, message_id, config_json
                FROM ticket_views
                WHERE guild_id = ?
                """,
                (guild_id,)
            )

        return await self.fetch_all(
            """
            SELECT guild_id, channel_id, message_id, config_json
            FROM ticket_views
            """
        )
    
    async def delete_ticket_view(self, message_id: int):
        await self.execute(
            """
            DELETE FROM ticket_views
            WHERE message_id = ?
            """,
            (message_id,)
        )