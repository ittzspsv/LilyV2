from ..sLilyDatabaseAccess import LilyDatabaseAccess
from ..integrations.logging import LoggingDatabase
from typing import Any, Dict, Optional, List, Any
from datetime import datetime, timezone
from collections import defaultdict

class ManagementDatabase(LilyDatabaseAccess):
    def __init__(self) -> None:
        super().__init__()

        self.cache: dict[Any, Any] = {}
        self.logs_db: Optional[LoggingDatabase] = None
        self._cache_ready = False

    async def load_cache(self) -> None:
        rows = await self.fetch_all(
            "SELECT guild_id, role_id FROM roles"
        )

        self.cache.clear()

        for row in rows:
            guild_id, role_id = row

            if guild_id not in self.cache:
                self.cache[guild_id] = set()

            self.cache[guild_id].add(role_id)

        self._cache_ready = True

    def get_staff_roles(self, guild_id: int) -> set:
        return self.cache.get(guild_id, set())
    
    """ Database methods """
    async def fetch_staff_detail(self, staff_id: int) -> Dict[str, Any]:
        query: str = """
        SELECT
            s.name,
            GROUP_CONCAT(r.role_name),
            s.on_loa,
            s.strikes_count,
            s.joined_on,
            s.timezone,
            s.responsibility,
            s.retired
        FROM staffs s
        LEFT JOIN staff_roles sr ON s.staff_id = sr.staff_id
        LEFT JOIN roles r ON sr.role_id = r.role_id
        WHERE s.staff_id = ?
        GROUP BY s.staff_id
        """

        row = await self.fetch_one(query, (staff_id,))

        if not row:
            return {}

        name, role_names, is_loa, strikes_count, joined_on_str, timezone, responsibility, retired = row

        roles_list = role_names.split(",") if role_names else []

        if joined_on_str:
            joined_on = datetime.strptime(joined_on_str, "%d/%m/%Y")
            joined_on_timestamp = int(joined_on.timestamp())
        else:
            joined_on_timestamp = int(datetime.now(timezone.utc).timestamp())

        return {
            "name": name,
            "role_name": roles_list,
            "is_loa": is_loa,
            "strikes_count": strikes_count,
            "joined_on": joined_on_timestamp,
            "timezone": timezone,
            "responsibility": responsibility,
            "retired": retired
        }
    
    async def fetch_all_staffs(self, guild_id: int) -> Dict[str, Any]:
        count_query = """
        SELECT 
            r.role_type,

            COUNT(DISTINCT s.staff_id) AS total_staffs,

            SUM(CASE WHEN s.on_loa = 1 THEN 1 ELSE 0 END) AS loa_staffs,

            SUM(CASE WHEN s.on_loa = 0 THEN 1 ELSE 0 END) AS active_staffs

        FROM staffs s
        JOIN staff_roles sr 
            ON s.staff_id = sr.staff_id
        JOIN roles r 
            ON sr.role_id = r.role_id

        WHERE 
            s.retired = 0 
            AND s.guild_id = ?

        GROUP BY r.role_type;
        """

        rows = await self.fetch_all(count_query, (guild_id,))

        role_count_result = {}
        for role_type, total, loa, active in rows:
            role_count_result[role_type] = {
                "total": total,
                "loa": loa,
                "active": active
            }
        rows = await self.fetch_all(
            """
            SELECT 
                r.role_id,
                r.role_name,
                s.staff_id,
                s.name,
                s.avatar_url,
                s.joined_on,
                s.Timezone,
                r.role_type
            FROM roles r
            LEFT JOIN staff_roles sr 
                ON r.role_id = sr.role_id
            LEFT JOIN staffs s 
                ON sr.staff_id = s.staff_id
                AND s.retired = 0
            WHERE r.guild_id = ?
            ORDER BY r.role_priority, s.name;
            """,
            (guild_id,)
        )


        role_user_map = {}
        time_now = datetime.now(timezone.utc)

        for role_id, role_name, staff_id, name, avatar_url, joined_on, dtimezone, role_type in rows:

            try:
                dt = (
                    datetime.strptime(joined_on, "%d/%m/%Y").replace(tzinfo=timezone.utc)
                    if joined_on
                    else time_now
                )
            except ValueError:
                dt = time_now

            unix_timestamp = int(dt.timestamp())

            role = role_user_map.setdefault(role_id, {
                "role_name": role_name,
                "role_type" : role_type,
                "staff": []
            })

            if staff_id is not None:
                role["staff"].append({
                    "name": name,
                    "id": staff_id,
                    "avatar_profile": avatar_url,
                    "joined_on": unix_timestamp,
                    "timezone": dtimezone or "Default"
                })

        return {
            "overall" : role_count_result,
            "roles": role_user_map
        }

    async def add_staff(self, staff_id: int, guild_id: int, name: str, avatar_url: str) -> Dict[str, Any]:
        row = await self.fetch_one(
            """
            SELECT retired
            FROM staffs
            WHERE staff_id = ? AND guild_id = ?
            """,
            (staff_id, guild_id)
        )


        if row:
            if row[0] == 1:
                await self.execute(
                    """
                    UPDATE staffs
                    SET retired = 0,
                        name = ?,
                        avatar_url = ?
                    WHERE staff_id = ? AND guild_id = ?
                    """,
                    (name, avatar_url, staff_id, guild_id)
                ,commit=False)
            else:
                return {
                    "success": False,
                    "message": "Staff entry already exists"
                }
        else:
            await self.execute(
                """
                INSERT INTO staffs (
                    staff_id,
                    name,
                    guild_id,
                    on_loa,
                    strikes_count,
                    retired,
                    Timezone,
                    responsibility,
                    avatar_url
                )
                VALUES (?, ?, ?, 0, 0, 0, 'Default', 'None', ?)
                """,
                (staff_id, name, guild_id, avatar_url)
            ,commit=False)

        config = await self.fetch_one(
            """
            SELECT staff_role_base
            FROM staff_configs
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

        base_roles = []
        if config and config[0]:
            base_roles = [
                int(r.strip()) for r in config[0].split(",") if r.strip()
            ]

        initial_role_row = await self.fetch_one(
            """
            SELECT role_id
            FROM roles
            WHERE guild_id = ?
            AND role_type = 'Staff'
            ORDER BY role_priority DESC
            LIMIT 1
            """,
            (guild_id,)
        )

        initial_role = initial_role_row[0] if initial_role_row else None

        if initial_role:
            await self.execute(
                "INSERT INTO staff_roles (staff_id, role_id) VALUES (?, ?)",
                (staff_id, initial_role),commit=False
            )

        roles_to_add = set(base_roles)
        if initial_role:
            roles_to_add.add(initial_role)

        await self.commit()

        return {
            "success": True,
            "roles_to_add": list(roles_to_add),
            "message": "Staff added successfully"
        }

    async def remove_staff(self, staff_id: int, guild_id: int) -> Dict[str, Any]:
        row = await self.fetch_one("""
            SELECT retired
            FROM staffs
            WHERE staff_id = ? AND guild_id = ?
        """, (staff_id, guild_id))

        if not row:
            return {
                "success": False,
                "message": "Staff not found"
            }

        retired = row[0]

        if retired == 1:
            return {
                "success": False,
                "message": "Staff is already retired"
            }

        await self.execute("""
            UPDATE staffs
            SET retired = 1
            WHERE staff_id = ? AND guild_id = ?
        """, (staff_id, guild_id), commit=False)

        rows = await self.fetch_all(
            """
            SELECT role_id
            FROM staff_roles
            WHERE staff_id = ?
            """,
            (staff_id,)
        )

        role_ids = [row[0] for row in rows]

        config = await self.fetch_one("""
                SELECT staff_role_base FROM staff_configs WHERE guild_id = ?
        """, (guild_id,))

        base_roles = []
        if config and config[0]:
            base_roles = [int(r.strip()) for r in config[0].split(",") if r.strip()]

        await self.execute("""
            DELETE FROM staff_roles
            WHERE staff_id = ?
        """, (staff_id,), commit=False)

        await self.commit()

        return {
            "success": True,
            "message": "Staff marked as retired",
            "roles_to_remove" : list(set(role_ids + base_roles))
        }
    
    async def edit_staff(self, staff_id: int, guild_id: int, name: Optional[str], joined_on: Optional[str], timezone: Optional[str], responsibility: Optional[str]) -> Dict[str, Any]:
        fields = {
            "name": name,
            "joined_on": joined_on,
            "timezone": timezone,
            "responsibility": responsibility
        }

        update_columns = {k: v for k, v in fields.items() if v is not None}

        if not update_columns:
            return {
                "success": False,
                "message": "No fields provided to update"
            }

        row = await self.fetch_one(
            "SELECT 1 FROM staffs WHERE staff_id = ? AND guild_id = ?",
            (staff_id, guild_id)
        )

        if not row:
            return {
                "success": False,
                "message": f"No staff found with ID {staff_id}"
            }

        set_clause = ", ".join([f"{col} = ?" for col in update_columns])

        values: List[Any] = list(update_columns.values())
        values.extend([staff_id, guild_id])

        query = f"""
        UPDATE staffs
        SET {set_clause}
        WHERE staff_id = ? AND guild_id = ?
        """

        await self.execute(query, tuple(values))

        return {
            "success": True,
            "message": f"Staff ID {staff_id} updated successfully"
        }
    
    async def strike_staff(self, staff_id: int, guild_id: int, issued_by: int, reason: str) -> Dict[str, Any]:
        exists = await self.fetch_one(
            "SELECT 1 FROM staffs WHERE staff_id = ? AND guild_id = ?",
            (staff_id, guild_id)
        )

        if not exists:
            return {
                "success": False,
                "message": "Staff member not found"
            }

        await self.execute(
            """
            INSERT INTO strikes (
                issued_by_id,
                issued_to_id,
                reason,
                date,
                guild_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                issued_by,
                staff_id,
                reason,
                datetime.today().strftime("%d/%m/%Y"),
                guild_id
            ),
            commit=False
        )

        await self.execute(
            """
            UPDATE staffs
            SET strikes_count = strikes_count + 1
            WHERE staff_id = ? AND guild_id = ?
            """,
            (staff_id, guild_id),
            commit=False
        )
        await self.commit()

        return {
            "success": True,
            "staff_id" : staff_id,
            "issued_by" : issued_by,
            "reason" : reason,
            "message": f"Successfully striked staff <@{staff_id}>"
        }
    
    async def remove_strike(self, strike_id: int, guild_id: int) -> Dict[str, str | bool]:
        row = await self.fetch_one(
            """
            SELECT issued_to_id
            FROM strikes
            WHERE strike_id = ? AND guild_id = ?
            """,
            (strike_id, guild_id)
        )

        if not row:
            return {
                "success": False,
                "message": f"No strike with ID `{strike_id}` found"
            }

        staff_id = row[0]

        await self.execute(
            "DELETE FROM strikes WHERE strike_id = ?",
            (strike_id,),
            commit=False
        )

        await self.execute(
            """
            UPDATE staffs
            SET strikes_count = CASE
                WHEN strikes_count > 0 THEN strikes_count - 1
                ELSE 0
            END
            WHERE staff_id = ? AND guild_id = ?
            """,
            (staff_id, guild_id),
            commit=False
        )

        await self.commit()

        return {
            "success": True,
            "message": f"Strike `{strike_id}` removed from <@{staff_id}>"
        }
    
    async def edit_strike(self, strike_id: int, guild_id: int, staff_id: int, new_reason: str) -> Dict[str, str | bool]:
        row = await self.fetch_one(
            """
            SELECT issued_to_id, issued_by_id
            FROM strikes
            WHERE strike_id = ? AND guild_id = ?
            """,
            (strike_id, guild_id)
        )

        if not row:
            return {
                "success": False,
                "message": f"No strike with ID `{strike_id}` found"
            }
        
        # Attempt to edit the strike.
        if not row[1] == staff_id:
            return {
                "success": False,
                "message": "Only the staff who issued the strike can edit it."
            }
        
        await self.execute("UPDATE strikes SET reason = ?", (new_reason,))

        return {
            "success": True,
            "message": f"Striked `{strike_id}` edited Successfully!"
        }

    async def fetch_staff_strikes(self, staff_id: int, guild_id: int) -> Dict[str, bool | str | List[dict]]:
        try:
            rows = await self.fetch_all(
                """
                SELECT strike_id, reason, date, issued_by_id
                FROM strikes
                WHERE issued_to_id = ? AND guild_id = ?
                ORDER BY strike_id DESC
                """,
                (staff_id, guild_id)
            )

            if not rows:
                return {
                    "success": False,
                    "message": "No strikes found",
                    "data": []
                }

            strikes = [
                {
                    "strike_id": r[0],
                    "reason": r[1],
                    "date": r[2],
                    "manager": r[3]
                }
                for r in rows
            ]

            return {
                "success": True,
                "message": "Strikes fetched",
                "data": strikes
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "data": []
            }
        
    async def add_role_entries(self, guild_id: int, roles: list | tuple) -> Dict[str, str | bool]:
        try:
            rows = await self.fetch_all(
                "SELECT role_id FROM roles WHERE guild_id = ?",
                (guild_id,)
            )

            concurrent_roles = tuple(role[0] for role in rows)

            await self.execute(
                "DELETE FROM roles WHERE guild_id = ?",
                (guild_id,),
                commit=False
            )

            if concurrent_roles:
                placeholders = ",".join("?" for _ in concurrent_roles)
                await self.execute(
                    f"DELETE FROM staff_roles WHERE role_id IN ({placeholders})",
                    concurrent_roles,
                    commit=False
                )

            priority = 0

            for item in roles:
                role_name = item["role_name"]
                role_id = item["role_id"]
                role_icon = item["role_icon"]

                await self.execute(
                    """
                    INSERT INTO roles 
                    (guild_id, role_id, role_name, role_priority, ban_limit, role_icon)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (guild_id, role_id, role_name, priority, 0, role_icon),
                    commit=False
                )

                priority += 1

            await self.commit()

            return {
                "success": True,
                "message": "Role hierarchy successfully set up!"
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
        
    async def add_loa(self, guild_id: int, staff_id: int, reason: str, loa_issued_by: int) -> Dict[str, Any]:
        if not staff_id:
            return {"success": False, "message": "Missing staff_id"}

        row = await self.fetch_one(
            "SELECT on_loa FROM staffs WHERE staff_id = ?",
            (staff_id,)
        )

        if row and row[0] == 1:
            return {"success": False, "message": "Staff is already on LOA"}

        try:
            await self.execute(
                "UPDATE staffs SET on_loa = 1 WHERE staff_id = ?",
                (staff_id,),
                commit=False
            )

            await self.execute(
                """
                INSERT INTO leaves (staff_id, reason, issued_by)
                VALUES (?, ?, ?)
                """,
                (staff_id, reason, loa_issued_by),
                commit=False
            )

            rows = await self.fetch_all(
                "SELECT role_id FROM staff_roles WHERE staff_id = ?",
                (staff_id,)
            )

            roles_to_remove = [row[0] for row in rows]

            config = await self.fetch_one(
                "SELECT loa_role, staff_role_base FROM staff_configs WHERE guild_id = ?",
                (guild_id,)
            )

            roles_to_add = (config[0],) if config and config[0] else ()

            if config:
                loa_role, staff_role_base = config

                if staff_role_base:
                    roles_to_remove.extend(
                        int(role) for role in staff_role_base.split(",")
                    )

            await self.commit()

            return {
                "success": True,
                "message": "Staff added to LOA successfully!",
                "roles_to_remove": roles_to_remove,
                "roles_to_add": roles_to_add
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
        
    async def remove_loa(self, staff_id: int, guild_id: int) -> Dict[str, Any]:
        if not staff_id:
            return {"success": False, "message": "Missing staff_id"}

        try:
            await self.execute(
                "UPDATE staffs SET on_loa = 0 WHERE staff_id = ?", 
                (staff_id,)
            )


            rows = await self.fetch_all(
                "SELECT role_id FROM staff_roles WHERE staff_id = ?", 
                (staff_id,)
            )

            roles_to_add = list(row[0] for row in rows)

            config = await self.fetch_one(
                "SELECT loa_role, staff_role_base FROM staff_configs WHERE guild_id = ?",
                (guild_id,)
            )

            roles_to_remove = (config[0],) if config and config[0] else ()

            if config:
                loa_role, staff_role_base = config

                if staff_role_base:
                    roles_to_add.extend(
                        int(role) for role in staff_role_base.split(",")
                    )

            return {
                "success": True,
                "message": "Staff removed from LOA successfully!",
                "roles_to_add": roles_to_add,
                "roles_to_remove" : roles_to_remove
            }

        except Exception as e:
            return {"success": False, "message": str(e)}
        
    async def fetch_loa_staffs(self, guild_id: int, role_type: str) -> List[Dict[str, Any]]:
        staff_loa: list = []

        rows = await self.fetch_all(
            """
            SELECT DISTINCT 
                s.staff_id, 
                s.joined_on, 
                s.avatar_url
            FROM staffs s
            JOIN staff_roles sr 
                ON s.staff_id = sr.staff_id
            JOIN roles r 
                ON sr.role_id = r.role_id
            WHERE 
                s.on_loa = 1
                AND s.guild_id = ?
                AND r.role_type = ?
            """,
            (guild_id, role_type)
        )

        for staff_id, joined_on, avatar_url in rows:
            dt = datetime.strptime(joined_on or "01/01/2000", "%d/%m/%Y")

            staff_loa.append({
                "staff_id": staff_id,
                "joined_on": int(dt.timestamp()),
                "avatar_url": avatar_url
            })

        return staff_loa
        
    async def update_staff(self, guild_id: int, staff_id: int, update_type: str, reason: str, updated_by: int) -> Dict[str, Any]:
        if staff_id == updated_by:
            return {"success": False, "message": "You cannot update yourself."}

        if update_type not in ("promotion", "demotion"):
            return {"success": False, "message": "Invalid update_type."}

        current_role = await self.fetch_one(
            """
            SELECT sr.id, r.role_id, r.role_priority
            FROM staff_roles sr
            JOIN roles r ON sr.role_id = r.role_id
            WHERE sr.staff_id = ?
            AND r.guild_id = ?
            AND r.role_type = 'Staff'
            LIMIT 1
            """,
            (staff_id, guild_id)
        )

        if not current_role:
            return {"success": False, "message": "No staff role assigned."}

        sr_id, current_role_id, current_priority = current_role

        updater_role = await self.fetch_one(
            """
            SELECT r.role_priority
            FROM staff_roles sr
            JOIN roles r ON sr.role_id = r.role_id
            WHERE sr.staff_id = ?
            AND r.guild_id = ?
            AND r.role_type = 'Staff'
            LIMIT 1
            """,
            (updated_by, guild_id)
        )

        if not updater_role:
            return {"success": False, "message": "Updater has no staff role."}

        updater_priority = updater_role[0]

        if current_priority <= updater_priority:
            return {
                "success": False,
                "message": "You cannot update someone with equal or higher role."
            }

        if update_type == "promotion":
            next_role = await self.fetch_one(
                """
                SELECT role_id, role_priority
                FROM roles
                WHERE guild_id = ?
                AND role_type = 'Staff'
                AND role_priority < ?
                ORDER BY role_priority DESC
                LIMIT 1
                """,
                (guild_id, current_priority)
            )
        else:
            next_role = await self.fetch_one(
                """
                SELECT role_id, role_priority
                FROM roles
                WHERE guild_id = ?
                AND role_type = 'Staff'
                AND role_priority > ?
                ORDER BY role_priority ASC
                LIMIT 1
                """,
                (guild_id, current_priority)
            )

        if not next_role:
            return {
                "success": False,
                "message": f"Already at {'highest' if update_type == 'promotion' else 'lowest'} role."
            }

        new_role_id, new_priority = next_role

        if new_priority < updater_priority:
            return {
                "success": False,
                "message": "You cannot update someone beyond your own role priority."
            }

        await self.execute(
            """
            UPDATE staff_roles
            SET role_id = ?
            WHERE id = ?
            """,
            (new_role_id, sr_id),
            commit=False
        )

        await self.execute(
            """
            INSERT INTO rank_updates (
                staff_id,
                updated_by,
                old_role_id,
                new_role_id,
                update_type,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                staff_id,
                updated_by,
                current_role_id,
                new_role_id,
                update_type,
                reason
            ),
            commit=False
        )

        await self.commit()

        return {
            "success": True,
            "message": f"{update_type.title()} successful",
            "old_role_id": current_role_id,
            "new_role_id": new_role_id,
            "staff_id": staff_id,
        }

    async def add_staff_quota(self, guild_id: int, role_id: int, min_msg: int, min_ms: int, on_quota_passed: str, on_quota_failed: str, check_by: str) -> Dict[str, Any]:
        # Constraints
        if not all(
            action is None or action in {'promote', 'demote', 'strike', 'Promote', 'Demote', 'Strike', 'none', 'None'}
            for action in (on_quota_passed, on_quota_failed)):       
                return {"success": False, "message": "Invalid parameters passed"}

        if check_by not in ("1d", "7d", "30d", None):
            return {"success": False, "message": "Invalid parameter type passed (check_by)"}

        # Add Quota Now.
        await self.execute('''
                INSERT INTO staff_quota (role_id, guild_id, min_msg, min_ms, on_quota_passed, on_quota_failed, check_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (role_id, guild_id, min_msg, min_ms, on_quota_passed, on_quota_failed, check_by))


        return {"success": True, "message" : "Quota Defined Successfully"}
    
    async def fetch_staff_quota(self, guild_id: int) -> List[Dict[str, Any]]:
        rows = await self.fetch_all('''
            SELECT quota_id, role_id, guild_id, min_msg, min_ms,
                on_quota_passed, on_quota_failed, check_by
            FROM staff_quota
            WHERE guild_id = ?
        ''', (guild_id,))

        return [
            {
                "quota_id": row[0],
                "role_id": row[1],
                "guild_id": row[2],
                "min_msg": row[3],
                "min_ms": row[4],
                "on_quota_passed": row[5],
                "on_quota_failed": row[6],
                "check_by": row[7],
            }
            for row in rows
        ]
    
    async def remove_staff_quota(self, guild_id: int ,quota_id: int) -> Dict[str, Any]:
        await self.execute(
            "DELETE FROM staff_quota WHERE quota_id = ? AND guild_id = ?",
            (quota_id, guild_id)
        )
        return {"success": True, "message": "Quota removed successfully"}

    # FIX THIS IN FUTURE    

    async def get_staff_current_quota(self, guild_id: int, staff_id: int) -> Dict[str, Any]:
        if self.logs_db is None:
            return {"success": False, "message": "Database has not been initialized"}
        msg_query = """
        SELECT daily_messages, weekly_messages, monthly_messages, total_messages
        FROM staff_messages
        WHERE staff_id = ? AND guild_id = ?
        """
        msg_data  = await self.fetch_one(msg_query, (staff_id, guild_id))

        if not msg_data:
            return {"success": False, "message": "Staff messages not found"}

        daily, weekly, monthly, total = msg_data

        role_query = """
        SELECT r.role_id
        FROM staff_roles sr
        JOIN roles r ON sr.role_id = r.role_id
        WHERE sr.staff_id = ?
        ORDER BY r.role_priority ASC
        LIMIT 1
        """
        role_data  = await self.fetch_one(role_query, (staff_id,))

        if not role_data:
            return {"success": False,"message": "Staff role not found"}

        role_id = role_data[0]

        quota_query = """
        SELECT min_msg, min_ms
        FROM staff_quota
        WHERE role_id = ? AND guild_id = ?
        """
        quota_data = await self.fetch_one(quota_query, (role_id, guild_id))

        if not quota_data:
            return {"success": False, "message": "No quota has been defined for any of the staff roles assigned to this user. Please define a quota."}
        
        mod_stats = await self.logs_db.fetch_mod_stats(**{"guild_id" : guild_id, "moderator_id": staff_id, "page_start" : 0, "page_end": 0})

        stats = mod_stats.get("stats") or {}
        weekly_ms = sum(action_data.get("7d", 0) for action_data in stats.values())

        min_msg = int(quota_data[0]) if quota_data[0] else 0
        min_ms = int(quota_data[1]) if quota_data[1] else 0
        message_quota_passed = weekly >= min_msg
        ms_quota_passed = weekly_ms >= min_ms
        

        return {
            "success" : True,
            "message" : "Quota fetched successfully.",
            "staff_id": staff_id,
            "guild_id": guild_id,

            "messages": {
                "daily": daily,
                "weekly": weekly,
                "monthly": monthly,
                "total": total,
            },

            "mod_stats_weekly" : {
                "weekly_ms": weekly_ms
            },

            "quota": {
                "min_msg": min_msg,
                "min_ms": min_ms,
            },

            "result": {
                "message_quota_passed": message_quota_passed,
                "ms_quota_passed": ms_quota_passed
            }
        }
    
    async def update_message(self, staff_id: int, guild_id: int) -> None:
        await self.execute('''
            INSERT INTO staff_messages (
                staff_id, guild_id,
                daily_messages, weekly_messages, monthly_messages, total_messages
            )
            VALUES (?, ?, 1, 1, 1, 1)
            ON CONFLICT(staff_id, guild_id) DO UPDATE SET
                daily_messages = daily_messages + 1,
                weekly_messages = weekly_messages + 1,
                monthly_messages = monthly_messages + 1,
                total_messages = total_messages + 1
        ''', (staff_id, guild_id))

    async def remove_role(self, role_id: int) -> Dict[str, Any]:
        try:
            await self.execute("DELETE FROM staff_roles WHERE role_id = ?", (role_id,), commit=False)
            await self.execute("DELETE FROM staff_quota WHERE role_id = ?", (role_id,), commit=False)
            await self.execute("DELETE FROM roles WHERE role_id = ?", (role_id,), commit=False)

            await self.commit()
            
            return {
                "success": True,
                "message": "Role removed successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Role removal encountered with an error: {e}"
            }
        
    # FIX THIS IN FUTURE 
    async def get_all_staff_quota_status(self, guild_id: int) -> Dict[str, Any]:
        if self.logs_db is None:
            return {"success": False, "message": "Database has not been initialized"}
        quotas = await self.fetch_all(
            """
            SELECT quota_id, role_id, min_msg, min_ms, on_quota_passed, on_quota_failed, check_by
            FROM staff_quota
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

        if not quotas:
            return {
                "success": False,
                "message": "No quotas defined for this guild"
            }

        quota_role_ids = [q[1] for q in quotas if q[1] is not None]

        if not quota_role_ids:
            return {
                "success": False,
                "message": "No valid quota roles found"
            }

        placeholders = ",".join("?" for _ in quota_role_ids)

        staff_rows = await self.fetch_all(
            f"""
            SELECT DISTINCT s.staff_id, s.name
            FROM staffs s
            JOIN staff_roles r ON s.staff_id = r.staff_id
            WHERE s.guild_id = ?
            AND s.retired = 0
            AND s.on_loa = 0
            AND r.role_id IN ({placeholders})
            """,
            (guild_id, *quota_role_ids)
        )

        if not staff_rows:
            return {
                "success": False,
                "message": "No applicable staff found for quota evaluation"
            }

        role_map_rows = await self.fetch_all(
            """
            SELECT sr.staff_id, sr.role_id
            FROM staff_roles sr
            JOIN roles r ON sr.role_id = r.role_id
            WHERE r.guild_id = ?
            """,
            (guild_id,)
        )

        staff_roles_map = defaultdict(list)
        for staff_id, role_id in role_map_rows:
            staff_roles_map[staff_id].append(role_id)

        passed_staff = []
        failed_staff = []

        for staff_id, name in staff_rows:
            staff_roles = staff_roles_map.get(staff_id, [])

            applicable_quotas = [
                q for q in quotas if q[1] in staff_roles
            ]

            if not applicable_quotas:
                continue

            msg_row = await self.fetch_one(
                """
                SELECT weekly_messages
                FROM staff_messages
                WHERE staff_id = ? AND guild_id = ?
                """,
                (staff_id, guild_id)
            )

            weekly_messages = msg_row[0] if msg_row else 0

            mod_stats = await self.logs_db.fetch_mod_stats(**{
                "guild_id": guild_id,
                "moderator_id": staff_id,
                "page_start": 0,
                "page_end": 0
            })

            stats = mod_stats.get("stats") or {}
            weekly_ms = sum(v.get("7d", 0) for v in stats.values())

            staff_passed_any = False
            staff_results = []
            staff_fail_reasons = []

            for quota in applicable_quotas:
                quota_id, quota_role_id, min_msg, min_ms, on_pass, on_fail, check_by = quota

                msg_ok = int(weekly_messages or 0) >= int(min_msg or 0)
                ms_ok = int(weekly_ms or 0) >= int(min_ms or 0)

                quota_passed = msg_ok and ms_ok

                staff_results.append({
                    "quota_id": quota_id,
                    "role_id": quota_role_id,
                    "passed": quota_passed,
                    "weekly_messages": weekly_messages,
                    "weekly_ms": weekly_ms,
                    "required": {
                        "min_msg": int(min_msg or 0),
                        "min_ms": int(min_ms or 0)
                    },
                    "failed_reasons": (
                        [] if quota_passed else
                        (["message_quota_failed"] if not msg_ok else []) +
                        (["mod_stats_failed"] if not ms_ok else [])
                    )
                })

                if quota_passed:
                    staff_passed_any = True
                else:
                    staff_fail_reasons.append(f"quota_{quota_id}_failed")

            if staff_passed_any:
                passed_staff.append({
                    "staff_id": staff_id,
                    "name": name,
                    "results": staff_results
                })
            else:
                failed_staff.append({
                    "staff_id": staff_id,
                    "name": name,
                    "reasons": staff_fail_reasons,
                    "results": staff_results
                })

        return {
            "success": True,
            "guild_id": guild_id,
            "summary": {
                "total_staff": len(list(staff_rows)),
                "passed": len(passed_staff),
                "failed": len(failed_staff),
                "total_quotas": len(list(quotas))
            },
            "passed_staff": passed_staff,
            "failed_staff": failed_staff,
        }
    
    async def reset_messages(self, guild_id: int) -> Dict[str, Any]:
        if not guild_id:
            return {"success": False, "message": "Invalid guild_id"}

        query = """
        UPDATE staff_messages
        SET daily_messages = 0,
            weekly_messages = 0
        WHERE guild_id = ?
        """

        await self.execute(query, (guild_id,))

        return {
            "success": True,
            "message": f"Daily and weekly messages reset for guild {guild_id}"
        }