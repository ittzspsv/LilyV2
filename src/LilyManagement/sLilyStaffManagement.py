import discord
import aiosqlite
import asyncio

try:
    import Misc.sLilyComponentV2 as CS2
except:
    pass

from datetime import datetime
from discord.ext import commands

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

        review_channel = interaction.client.get_channel(1418140702163861504)
        if review_channel is None:
            await staff.send("⚠️ Review channel not found.")
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
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You don’t have permission to approve this.", ephemeral=True)
            return

        await AssignLoa(self.staff.id, self.reason, self.days)
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        await self.staff.send(f"✅ Your LOA request for **{self.days} days** has been approved. Good luck!")
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You don’t have permission to reject this.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        await self.staff.send(f"❌ Your LOA request for **{self.days} days** has been rejected.")
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

async def initialize():
    global sdb
    sdb = await aiosqlite.connect("storage/management/staff_management.db")

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
        SELECT s.name, r.role_name, s.on_loa, s.strikes_count, s.joined_on, s.timezone
        FROM staffs s
        LEFT JOIN roles r ON s.role_id = r.role_id
        WHERE s.staff_id = ?
        """
        cursor = await sdb.execute(query, (staff.id,))
        row = await cursor.fetchone()

        if not row:
            raise ValueError("Staff data not found in database.")

        name, role_name, is_loa, strikes_count, joined_on_str, timezone = row

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

        view = CS2.StaffDataComponent(
            name, 
            role_name or "N/A",
            "N/A",
            timezone or "Not Given",
            joined_on.strftime("%d/%m/%Y"),
            f"{years} years {months} months {days} days",
            strikes_count,
            staff.avatar.url,
            is_loa
        )
        return view

    except Exception as e:
        print(f"Error fetching staff detail: {e}")
        return CS2.EmptyView()

async def FetchAllStaffs():
    try:
        query = """
        SELECT s.staff_id, r.role_name, s.on_loa, r.role_priority
        FROM staffs s
        LEFT JOIN roles r ON s.role_id = r.role_id
        WHERE s.retired = 0
        ORDER BY r.role_priority ASC
        """
        async with sdb.execute(query) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            raise ValueError("No active staff data found in database.")

        embed = discord.Embed(
            title="STAFF LIST",
            description=f"**Total Count : {len(rows)}**",
            colour=0x3100f5
        )

        roles = {}
        active_moderators = 0
        loa_moderators = 0

        for staff_id, role_name, is_loa, role_priority in rows:
            mention = f"<@{staff_id}>"
            role_name = role_name or "Unknown Role"

            if role_name not in roles:
                roles[role_name] = {
                    "priority": role_priority if role_priority is not None else 999,
                    "mentions": []
                }

            roles[role_name]["mentions"].append(mention)

            if is_loa:
                loa_moderators += 1
            else:
                active_moderators += 1

        sorted_roles = sorted(
            roles.items(),
            key=lambda x: x[1]["priority"]
        )

        for role_name, data in sorted_roles:
            mentions = data["mentions"]
            count = len(mentions)
            embed.add_field(
                name=f"__{role_name}__ ({count})",
                value="- " + "\n- ".join(mentions),
                inline=False
            )

        analysis_text = (
            f"**Staff Active:** {active_moderators}\n"
            f"**Staffs in LOA:** {loa_moderators}"
        )
        embed.add_field(name="__ANALYSIS__", value=analysis_text, inline=False)

        return embed

    except Exception as e:
        return discord.Embed(title="Error", description=str(e), colour=0xf50000)

async def AddStaff(ctx: commands.Context, staff: discord.Member):
    staff_id = staff.id
    name = staff.display_name

    cursor = await sdb.execute("SELECT retired FROM staffs WHERE staff_id = ?", (staff_id,))
    row = await cursor.fetchone()

    top_role = None
    for role in sorted(staff.roles, key=lambda r: r.position, reverse=True):
        if role.is_default():
            continue
        top_role = role
        break

    if not top_role:
        await ctx.send(f"❌ Staff {staff.mention} has no assignable roles.")
        return

    cursor = await sdb.execute("SELECT role_id FROM roles WHERE role_id = ?", (top_role.id,))
    role_row = await cursor.fetchone()
    if not role_row:
        await ctx.send(f"Role {top_role.name} does not exist in the roles table.")
        return

    role_id = role_row[0]

    if row:
        retired = row[0]
        if retired:
            await sdb.execute(
                "UPDATE staffs SET retired = 0, role_id = ?, name = ? WHERE staff_id = ?",
                (role_id, name, staff_id)
            )
            await ctx.send(f"✅ Staff {staff.name} was retired and is now reactivated with updated role.")
        else:
            await sdb.execute(
                "UPDATE staffs SET role_id = ?, name = ? WHERE staff_id = ?",
                (role_id, name, staff_id)
            )
            await ctx.send(f"✅ Staff {staff.name}'s role has been updated.")
    else:
        await sdb.execute(
            "INSERT INTO staffs (staff_id, name, role_id, on_loa, strikes_count, retired) VALUES (?, ?, ?, 0, 0, 0)",
            (staff_id, name, role_id)
        )
        await ctx.send(f"✅ Staff {staff.name} has been added with role.")

    await sdb.commit()

async def RemoveStaff(ctx: commands.Context, staff_id: int):
    cursor = await sdb.execute("SELECT 1 FROM staffs WHERE staff_id = ?", (staff_id,))
    exists = await cursor.fetchone()

    if exists:
        await sdb.execute("UPDATE staffs SET retired = 1 WHERE staff_id = ?", (staff_id,))
        await sdb.commit()
        await ctx.send(f"✅ Staff with ID {staff_id} has been marked as retired.")
    else:
        await ctx.send(f"No staff found with ID {staff_id}.")

async def StrikeStaff(ctx: commands.Context, staff_id: str, reason: str):
    try:
        cursor = await sdb.execute("SELECT 1 FROM staffs WHERE staff_id = ?", (staff_id,))
        exists = await cursor.fetchone()

        if not exists:
            return discord.Embed(title="Staff Member Not Found", colour=0xf50000)

        await sdb.execute(
            "INSERT INTO strikes (issued_by_id, issued_to_id, reason, date) VALUES (?, ?, ?, ?)",
            (ctx.author.id, staff_id, reason, datetime.today().strftime("%d/%m/%Y"))
        )

        await sdb.execute(
            "UPDATE staffs SET strikes_count = strikes_count + 1 WHERE staff_id = ?",
            (staff_id,)
        )

        await sdb.commit()
        return discord.Embed(
            description=f"✅ **Successfully Striked Staff <@{staff_id}>**",
            colour=0xf50000
        )

    except Exception as e:
        return discord.Embed(title=f"Exception: {e}", colour=0xf50000)

async def RemoveStrikeStaff(ctx: commands.Context, strike_id: str):
    try:
        target_id = int(strike_id)

        cursor = await sdb.execute(
            "SELECT issued_to_id FROM strikes WHERE strike_id = ?",
            (target_id,)
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
            WHERE staff_id = ?
            """,
            (staff_id,)
        )

        await sdb.commit()

        return discord.Embed(
            description=f"✅ Strike {target_id} removed from <@{staff_id}>",
            colour=0x00ff00
        )

    except Exception as e:
        return discord.Embed(title=f"Exception: {e}", colour=0xf50000)

async def ListStrikes(staff: discord.Member):
    try:
        async with sdb.execute(
            "SELECT strike_id, reason, date, issued_by_id FROM strikes WHERE issued_to_id = ?",
            (str(staff.id),)
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return discord.Embed(
                title="No Strikes Found",
                description=f"No strikes found for {staff.mention}",
                colour=0xf50000
            ).set_thumbnail(url=staff.display_avatar.url)

        embed = discord.Embed(
            title=f"Strikes for {staff.display_name}",
            description=f"Listing all strikes issued to {staff.mention}",
            colour=0xf50000
        )
        embed.set_thumbnail(url=staff.display_avatar.url)

        for strike_id, reason, date, manager in rows:
            embed.add_field(
                name=f"__Strike ID: {strike_id}__",  # underline
                value=(
                    f"**Reason:** {reason}\n"
                    f"**Date:** {date}\n"
                    f"**Manager:** <@{manager}>"
                ),
                inline=False
            )

        embed.set_footer(text="Immutable Records Can only be removed by Higher Staffs")
        return embed

    except Exception as e:
        return discord.Embed(
            title=f"Exception: {e}",
            colour=0xf50000
        )
    
async def AssignLoa(staff_id: str, reason: str, days: int):
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
            WHERE staff_id = ?
            """,
            (staff_id,)
        )

        await sdb.commit()
        return True

    except Exception as e:
        print(f"Error assigning LOA: {e}")
        return False

async def RemoveLoa(staff_id: str):
    try:
        await sdb.execute(
            """
            UPDATE staffs
            SET on_loa = 0
            WHERE staff_id = ?
            """,
            (staff_id,)
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