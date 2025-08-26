import json
import discord
import aiosqlite
import pandas as pd
import asyncio
import ast
try:
    import Misc.sLilyComponentV2 as CS2
except:
    pass

from datetime import datetime
from discord.ext import commands

sdb = None

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
        resultant = await sdb.execute(
            "SELECT name, role, responsibility, join_date, strikes FROM staff_data WHERE staff_id = ?",
            (staff.id,)
        )
        row = await resultant.fetchone()

        if not row:
            raise ValueError("Staff data not found in database.")

        name, role, responsibility, join_date, strikes = row

        start_date = datetime.strptime(join_date, "%d/%m/%Y")
        current_date = datetime.today()

        years = current_date.year - start_date.year
        months = current_date.month - start_date.month
        days = current_date.day - start_date.day

        if days < 0:
            months -= 1
            days += 30
        if months < 0:
            years -= 1
            months += 12

        if isinstance(strikes, str):
            try:
                strikes_list = json.loads(strikes)  # JSON string
                strike_count = len(strikes_list)
            except json.JSONDecodeError:
                strike_count = int(strikes) if strikes.isdigit() else 0
        elif isinstance(strikes, int):
            strike_count = strikes
        else:
            strike_count = 0
        view = CS2.StaffDataComponent(name, role, responsibility, join_date, f"{years} years {months} months {days} days", strike_count, staff.avatar.url)
        '''
        embed = discord.Embed(title=name.title(), colour=0xf50000)
        embed.add_field(name="Role", value=role, inline=False)
        embed.add_field(name="Responsibilities", value=responsibility, inline=False)
        embed.add_field(name="Join Date", value=join_date, inline=False)
        embed.add_field(
            name="Evaluated Experience In Server",
            value=f"{years} years {months} months {days} days",
            inline=False
        )
        embed.add_field(name="Strike Count", value=strike_count, inline=False)
        embed.set_thumbnail(url=staff.avatar.url)
        '''
        return view

    except Exception as e:
        return CS2.EmptyView()

async def FetchAllStaffs():
    try:
        async with sdb.execute(
            "SELECT staff_id, role, LOA, higher_staff FROM staff_data"
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            raise ValueError("No staff data found in database.")

        embed = discord.Embed(
            title="STAFF LIST",
            description=f"**Total Count : {len(rows)}**",
            colour=0x3100f5
        )

        roles = {}
        active_moderators = 0
        loa_moderators = 0

        for staff_id, role, loa, higher_staff in rows:
            mention = f"<@{staff_id}>"

            if role not in roles:
                roles[role] = []
            roles[role].append(mention)

            if loa:
                loa_moderators += 1
            elif not higher_staff and not loa:
                active_moderators += 1

        role_priority = ("")
        for role, mentions in roles.items():
            count = len(mentions)
            names_with_bullet = "- " + "\n- ".join(mentions)
            embed.add_field(
                name=f"__{role}__ ({count})",
                value=names_with_bullet,
                inline=False
            )

        analysis_text = (
            f"**Staff Prioritized on Moderation:** {active_moderators}\n"
            f"**Staffs in LOA:** {loa_moderators}"
        )
        embed.add_field(
            name="__ANALYSIS__",
            value=analysis_text,
            inline=False
        )

        return embed

    except Exception as e:
        return discord.Embed(title="Error", description=str(e), colour=0xf50000)

async def StrikeStaff(ctx: commands.Context, staff_id: str, reason: str):
    try:
        cursor_strikes = await sdb.execute(
            "SELECT strikes FROM staff_data WHERE staff_id = ?", 
            (staff_id,)
        )
        values = await cursor_strikes.fetchall()

        if not values:
            embed = discord.Embed(
                title="Staff Member Not Found",
                colour=0xf50000
            )
            return embed
        strike_data = ast.literal_eval(values[0][0])

        strike = {
            "reason": reason,
            "date": datetime.today().strftime("%d/%m/%Y"),
            "manager": ctx.author.id
        }
        strike_data.append(strike)

        await sdb.execute(
            "UPDATE staff_data SET strikes = ? WHERE staff_id = ?", 
            (str(strike_data), staff_id)
        )
        await sdb.commit()

        embed = discord.Embed(
            description=f"**Successfully Striked Staff <@{staff_id}>**",
            colour=0xf50000
        )
        return embed

    except Exception as e:
        embed = discord.Embed(
            title=f"Exception: {e}",
            colour=0xf50000
        )
        return embed
    
async def ListStrikes(staff_id: str):
    try:
        async with sdb.execute("SELECT strikes FROM staff_data WHERE staff_id = ?", (staff_id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            return discord.Embed(
                title="Staff Member Not Found",
                description=f"No data found for <@{staff_id}>",
                colour=0xf50000
            )

        strikes = ast.literal_eval(row[0]) if row[0] else []

        embed = discord.Embed(
            title="Strikes",
            description=f"Showing for <@{staff_id}>",
            colour=0xf50000
        )

        for idx, strike in enumerate(strikes, start=1):
            embed.add_field(
                name=f"Strike {idx}",
                value=(
                    f"**Reason     : {strike['reason']}**\n"
                    f"**Date       : {strike['date']}**\n"
                    f"**Manager    : <@{strike['manager']}>**"
                ),
                inline=False
            )

        return embed

    except Exception as e:
        return discord.Embed(
            title=f"Exception : {e}",
            colour=0xf50000
        )