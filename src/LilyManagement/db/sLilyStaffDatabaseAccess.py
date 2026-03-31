import aiosqlite
from datetime import datetime, timezone
import Config.sBotDetails as Configs

from typing import Optional, Dict, List, Any

sdb = None

async def initialize():
    global sdb
    sdb = await aiosqlite.connect("storage/management/staff_management.db")
    '''
    #DDL SCHEMA INITIALIZATION
    await sdb.execute("CREATE TABLE IF NOT EXISTS roles (role_id INTEGER PRIMARY KEY ,role_name TEXT NOT NULL UNIQUE,role_priority INTEGER NOT NULL, ban_limit INTEGER)")
    await sdb.commit()
    '''
async def initialize_cache():
    pass

async def fetch_staff_detail(staff_id: int):
    query = """
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

    cursor = await sdb.execute(query, (staff_id,))
    row = await cursor.fetchone()

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

async def fetch_all_staffs(guild_id: int):
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

    cursor = await sdb.execute(count_query, (guild_id,))
    rows = await cursor.fetchall()
    role_count_result = {}
    for role_type, total, loa, active in rows:
        role_count_result[role_type] = {
            "total": total,
            "loa": loa,
            "active": active
        }
    cursor = await sdb.execute(
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

    rows = await cursor.fetchall()

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

async def add_staff(payload: dict) -> Dict[str, Any]:
    staff_id: int = payload.get("staff_id")
    guild_id: int = payload.get("guild_id")
    name: str = payload.get("name")
    avatar_url: str = payload.get("avatar_url")

    cursor = await sdb.execute(
        """
        SELECT retired
        FROM staffs
        WHERE staff_id = ? AND guild_id = ?
        """,
        (staff_id, guild_id)
    )

    row = await cursor.fetchone()

    await sdb.execute("BEGIN")

    if row:
        if row[0] == 1:
            await sdb.execute(
                """
                UPDATE staffs
                SET retired = 0,
                    name = ?,
                    avatar_url = ?
                WHERE staff_id = ? AND guild_id = ?
                """,
                (name, avatar_url, staff_id, guild_id)
            )
        else:
            await sdb.execute("ROLLBACK")
            return {
                "success": False,
                "message": "Staff entry already exists"
            }
    else:
        await sdb.execute(
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
        )

    cursor = await sdb.execute(
        """
        SELECT staff_role_base, staff_updates_channel
        FROM staff_configs
        WHERE guild_id = ?
        """,
        (guild_id,)
    )

    config = await cursor.fetchone()

    base_roles = []
    if config and config[0]:
        base_roles = [
            int(r.strip()) for r in config[0].split(",") if r.strip()
        ]

    cursor = await sdb.execute(
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

    initial_role_row = await cursor.fetchone()

    initial_role = initial_role_row[0] if initial_role_row else None

    await sdb.execute("INSERT INTO staff_roles (staff_id, role_id) VALUES (?, ?)", (staff_id, initial_role))


    await sdb.commit()

    roles_to_add = set(base_roles)
    if initial_role:
        roles_to_add.add(initial_role)

    return {
        "success": True,
        "roles_to_add": list(roles_to_add),
        "message": "Staff added successfully",
        "staff_updates_channel" : config[1]
    }

async def remove_staff(payload: dict) -> Dict[str, str | bool]:
    staff_id: str = payload["staff_id"]
    guild_id: str = payload["guild_id"]

    cursor = await sdb.execute("""
        SELECT retired
        FROM staffs
        WHERE staff_id = ? AND guild_id = ?
    """, (staff_id, guild_id))

    row = await cursor.fetchone()

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

    await sdb.execute("""
        UPDATE staffs
        SET retired = 1
        WHERE staff_id = ? AND guild_id = ?
    """, (staff_id, guild_id))

    cursor = await sdb.execute(
        """
        SELECT role_id
        FROM staff_roles
        WHERE staff_id = ?
        """,
        (staff_id,)
    )

    rows = await cursor.fetchall()

    role_ids = [row[0] for row in rows]

    cursor = await sdb.execute("""
            SELECT staff_role_base, staff_updates_channel FROM staff_configs WHERE guild_id = ?
     """, (guild_id,))

    config = await cursor.fetchone()
    base_roles = []
    if config and config[0]:
        base_roles = [int(r.strip()) for r in config[0].split(",") if r.strip()]

    await sdb.execute("""
        DELETE FROM staff_roles
        WHERE staff_id = ?
    """, (staff_id,))

    await sdb.commit()

    return {
        "success": True,
        "message": "Staff marked as retired",
        "roles_to_remove" : list(set(role_ids + base_roles)),
        "staff_updates_channel" : config[1]
    }

async def edit_staff(payload: dict) -> Dict[str, str | bool]:
    staff_id = payload["staff_id"]
    guild_id = payload["guild_id"]

    fields = {
        "name": payload.get("name"),
        "role_id": payload.get("role_id"),
        "joined_on": payload.get("joined_on"),
        "timezone": payload.get("timezone"),
        "responsibility": payload.get("responsibility")
    }

    update_columns = {k: v for k, v in fields.items() if v is not None}

    if not update_columns:
        return {
            "success": False,
            "message": "No fields provided to update"
        }

    async with sdb.execute("BEGIN IMMEDIATE"):

        cursor = await sdb.execute(
            "SELECT 1 FROM staffs WHERE staff_id = ? AND guild_id = ?",
            (staff_id, guild_id)
        )
        row = await cursor.fetchone()

        if not row:
            return {
                "success": False,
                "message": f"No staff found with ID {staff_id}"
            }

        set_clause = ", ".join([f"{col} = ?" for col in update_columns])

        values = list(update_columns.values())
        values.extend([staff_id, guild_id])

        query = f"""
        UPDATE staffs
        SET {set_clause}
        WHERE staff_id = ? AND guild_id = ?
        """

        await sdb.execute(query, values)

    await sdb.commit()

    return {
        "success": True,
        "message": f"Staff ID {staff_id} updated successfully"
    }

async def strike_staff(payload: dict) -> Dict[str, str | bool]:
    staff_id = payload["staff_id"]
    guild_id = payload["guild_id"]
    issued_by = payload["issued_by"]
    reason = payload["reason"]

    cursor = await sdb.execute(
        "SELECT 1 FROM staffs WHERE staff_id = ? AND guild_id = ?",
        (staff_id, guild_id)
    )
    exists = await cursor.fetchone()

    if not exists:
        return {
            "success": False,
            "message": "Staff member not found"
        }

    await sdb.execute(
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
        )
    )

    await sdb.execute(
        """
        UPDATE staffs
        SET strikes_count = strikes_count + 1
        WHERE staff_id = ? AND guild_id = ?
        """,
        (staff_id, guild_id)
    )

    cursor = await sdb.execute("""
            SELECT staff_updates_channel FROM staff_configs WHERE guild_id = ?
     """, (guild_id,))

    config = await cursor.fetchone()
    await sdb.commit()

    return {
        "success": True,
        "staff_id" : staff_id,
        "issued_by" : issued_by,
        "reason" : reason,
        "message": f"Successfully striked staff <@{staff_id}>",
        "staff_updates_channel" : config[0]
    }

async def remove_strike(payload: dict) -> Dict[str, str | bool]:
    strike_id = payload["strike_id"]
    guild_id = payload["guild_id"]


    cursor = await sdb.execute(
        """
        SELECT issued_to_id
        FROM strikes
        WHERE strike_id = ? AND guild_id = ?
        """,
        (strike_id, guild_id)
    )

    row = await cursor.fetchone()

    if not row:
        return {
            "success": False,
            "message": f"No strike with ID `{strike_id}` found"
        }

    staff_id = row[0]

    await sdb.execute(
        "DELETE FROM strikes WHERE strike_id = ?",
        (strike_id,)
    )

    await sdb.execute(
        """
        UPDATE staffs
        SET strikes_count = CASE
            WHEN strikes_count > 0 THEN strikes_count - 1
            ELSE 0
        END
        WHERE staff_id = ? AND guild_id = ?
        """,
        (staff_id, guild_id)
    )

    await sdb.commit()

    return {
        "success": True,
        "message": f"Strike `{strike_id}` removed from <@{staff_id}>"
    }

async def fetch_staff_strikes(payload: dict) -> Dict[str, bool | str | List[dict]]:
    staff_id = payload["staff_id"]
    guild_id = payload["guild_id"]

    try:
        async with sdb.execute(
            """
            SELECT strike_id, reason, date, issued_by_id
            FROM strikes
            WHERE issued_to_id = ? AND guild_id = ?
            ORDER BY strike_id DESC
            """,
            (staff_id, guild_id)
        ) as cursor:

            rows = await cursor.fetchall()

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
    
async def add_role_entries(payload: dict) -> Dict[str, str | bool]:
    try:
        guild_id = payload["guild_id"]
        roles = payload["roles"]

        cursor = await sdb.execute(
            "SELECT role_id FROM roles WHERE guild_id = ?",
            (guild_id,)
        )
        rows = await cursor.fetchall()

        concurrent_roles = tuple(role[0] for role in rows)

        await sdb.execute(
            "DELETE FROM roles WHERE guild_id = ?",
            (guild_id,)
        )

        if concurrent_roles:
            placeholders = ",".join("?" for _ in concurrent_roles)
            await sdb.execute(
                f"DELETE FROM staff_roles WHERE role_id IN ({placeholders})",
                concurrent_roles
            )

        priority = 0

        for item in roles:
            role_name = item["role_name"]
            role_id = item["role_id"]
            role_icon = item["role_icon"]

            await sdb.execute(
                """
                INSERT INTO roles 
                (guild_id, role_id, role_name, role_priority, ban_limit, role_icon)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (guild_id, role_id, role_name, priority, 0, role_icon)
            )

            priority += 1

        await sdb.commit()

        return {
            "success": True,
            "message": "Role hierarchy successfully set up!"
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
    
async def add_loa(payload: dict) -> Dict[str, Any]:
    guild_id = payload.get("guild_id")
    staff_id = payload.get("staff_id")
    reason = payload.get("reason")
    loa_issued_by = payload.get("loa_issued_by")

    if not staff_id:
        return {"success": False, "message": "Missing staff_id"}

    cursor = await sdb.execute(
        "SELECT on_loa FROM staffs WHERE staff_id = ?",
        (staff_id,)
    )

    row = await cursor.fetchone()

    if row and row["on_loa"] == 1:
        return {"success": False, "message": "Staff is already on LOA"}

    try:
        await sdb.execute("BEGIN")

        await sdb.execute(
            "UPDATE staffs SET on_loa = 1 WHERE staff_id = ?",
            (staff_id,)
        )

        await sdb.execute(
            """
            INSERT INTO leaves (staff_id, reason, issued_by)
            VALUES (?, ?, ?)
            """,
            (staff_id, reason, loa_issued_by)
        )

        rows = await sdb.execute_fetchall(
            "SELECT role_id FROM staff_roles WHERE staff_id = ?",
            (staff_id,)
        )
        roles_to_remove = tuple(row["role_id"] for row in rows)

        cursor = await sdb.execute(
            "SELECT loa_role FROM staff_configs WHERE guild_id = ?",
            (guild_id,)
        )

        config = await cursor.fetchone()

        roles_to_add = ()
        if config and config["loa_role"]:
            roles_to_add = (config["loa_role"],)

        await sdb.commit()

        return {
            "success": True,
            "message": "Staff added to LOA successfully!",
            "roles_to_remove": roles_to_remove,
            "roles_to_add": roles_to_add
        }

    except Exception as e:
        await sdb.execute("ROLLBACK")
        return {"success": False, "message": str(e)}

async def remove_loa(payload: dict) -> Dict[str, Any]:
    staff_id: int = payload.get("staff_id")
    guild_id: int = payload.get("guild_id")

    if not staff_id:
        return {"success": False, "message": "Missing staff_id"}

    try:
        await sdb.execute(
            "UPDATE staffs SET on_loa = 0 WHERE staff_id = ?", 
            (staff_id,)
        )


        cursor = await sdb.execute(
            "SELECT role_id FROM staff_roles WHERE staff_id = ?", 
            (staff_id,)
        )
        rows = await cursor.fetchall()

        roles_to_add = tuple(row[0] for row in rows)

        cursor = await sdb.execute(
            "SELECT loa_role FROM staff_configs WHERE guild_id = ?",
            (guild_id,)
        )

        config = await cursor.fetchone()

        roles_to_remove = ()
        if config and config["loa_role"]:
            roles_to_remove = (config["loa_role"],)

        await sdb.commit()

        return {
            "success": True,
            "message": "Staff removed from LOA successfully!",
            "roles_to_add": roles_to_add,
            "roles_to_remove" : roles_to_remove
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

async def fetch_loa_staffs(payload: dict) -> List[Dict[str, Any]]:
    guild_id: int = payload.get("guild_id")
    role_type: str = payload.get("role_type") 

    staff_loa: list = []

    cursor = await sdb.execute(
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

    rows = await cursor.fetchall()

    for staff_id, joined_on, avatar_url in rows:
        dt = datetime.strptime(joined_on or "01/01/2000", "%d/%m/%Y")

        staff_loa.append({
            "staff_id": staff_id,
            "joined_on": int(dt.timestamp()),
            "avatar_url": avatar_url
        })

    return staff_loa

async def update_staff(payload: dict) -> Dict[str, Any]:
    guild_id: int = payload.get("guild_id")
    staff_id: int = payload.get("staff_id")
    update_type: str = payload.get("update_type")
    reason: str = payload.get("reason")
    updated_by: int = payload.get("updated_by")

    if staff_id == updated_by:
        return {"success": False, "message": "You cannot update yourself."}

    if update_type not in ("promotion", "demotion"):
        return {"success": False, "message": "Invalid update_type."}

    cursor = await sdb.execute(
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

    current_role = await cursor.fetchone()

    if not current_role:
        return {"success": False, "message": "No staff role assigned."}

    sr_id = current_role[0]
    current_role_id = current_role[1]
    current_priority = current_role[2]

    cursor = await sdb.execute(
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

    updater_role = await cursor.fetchone()

    if not updater_role:
        return {"success": False, "message": "Updater has no staff role."}

    updater_priority = updater_role[0]

    if current_priority <= updater_priority:
        return {
            "success": False,
            "message": "You cannot update someone with equal or higher role."
        }

    if update_type == "promotion":
        cursor = await sdb.execute(
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

        next_role = await cursor.fetchone()
    else:
        cursor = await sdb.execute(
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

        next_role = await cursor.fetchone()

    if not next_role:
        return {
            "success": False,
            "message": f"Already at {'highest' if update_type == 'promotion' else 'lowest'} role."
        }

    new_role_id = next_role[0]
    new_priority = next_role[1]

    if new_priority < updater_priority:
        return {
            "success": False,
            "message": "You cannot update someone beyond your own role priority."
        }

    await sdb.execute("BEGIN")

    await sdb.execute(
        """
        UPDATE staff_roles
        SET role_id = ?
        WHERE id = ?
        """,
        (new_role_id, sr_id)
    )

    await sdb.execute(
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
        )
    )

    cursor = await sdb.execute(
        "SELECT staff_updates_channel FROM staff_configs WHERE guild_id = ?",
        (guild_id,)
    )

    row = await cursor.fetchone()

    await sdb.commit()

    return {
        "success": True,
        "message": f"{update_type.title()} successful",
        "old_role_id": current_role_id,
        "new_role_id": new_role_id,
        "staff_id": staff_id,
        "staff_updates_channel": row[0] if row else None
    }

async def add_staff_quota(payload: dict) -> Dict[str, Any]:
    pass