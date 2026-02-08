import discord
import aiosqlite
import asyncio
from ast import literal_eval
import Config.sBotDetails as Configs
from enum import Enum
import LilyModeration.sLilyModeration as mLily

try:
    import Misc.sLilyComponentV2 as CS2
except:
    pass

from datetime import datetime
from discord.ext import commands
import LilyRulesets.sLilyRulesets as LilyRuleset

sdb = None

class LOAModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Request LOA")
        self.days = discord.ui.TextInput(
            label="Number of days",
            placeholder="Enter number of days",
            required=True
        )
        self.reason = discord.ui.TextInput(
            label="Reason",
            style=discord.TextStyle.paragraph,
            placeholder="Enter reason",
            required=True
        )
        self.add_item(self.days)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Your LOA request has been submitted!", ephemeral=True)

        days = int(self.days.value)
        reason = self.reason.value
        staff = interaction.user

        review_channel = interaction.client.get_channel(1421841285253431408)
        if review_channel is None:
            await staff.send("⚠️ Review channel not found. Contact a developer")
            return

        embed = discord.Embed(
            title="📝 LOA Request",
            description="A staff member has requested a Leave of Absence.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Staff", value=f"{staff.mention}", inline=True)
        embed.add_field(name="Days", value=str(days), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=staff.display_avatar.url if staff.display_avatar else "https://i.imgur.com/6VBx3io.png")
        embed.set_footer(text="Use the buttons below to approve or reject this request.")

        view = LOAReviewView(staff, reason, days)
        await review_channel.send(embed=embed, view=view)

class LOAReviewView(discord.ui.View):
    def __init__(self, staff, reason, days):
        super().__init__(timeout=86400)
        self.staff = staff
        self.reason = reason
        self.days = days

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            has_permission = await LilyRuleset.rPermissionEvaluator(
                interaction,
                PermissionType="role",
                RoleAllowed=lambda: GetRoles(('Developer', 'Staff Manager'))
            )
        except commands.CheckFailure as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        await AssignLoa(self.staff.id, self.reason, self.days)
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await self.staff.send(
            f"✅ Your LOA request for **{self.days} days** has been approved. Good luck!"
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            has_permission = await LilyRuleset.rPermissionEvaluator(
                interaction,
                PermissionType="role",
                RoleAllowed=lambda: GetRoles(('Developer', 'Staff Manager', 'TestRole'))
            )
        except commands.CheckFailure as e:
            await interaction.response.send_message(
                f"❌ {e}", ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()

        await self.staff.send(
            f"❌ Your LOA request for **{self.days} days** has been rejected."
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

async def initialize():
    global sdb
    sdb = await aiosqlite.connect("storage/management/staff_management.db")

    #DDL SCHEMA INITIALIZATION
    await sdb.execute("CREATE TABLE IF NOT EXISTS roles (role_id INTEGER PRIMARY KEY ,role_name TEXT NOT NULL UNIQUE,role_priority INTEGER NOT NULL, ban_limit INTEGER)")
    await sdb.commit()

async def GetRoles(role_names: tuple = ()):
    try:
        global sdb
        if not role_names:
            return []

        placeholders = ",".join("?" for _ in role_names)
        query = f"SELECT role_id FROM roles WHERE role_name IN ({placeholders})"
        
        cursor = await sdb.execute(query, role_names)
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
    except:
        return []

async def GetBanRoles():
    try:
        global sdb
        cursor = await sdb.execute("SELECT role_id FROM roles WHERE ban_limit > 0")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
    except:
        return []

async def GetAssignableRoles(roles):
    global sdb

    highest_allotment = None
    highest_position = -1

    for role in roles:
        try:
            cursor = await sdb.execute(
                "SELECT manage_role_allowances FROM roles WHERE role_id = ?",
                (role.id,)
            )
            row = await cursor.fetchone()
            await cursor.close()

            if row and row[0]:
                role_allotment = literal_eval(row[0])
                if role_allotment:
                    if role.position > highest_position:
                        highest_position = role.position
                        highest_allotment = role_allotment

        except Exception as e:
            print(f"Exception [GetAssignableRoles] for role {role.id}:", e)
            continue

    return highest_allotment or {}

async def run_query(ctx: commands.Context, query: str):
    try:
        cursor = await sdb.execute(query)

        try:
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
        except Exception:
            rows = None
            columns = []

        await sdb.commit()

        if rows:
            chunk_size = 5

            col_widths = []
            for i, col in enumerate(columns):
                max_len = max(len(str(row[i])) for row in rows) if rows else 0
                col_widths.append(max(len(col), max_len))

            header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
            separator = "-+-".join("-" * col_widths[i] for i in range(len(columns)))

            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i+chunk_size]
                lines = []
                for row in chunk:
                    line = " | ".join(str(row[j]).ljust(col_widths[j]) for j in range(len(columns)))
                    lines.append(line)
                table = "\n".join([header, separator] + lines)
                await ctx.send(f"```\n{table}\n```")
                await asyncio.sleep(0.5)
        else:
            await ctx.send("Execution Successful")

    except Exception as e:
        await ctx.send(f"Error: `{type(e).__name__}: {e}`")

async def FetchStaffDetail(staff: discord.Member):
    try:
        query = """
        SELECT s.name, r.role_name, s.on_loa, s.strikes_count, s.joined_on, s.timezone, s.responsibility, s.retired
        FROM staffs s
        LEFT JOIN roles r ON s.role_id = r.role_id
        WHERE s.staff_id = ?
        """
        cursor = await sdb.execute(query, (staff.id,))
        row = await cursor.fetchone()

        if not row:
            raise ValueError("Staff data not found in database.")

        name, role_name, is_loa, strikes_count, joined_on_str, timezone, responsibility, retired = row

        joined_on = datetime.strptime(joined_on_str, "%d/%m/%Y")
        current_date = datetime.today()

        years = current_date.year - joined_on.year
        months = current_date.month - joined_on.month
        days = current_date.day - joined_on.day

        if days < 0:
            months -= 1
            days += 30
        if months < 0:
            years -= 1
            months += 12

        if is_loa == 1:
            status_display = f"{Configs.emoji['dnd']} On Leave"
        elif retired == 1:
            status_display = f"{Configs.emoji['invisible']} Retired"
        else:
            status_display = f"{Configs.emoji['online']} Active"

        embed = discord.Embed(
            color=0xFFFFFF,
            title=f"{name}'s Profile",
        )

        embed.set_thumbnail(url=staff.avatar.url if staff.avatar else staff.default_avatar.url)
        embed.set_image(url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png?format=webp&quality=lossless")

        embed.add_field(
            name="__Basic Information__",
            value=(
                f"{Configs.emoji['shield']} **Role:** {role_name or 'N/A'}\n"
                f"{Configs.emoji['bookmark']} **Responsibilities:** {responsibility or 'N/A'}\n"
                f"{Configs.emoji['clock']} **Timezone:** {timezone or 'N/A'}\n"
                f"{Configs.emoji['calender']} **Join Date:** {joined_on.strftime('%d/%m/%Y') or '0/0/0000'}"
            ),
            inline=False,
        )

        embed.add_field(
            name="__Experience Information__",
            value=(
                f"{Configs.emoji['clock']} **Evaluated Experience:** "
                f"**{years} years {months} months {days} days**"
            ),
            inline=False,
        )

        embed.add_field(
            name="__Strikes Information__",
            value=f"{Configs.emoji['logs']} **Strike Count:** **{strikes_count}**",
            inline=False,
        )

        embed.add_field(
            name="__Status__",
            value=f"{status_display}\n",
            inline=False,
        )
        return embed


    except Exception as e:
        print(f"Error fetching staff detail: {e}")
        return discord.Embed(
            color=0xFF0000,
            description=f"{Configs.emoji['cross']} failed to fetch staff data. please check the database.",
        )

async def FetchAllStaffs(ctx: commands.Context):
    try:
        guild_id = ctx.guild.id

        count_query = """
        SELECT 
            COUNT(*) AS total_staffs,
            SUM(CASE WHEN s.on_loa = 1 THEN 1 ELSE 0 END) AS loa_staffs,
            SUM(CASE WHEN s.on_loa = 0 THEN 1 ELSE 0 END) AS active_staffs
        FROM staffs s
        WHERE s.retired = 0 AND s.guild_id = ?
        """
        cursor = await sdb.execute(count_query, (guild_id,))
        total_staffs, loa_staffs, active_staffs = await cursor.fetchone()

        staff_roles_query = """
        SELECT s.staff_id, s.name, r.role_name, r.role_priority
        FROM staffs s
        JOIN staff_roles sr ON sr.staff_id = s.staff_id
        JOIN roles r ON r.role_id = sr.role_id
        WHERE s.retired = 0 AND s.guild_id = ? AND r.role_type = 'Staff'
        ORDER BY r.role_priority ASC
        """
        cursor = await sdb.execute(staff_roles_query, (guild_id,))
        staff_rows = await cursor.fetchall()


        responsibility_query = """
            SELECT s.staff_id, s.name, r.role_name
            FROM staffs s
            JOIN staff_roles sr ON sr.staff_id = s.staff_id
            JOIN roles r ON r.role_id = sr.role_id
            WHERE s.retired = 0 AND s.guild_id = ? AND r.role_type = 'Responsibility'
            ORDER BY r.role_name ASC
        """
        cursor = await sdb.execute(responsibility_query, (guild_id,))
        resp_rows = await cursor.fetchall()

        staff_roles = {}
        for staff_id, name, role_name, role_priority in staff_rows:
            mention = f"<@{staff_id}>"
            if role_name not in staff_roles:
                staff_roles[role_name] = {
                    "priority": role_priority if role_priority is not None else 999,
                    "mentions": []
                }
            staff_roles[role_name]["mentions"].append(mention)

        staff_embed = discord.Embed(
            title=f"{Configs.emoji['arrow']} Staff Hierarchy",
            colour=16777215
        ).set_thumbnail(
            url="https://media.discordapp.net/attachments/1366840025010012321/1438090416628043866/shield.png?format=webp&quality=lossless"
        ).set_image(
            url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png?format=webp&quality=lossless"
        )

        sorted_staff_roles = sorted(staff_roles.items(), key=lambda x: x[1]["priority"])
        for role_name, data in sorted_staff_roles:
            mentions = data["mentions"]
            count = len(mentions)
            staff_embed.add_field(
                name=f"__{role_name}__ ({count})",
                value="- " + "\n- ".join(mentions),
                inline=False
            )

        responsibilities = {}
        for staff_id, name, role_name in resp_rows:
            mention = f"<@{staff_id}>"
            if role_name not in responsibilities:
                responsibilities[role_name] = []
            responsibilities[role_name].append(mention)

        resp_embed = discord.Embed(
            title=f"{Configs.emoji['arrow']} Responsibilities",
            colour=16777215
        ).set_thumbnail(
            url="https://media.discordapp.net/attachments/1366840025010012321/1438064934574493768/logs.png?format=webp&quality=lossless"
        ).set_image(
            url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png?format=webp&quality=lossless"
        )

        for role_name, mentions in sorted(responsibilities.items()):
            resp_embed.add_field(
                name=f"__{role_name}__ ({len(mentions)})",
                value="- " + "\n- ".join(mentions),
                inline=False
            )

        overview_embed = discord.Embed(
            title=f"{Configs.emoji['arrow']} Staff Overview",
            colour=16777215
        ).set_thumbnail(
            url="https://media.discordapp.net/attachments/1366840025010012321/1438064934574493768/logs.png?format=webp&quality=lossless"
        ).set_image(
            url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png?format=webp&quality=lossless"
        ).add_field(
            name="On LOA", value=f"**{loa_staffs}**", inline=True
        ).add_field(
            name="Active Staffs", value=f"**{active_staffs}**", inline=True
        ).add_field(
            name="Total Staffs", value=f"**{total_staffs}**", inline=True
        )

        return [overview_embed, staff_embed, resp_embed]

    except Exception as e:
        print(f"Error fetching staff list: {e}")
        return [
            discord.Embed(
                title=f"{Configs.emoji['cross']} Error",
                description="Failed to fetch staff data. Please check the database.",
                colour=0xf50000
            )
        ]

async def AddStaff(ctx: commands.Context, staff: discord.Member):
    staff_id = staff.id
    name = staff.display_name
    guild_id = ctx.guild.id

    async with sdb.execute("BEGIN IMMEDIATE"):
        cursor = await sdb.execute("""
            SELECT retired
            FROM staffs
            WHERE staff_id = ? AND guild_id = ?
        """, (staff_id, guild_id))
        row = await cursor.fetchone()

        cursor = await sdb.execute("""
            SELECT role_id, role_type
            FROM roles
        """)
        db_roles = await cursor.fetchall()

        staff_role_ids = {r[0] for r in db_roles if r[1] == "Staff"}
        responsibility_role_ids = {r[0] for r in db_roles if r[1] == "Responsibility"}

        top_staff_role = None
        for role in sorted(staff.roles, key=lambda r: r.position, reverse=True):
            if role.id in staff_role_ids:
                top_staff_role = role
                break

        discord_responsibilities = {
            role.id for role in staff.roles
            if role.id in responsibility_role_ids
        }

        if row:
            if row[0] == 1:
                await sdb.execute("""
                    UPDATE staffs
                    SET retired = 0, name = ?
                    WHERE staff_id = ? AND guild_id = ?
                """, (name, staff_id, guild_id))
            else:
                await sdb.execute("""
                    UPDATE staffs
                    SET name = ?
                    WHERE staff_id = ? AND guild_id = ?
                """, (name, staff_id, guild_id))
        else:
            await sdb.execute("""
                INSERT INTO staffs (
                    staff_id, name, guild_id,
                    on_loa, strikes_count, retired,
                    Timezone, responsibility
                )
                VALUES (?, ?, ?, 0, 0, 0, 'Default', 'None')
            """, (staff_id, name, guild_id))

        if top_staff_role:
            await sdb.execute("""
                DELETE FROM staff_roles
                WHERE staff_id = ?
                  AND role_id IN (
                    SELECT role_id FROM roles WHERE role_type = 'Staff'
                  )
            """, (staff_id,))

            await sdb.execute("""
                INSERT INTO staff_roles (staff_id, role_id)
                VALUES (?, ?)
            """, (staff_id, top_staff_role.id))

        cursor = await sdb.execute("""
            SELECT sr.role_id
            FROM staff_roles sr
            JOIN roles r ON r.role_id = sr.role_id
            WHERE sr.staff_id = ? AND r.role_type = 'Responsibility'
        """, (staff_id,))
        db_responsibilities = {r[0] for r in await cursor.fetchall()}

        to_add = discord_responsibilities - db_responsibilities
        to_remove = db_responsibilities - discord_responsibilities

        if to_remove:
            await sdb.executemany("""
                DELETE FROM staff_roles
                WHERE staff_id = ? AND role_id = ?
            """, [(staff_id, rid) for rid in to_remove])

        if to_add:
            await sdb.executemany("""
                INSERT INTO staff_roles (staff_id, role_id)
                VALUES (?, ?)
            """, [(staff_id, rid) for rid in to_add])

    await sdb.commit()

    if top_staff_role:
        embed_text = f"Staff synced successfully with <@&{top_staff_role.id}> | responsible for {len(discord_responsibilities)} actions"
        await ctx.send(embed=mLily.SimpleEmbed(embed_text))
    elif discord_responsibilities:
        embed_text = f"User has no staff role but is responsible for {len(discord_responsibilities)} actions"
        await ctx.send(embed=mLily.SimpleEmbed(embed_text))
    else:
        embed_text = "User has no staff role or responsibilities"
        await ctx.send(embed=mLily.SimpleEmbed(embed_text, 'cross'))

async def RemoveStaff(ctx: commands.Context, staff_id: int):
    guild_id = ctx.guild.id

    try:
        async with sdb.execute("BEGIN IMMEDIATE"):
            cursor = await sdb.execute("""
                SELECT retired
                FROM staffs
                WHERE staff_id = ? AND guild_id = ?
            """, (staff_id, guild_id))
            row = await cursor.fetchone()

            if not row:
                raise LookupError("Staff not found")

            await sdb.execute("""
                UPDATE staffs
                SET retired = 1
                WHERE staff_id = ? AND guild_id = ?
            """, (staff_id, guild_id))

            await sdb.execute("""
                DELETE FROM staff_roles
                WHERE staff_id = ?
            """, (staff_id,))

        await sdb.commit()

        await ctx.send(
            embed=mLily.SimpleEmbed(
                f"Staff <@{staff_id}> has been marked as **Retired**"
            )
        )

    except LookupError:
        await ctx.send(
            embed=mLily.SimpleEmbed(
                f"No staff found with ID `{staff_id}`.",
                'cross'
            )
        )

    except Exception as e:
        print(f"Exception [RemoveStaff] {e}")
        await sdb.rollback()
        raise

async def EditStaff(ctx: commands.Context, staff_id: int, name: str = None, role_id: int = None, joined_on: str = None, timezone: str = None, responsibility: str = None):
    try:
        cursor = await sdb.execute("SELECT 1 FROM staffs WHERE staff_id = ? AND guild_id = ?", (staff_id, ctx.guild.id))
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            await ctx.send(embed=mLily.SimpleEmbed(f"No staff found with ID {staff_id}.", 'cross'))
            return

        fields = {
            "name": name,
            "role_id": role_id,
            "joined_on": joined_on,
            "timezone": timezone,
            "responsibility": responsibility
        }
        update_columns = {k: v for k, v in fields.items() if v is not None}

        if not update_columns:
            await ctx.send(embed=mLily.SimpleEmbed(f"No Fields Provided to update", 'cross'))
            return

        set_clause = ", ".join([f"{col} = ?" for col in update_columns.keys()])
        values = list(update_columns.values())
        values.append(staff_id)
        values.append(ctx.guild.id)

        query = f"UPDATE staffs SET {set_clause} WHERE staff_id = ? AND guild_id = ?"
        await sdb.execute(query, values)
        await sdb.commit()

        await ctx.send(embed=mLily.SimpleEmbed(f"Staff ID {staff_id} updated successfully."))
    except Exception as e:
        await ctx.send(embed=mLily.SimpleEmbed(f"Error Updating Staff Details", 'cross'))
        print(e)

async def StrikeStaff(ctx: commands.Context, staff_id: str, reason: str):
    try:
        cursor = await sdb.execute("SELECT 1 FROM staffs WHERE staff_id = ? AND guild_id = ?", (staff_id,ctx.guild.id))
        exists = await cursor.fetchone()

        if not exists:
            return discord.Embed(title="Staff Member Not Found", colour=0xf50000)

        await sdb.execute(
            "INSERT INTO strikes (issued_by_id, issued_to_id, reason, date, guild_id) VALUES (?, ?, ?, ?, ?)",
            (ctx.author.id, staff_id, reason, datetime.today().strftime("%d/%m/%Y"), ctx.guild.id)
        )

        await sdb.execute(
            "UPDATE staffs SET strikes_count = strikes_count + 1 WHERE staff_id = ? AND guild_id = ?",
            (staff_id,ctx.guild.id)
        )

        await sdb.commit()
        return mLily.SimpleEmbed(f'**Successfully Striked Staff <@{staff_id}>**')

    except Exception as e:
        return mLily.SimpleEmbed(f'Exception : {e}', 'cross')

async def RemoveStrikeStaff(ctx: commands.Context, strike_id: str):
    try:
        target_id = int(strike_id)

        cursor = await sdb.execute(
            "SELECT issued_to_id FROM strikes WHERE strike_id = ? AND guild_id = ?",
            (target_id,ctx.guild.id)
        )
        row = await cursor.fetchone()

        if not row:
            return discord.Embed(
                title="Strike Not Found",
                description=f"No strike with ID `{target_id}` found.",
                colour=0xf50000
            )

        staff_id = row[0]

        await sdb.execute("DELETE FROM strikes WHERE strike_id = ?", (target_id,))

        await sdb.execute(
            """
            UPDATE staffs
            SET strikes_count = CASE 
                WHEN strikes_count > 0 THEN strikes_count - 1 
                ELSE 0 
            END
            WHERE staff_id = ? AND guild_id = ?
            """,
            (staff_id, ctx.guild.id)
        )

        await sdb.commit()

        return mLily.SimpleEmbed(f"Strike `{target_id}` removed from <@{staff_id}>")

    except Exception as e:
        return mLily.SimpleEmbed(f"Exception: {e}", 'cross')

async def ListStrikes(ctx: commands.Context, staff: discord.Member):
    try:
        async with sdb.execute(
            "SELECT strike_id, reason, date, issued_by_id FROM strikes WHERE issued_to_id = ? AND guild_id = ?",
            (str(staff.id),ctx.guild.id)
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            embed = (
                discord.Embed(
                    color=0xf50000,
                    title=f"{Configs.emoji['cross']} No Strikes Found",
                    description=f"No strikes found for {staff.mention}.",
                )
                .set_thumbnail(url=staff.display_avatar.url or Configs.img['member'])
                .set_footer(text="Immutable Records • Managed by Lily System")
            )
            return embed


        embed = (
            discord.Embed(
                color=0xFFFFFF,
                title=f"{Configs.emoji['arrow']} {staff.display_name}'s Strike Information",
                description=f"{Configs.emoji['bookmark']} Listing all strikes issued to {staff.mention}",
            )
            .set_thumbnail(url=staff.display_avatar.url)
            .set_image(
                url=Configs.img['border']
            )
        )

        for strike_id, reason, date, manager in rows:
            embed.add_field(
                name=f"{Configs.emoji['pencil']} __Strike ID: {strike_id}__",
                value=(
                    f"> {Configs.emoji['bookmark']} **Reason** : {reason}\n"
                    f"> {Configs.emoji['shield']} **Manager** : <@{manager}>\n"
                    f"> {Configs.emoji['calender']} **Date** : {date}"
                ),
                inline=False,
            )

        embed.set_footer(text="Immutable Records • Can only be removed by higher staff")
        return embed

    except Exception as e:
        return discord.Embed(
            title=f"{Configs.emoji['cross']} Exception Occurred",
            description=f"```{e}```",
            colour=0xf50000
        )

async def AssignLoa(ctx: commands.Context, staff_id: str, reason: str, days: int):
    try:
        await sdb.execute(
            """
            INSERT INTO leaves (staff_id, reason, days)
            VALUES (?, ?, ?)
            """,
            (staff_id, reason, days)
        )

        await sdb.execute(
            """
            UPDATE staffs
            SET on_loa = 1
            WHERE staff_id = ? AND guild_id = ?
            """,
            (staff_id,ctx.guild.id)
        )

        await sdb.commit()
        return True

    except Exception as e:
        print(f"Error assigning LOA: {e}")
        return False

async def RemoveLoa(ctx: commands.Context, staff_id: str):
    try:
        await sdb.execute(
            """
            UPDATE staffs
            SET on_loa = 0
            WHERE staff_id = ? AND guild_id = ?
            """,
            (staff_id,ctx.guild.id)
        )

        await sdb.commit()
        return True

    except Exception as e:
        print(f"Error removing LOA: {e}")
        return False

async def RequestLoa(ctx: commands.Context):
    interaction = getattr(ctx, "interaction", None)
    if interaction:
        await interaction.response.send_modal(LOAModal())
    else:
        await ctx.send("Opening LOA request modal...")
        await ctx.send_modal(LOAModal())

class RoleType(str, Enum):
        Staff = "Staff"
        Responsibility = "Responsibility"

async def AddRole(ctx: commands.Context, role: discord.Role, ban_limit: int, role_type: RoleType):
    try:
        cursor = await sdb.execute(
            "SELECT role_id, role_priority FROM roles WHERE guild_id = ? ORDER BY role_priority ASC",
            (ctx.guild.id,)
        )
        db_roles = await cursor.fetchall()

        role_list = []
        for db_role_id, db_priority in db_roles:
            db_role = ctx.guild.get_role(db_role_id)
            if db_role:
                role_list.append((db_role_id, db_priority, db_role.position))

        insert_index = 0
        for i, (_, _, discord_pos) in enumerate(role_list):
            if role.position > discord_pos:
                break
            insert_index += 1

        for i in range(insert_index, len(role_list)):
            db_role_id = role_list[i][0]
            await sdb.execute(
                "UPDATE roles SET role_priority = role_priority + 1 WHERE role_id = ?",
                (db_role_id,)
            )

        await sdb.execute(
            "INSERT INTO roles (role_id, role_name, role_priority, ban_limit, role_type, guild_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (role.id, role.name, insert_index, ban_limit, role_type.value, ctx.guild.id)
        )

        await sdb.commit()

        await ctx.send(
            embed=mLily.SimpleEmbed(f"Successfully Added {role.name} at priority {insert_index}")
        )
    except Exception as e:
        await ctx.send(
            embed=mLily.SimpleEmbed(f"Error Adding {role.name}: {e}", 'cross')
        )

async def GetAllStaffRoles(ctx: commands.Context):
    try:
        cursor = await sdb.execute(
            "SELECT role_id, role_name FROM roles WHERE guild_id = ? ORDER BY role_priority ASC",
            (ctx.guild.id,)
        )
        rows = await cursor.fetchall()

        if not rows:
            await ctx.send(embed=mLily.SimpleEmbed("No staff roles found in this guild.", 'cross'))
            return

        role_names = []
        role_mentions = []

        for role_id, role_name in rows:
            role = ctx.guild.get_role(role_id)
            if role:
                role_names.append(role.name)
                role_mentions.append(role.mention)
            else:
                role_names.append(role_name)
                role_mentions.append(f"<@&{role_id}>")

        embed = discord.Embed(
            title="Permission Assigned Roles",
            colour=0xffffff
        )
        embed.add_field(name="Role Names", value="\n".join(role_names), inline=True)
        embed.add_field(name="Role Reference", value="\n".join(role_mentions), inline=True)

        await ctx.send(embed=embed)

    except Exception as e:
        print(f"Exception [GetAllStaffRoles] {e}")
        await ctx.send(embed=mLily.SimpleEmbed(f"Error fetching staff roles", 'cross'))