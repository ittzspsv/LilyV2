import discord
from ast import literal_eval
import Config.sBotDetails as Configs
import LilyManagement.types.sLilyStaffManagementTypes as types
import re

import Config.sBotDetails as Configs

import asyncio

from typing import Optional
from Misc.sLilyEmbed import simple_embed


from LilyManagement.db.sLilyStaffDatabaseAccess import fetch_staff_detail, fetch_all_staffs, add_staff, remove_staff, edit_staff, strike_staff, remove_strike, fetch_staff_strikes, add_loa, remove_loa, update_staff, add_staff_quota, remove_staff_quota, fetch_staff_quota, get_staff_current_quota, remove_role, reset_messages, get_all_staff_quota_status
import LilyManagement.db.sLilyStaffDatabaseAccess as LSDA

from LilyManagement.components.sLilyStaffManagementComponents import StaffsView, StaffRoleView

from discord.ext import commands


async def GetRoles(role_names: tuple = ()):
    try:
        if not role_names:
            return []

        placeholders = ",".join("?" for _ in role_names)
        query = f"SELECT role_id FROM roles WHERE role_name IN ({placeholders})"
        
        cursor = await LSDA.sdb.execute(query, role_names)
        rows = await cursor.fetchall()

        return [row[0] for row in rows]
    except Exception as e:
        print(f"Exception [GetRoles] {e}")
        return []

async def GetBanRoles():
    try:
        cursor = await LSDA.sdb.execute("SELECT role_id FROM roles WHERE ban_limit > 0")
        rows = await cursor.fetchall()

        return [row[0] for row in rows]
    except Exception as e:
        print(f"Exception [GetRoles] {e}")
        return []

async def GetAssignableRoles(roles):
    highest_allotment = None
    highest_position = -1

    for role in roles:
        try:
            cursor = await LSDA.sdb.execute(
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

async def FetchStaffDetail(staff: discord.Member):
    try:
        data_dict = await fetch_staff_detail(staff.id)
        if not data_dict:
            raise ValueError("Staff data not found in database.")

        name, role_name, is_loa, strikes_count, joined_on_str, timezone, responsibility, retired = (
            data_dict.get("name"), data_dict.get("role_name"), data_dict.get("is_loa"), data_dict.get("strikes_count"), 
            data_dict.get("joined_on"), data_dict.get("timezone"), data_dict.get("responsibility"), data_dict.get("retired")
        )

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
                f"{Configs.emoji['shield']} **Role:** {','.join(role_name) or 'N/A'}\n"
                f"{Configs.emoji['bookmark']} **Responsibilities:** {responsibility or 'N/A'}\n"
                f"{Configs.emoji['clock']} **Timezone:** {timezone or 'N/A'}\n"
                f"{Configs.emoji['calender']} **Join Date:** <t:{joined_on_str}:D>"
            ),
            inline=False,
        )

        embed.add_field(
            name="__Experience Information__",
            value=(
                f"{Configs.emoji['clock']} **Evaluated Experience:** "
                f"<t:{joined_on_str}:R>"
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
        data = await fetch_all_staffs(ctx.guild.id)

        overall_details = data["overall"]
        role_user_map = data["roles"]

        view = StaffsView(ctx, overall_details, role_user_map)
        view.message = await ctx.reply(view=view)

    except Exception as e:
        print(f"Error fetching staff list: {e}")

        embed = discord.Embed(
            title=f"{Configs.emoji['cross']} Error",
            description="Failed to fetch staff data. Please check the database.",
            colour=0xf50000
        )

        await ctx.reply(embed=embed)

async def update_all_staffs(ctx: commands.Context):
    guild_id = ctx.guild.id

    cursor = await LSDA.sdb.execute(
        "SELECT staff_id FROM staffs WHERE retired = 0 AND on_loa = 0 AND guild_id = ?",
        (guild_id,)
    )
    rows = await cursor.fetchall()
    staff_ids = [row[0] for row in rows]

    cursor = await LSDA.sdb.execute("""
        SELECT role_id, role_type
        FROM roles
        WHERE guild_id = ?
    """, (guild_id,))
    db_roles = await cursor.fetchall()

    staff_role_ids = {r[0] for r in db_roles if r[1] == "Staff"}
    responsibility_role_ids = {r[0] for r in db_roles if r[1] == "Responsibility"}

    for staff_id in staff_ids:

        staff_member = ctx.guild.get_member(staff_id)

        if not staff_member:
            try:
                staff_member = await ctx.guild.fetch_member(staff_id)
            except discord.NotFound:
                continue

        try:

            top_staff_role = None

            for role in reversed(staff_member.roles):
                if role.id in staff_role_ids:
                    top_staff_role = role
                    break

            discord_responsibilities = {
                role.id for role in staff_member.roles
                if role.id in responsibility_role_ids
            }

            await LSDA.sdb.execute(
                "DELETE FROM staff_roles WHERE staff_id = ?",
                (staff_id,)
            )

            if top_staff_role is None and not discord_responsibilities:
                await LSDA.sdb.execute("""
                    UPDATE staffs
                    SET retired = 1
                    WHERE staff_id = ? AND guild_id = ?
                """, (staff_id, guild_id))

                continue

            await LSDA.sdb.execute("""
                UPDATE staffs
                SET retired = 0, avatar_url = ?
                WHERE staff_id = ? AND guild_id = ?
            """, (staff_member.display_avatar.url, staff_id, guild_id))

            await LSDA.sdb.execute("""
                INSERT INTO staff_roles (staff_id, role_id)
                VALUES (?, ?)
            """, (staff_id, top_staff_role.id))

            if discord_responsibilities:
                await LSDA.sdb.executemany("""
                    INSERT INTO staff_roles (staff_id, role_id)
                    VALUES (?, ?)
                """, [(staff_id, rid) for rid in discord_responsibilities])

            print(f"[Update_All_Staffs] Updated {staff_member.name}")

        except Exception as e:
            print(f"Exception [Update_All_Staffs] {e}")
            continue

        await asyncio.sleep(1)

    await LSDA.sdb.commit()
    await ctx.reply(embed=simple_embed(f"Updated Every staff roles on the Database!"))

'''
async def update_staff(ctx: commands.Context, staff: discord.Member):
    guild_id = ctx.guild.id
    staff_id = staff.id

    try:
        cursor = await LSDA.sdb.execute(
            "SELECT 1 FROM staffs WHERE staff_id = ? AND guild_id = ?",
            (staff_id, guild_id)
        )
        exists = await cursor.fetchone()

        if not exists:
            return

        cursor = await LSDA.sdb.execute("""
            SELECT role_id, role_type
            FROM roles
            WHERE guild_id = ?
        """, (guild_id,))
        db_roles = await cursor.fetchall()

        staff_role_ids = {r[0] for r in db_roles if r[1] == "Staff"}
        responsibility_role_ids = {r[0] for r in db_roles if r[1] == "Responsibility"}


        top_staff_role = None
        for role in reversed(staff.roles):
            if role.id in staff_role_ids:
                top_staff_role = role
                break

        discord_responsibilities = {
            role.id for role in staff.roles
            if role.id in responsibility_role_ids
        }


        await LSDA.sdb.execute(
            "DELETE FROM staff_roles WHERE staff_id = ?",
            (staff_id,)
        )

        if not top_staff_role:
            await LSDA.sdb.execute("""
                UPDATE staffs
                SET retired = 1
                WHERE staff_id = ? AND guild_id = ?
            """, (staff_id, guild_id))

            await LSDA.sdb.commit()
            return

        await LSDA.sdb.execute("""
            UPDATE staffs
            SET retired = 0
            WHERE staff_id = ? AND guild_id = ?
        """, (staff_id, guild_id))

        await LSDA.sdb.execute("""
            INSERT INTO staff_roles (staff_id, role_id)
            VALUES (?, ?)
        """, (staff_id, top_staff_role.id))

        if discord_responsibilities:
            await LSDA.sdb.executemany("""
                INSERT INTO staff_roles (staff_id, role_id)
                VALUES (?, ?)
            """, [(staff_id, rid) for rid in discord_responsibilities])

        await LSDA.sdb.commit()
        await ctx.reply(embed=simple_embed(f"Updated {staff.mention} role on the Database!"))

    except Exception as e:
        print(f"Exception [Update_Staff] {e}")
''' 
async def AddStaff(ctx: commands.Context, staff: discord.Member):
    payload = {
        "staff_id": staff.id,
        "guild_id": ctx.guild.id,
        "name": staff.display_name,
        "avatar_url": staff.avatar.url if staff.avatar else None
    }

    response = await add_staff(payload)

    if not response.get("success"):
        await ctx.reply(embed=simple_embed(response.get("message"), "cross"))
        return

    roles_to_add = set(response.get("roles_to_add", ()))

    add_roles = {
        ctx.guild.get_role(role_id)
        for role_id in roles_to_add
    }
    add_roles = {r for r in add_roles if r}

    if add_roles:
        await staff.add_roles(*add_roles, reason=f"Staff added by {ctx.author.id}")

    await ctx.reply(embed=simple_embed(response.get("message")))

async def AddStaffBadge(ctx: commands.Context, staffs: str):
    mention_ids = re.findall(r"<@!?(\d+)>", staffs)
    raw_ids = re.findall(r"(?:^|\s)(\d{6,})(?:\s|$)", staffs)
    ids = list({int(i) for i in mention_ids + raw_ids})

    for staff_id in ids:
        staff = ctx.guild.get_member(staff_id)
        if staff is None:
            try:
                staff = await ctx.guild.fetch_member(staff_id)
            except:
                continue

        payload = {
            "staff_id": staff_id,
            "guild_id": ctx.guild.id,
            "name": staff.display_name,
            "avatar_url": staff.avatar.url if staff.avatar else None
        }

        response = await add_staff(payload)

        if not response.get("success"):
            continue

        roles_to_add = set(response.get("roles_to_add", ()))

        add_roles = {
            ctx.guild.get_role(role_id)
            for role_id in roles_to_add
        }
        add_roles = {r for r in add_roles if r}

        if add_roles:
            try:
                await staff.add_roles(*add_roles, reason=f"Staff added by {ctx.author.id}")
            except:
                continue
        
        await asyncio.sleep(1.5)

    await ctx.reply(embed=simple_embed("Batch of staffs has been added successfully!"))

async def RemoveStaff(ctx: commands.Context,staff: discord.Member | int,reason: str):
    if isinstance(staff, int):
        staff_id = staff
        member = None
    else:
        staff_id = staff.id
        member = staff

    payload = {
        "staff_id": staff_id,
        "guild_id": ctx.guild.id
    }

    response = await remove_staff(payload)

    if not response.get("success"):
        await ctx.reply(embed=simple_embed(response.get("message"), "cross"))
        return

    roles_to_remove = set(response.get("roles_to_remove", ()))
    channel_id = response.get("staff_updates_channel")

    if member is None:
        try:
            member = await ctx.guild.fetch_member(staff_id)
        except Exception:
            member = None

    staff_updates_channel = ctx.guild.get_channel(channel_id)
    if staff_updates_channel is None and channel_id:
        try:
            staff_updates_channel = await ctx.guild.fetch_channel(channel_id)
        except Exception:
            staff_updates_channel = None

    if member:
        remove_roles = {
            ctx.guild.get_role(role_id)
            for role_id in roles_to_remove
        }
        remove_roles = {r for r in remove_roles if r}

        if remove_roles:
            await member.remove_roles(
                *remove_roles,
                reason=f"Staff removed by {ctx.author.id} | {reason}"
            )

    if staff_updates_channel:
        embed = discord.Embed(
            color=16777215,
            title="Staff Update Information",
            description=f"### <@{staff_id}> has been removed from the team",
        )
        if staff:
            embed.set_thumbnail(url=staff.display_avatar.url)
        embed.set_image(url=Configs.img['border'])
        embed.add_field(
            name="Handled by",
            value=f"{ctx.author.mention}",
            inline=False,
        )
        embed.add_field(
            name="Reason",
            value=f"- {reason}",
            inline=False,
        )
        await staff_updates_channel.send(
            embed=embed
        )
    await ctx.reply(embed=simple_embed(response.get("message")))

async def EditStaff(ctx: commands.Context,staff_id: int,name: str = None,role_id: Optional[int] = None,joined_on: Optional[str] = None,timezone: Optional[str] = None, responsibility: Optional[str] = None):
    payload = {
        "staff_id": staff_id,
        "guild_id": ctx.guild.id,
        "name": name,
        "role_id": role_id,
        "joined_on": joined_on,
        "timezone": timezone,
        "responsibility": responsibility
    }

    result = await edit_staff(payload)

    if result.get("success"):
        await ctx.reply(
            embed=simple_embed(
                result["message"]
            )
        )
    else:
        await ctx.reply(
            embed=simple_embed(
                result["message"],'cross'
            )
        )

async def StrikeStaff(ctx: commands.Context, staff: discord.Member, reason: str):
    payload = {
        "staff_id": staff.id,
        "guild_id": ctx.guild.id,
        "issued_by": ctx.author.id,
        "reason": reason
    }

    response = await strike_staff(payload)

    if not response.get("success"):
        await ctx.reply(embed=simple_embed(response.get("message"), "cross"))
        return

    message = response.get("message")
    issued_by = response.get("issued_by")
    strike_reason = response.get("reason")


    channel_id = response.get("staff_updates_channel")
    staff_updates_channel = ctx.guild.get_channel(channel_id)

    if staff_updates_channel is None and channel_id:
        try:
            staff_updates_channel = await ctx.guild.fetch_channel(channel_id)
        except Exception:
            staff_updates_channel = None

    embed = discord.Embed(
        color=16777215,
        title="Strike Information",
        description=f"### {staff.mention} has been Striked!"
    )
    embed.set_thumbnail(url=staff.display_avatar.url)
    embed.set_image(url=Configs.img['border'])


    embed.add_field(
        name="Striked By",
        value=f"<@{issued_by}>",
        inline=False,
    )

    embed.add_field(
        name="Reason",
        value=f"- {strike_reason}",
        inline=False,
    )

    await ctx.reply(embed=simple_embed(message))

    if staff_updates_channel:
        await staff_updates_channel.send(
            content=staff.mention,
            embed=embed
        )

async def RemoveStrikeStaff(ctx: commands.Context, strike_id: int):

    payload = {
        "strike_id": strike_id,
        "guild_id": ctx.guild.id
    }

    result = await remove_strike(payload)

    status = result.get("success")
    message = result.get("message")

    if status:
        await ctx.reply(embed=simple_embed(message))
    else:
        await ctx.reply(embed=simple_embed(message, "cross"))

async def ListStrikes(ctx: commands.Context, staff: discord.Member):
    payload = {
        "staff_id": staff.id,
        "guild_id": ctx.guild.id
    }

    result = await fetch_staff_strikes(payload)

    if not result["success"] and not result["data"]:
        embed = (
            discord.Embed(
                color=0xf50000,
                title=f"{Configs.emoji['cross']} No Strikes Found",
                description=f"No strikes found for {staff.mention}.",
            )
            .set_thumbnail(url=staff.display_avatar.url or Configs.img['member'])
            .set_footer(text="Immutable Records • Managed by Lily System")
        )

        await ctx.reply(embed=embed)
        return

    embed = (
        discord.Embed(
            color=0xFFFFFF,
            title=f"{Configs.emoji['arrow']} {staff.display_name}'s Strike Information",
            description=f"{Configs.emoji['bookmark']} Listing all strikes issued to {staff.mention}",
        )
        .set_thumbnail(url=staff.display_avatar.url)
        .set_image(url=Configs.img['border'])
    )

    for strike in result["data"]:
        embed.add_field(
            name=f"{Configs.emoji['pencil']} __Strike ID: {strike['strike_id']}__",
            value=(
                f"> {Configs.emoji['bookmark']} **Reason** : {strike['reason']}\n"
                f"> {Configs.emoji['shield']} **Manager** : <@{strike['manager']}>\n"
                f"> {Configs.emoji['calender']} **Date** : {strike['date']}"
            ),
            inline=False
        )

    embed.set_footer(text="Immutable Records • Can only be removed by higher staff")

    await ctx.reply(embed=embed)

async def AddLOA(ctx: commands.Context, staff: discord.Member, reason: str):
    response = await add_loa({
        "staff_id": staff.id,
        "reason": reason,
        "loa_issued_by": ctx.author.id,
        "guild_id": ctx.guild.id
    })

    if not response.get("success"):
        await ctx.reply(embed=simple_embed(response.get("message")))
        return

    roles_to_remove = set(response.get("roles_to_remove", ()))
    roles_to_add = set(response.get("roles_to_add", ()))

    current_roles = set(staff.roles)

    remove_roles = {
        ctx.guild.get_role(rid)
        for rid in roles_to_remove
    }
    remove_roles = {r for r in remove_roles if r}

    add_roles = {
        ctx.guild.get_role(rid)
        for rid in roles_to_add
    }
    add_roles = {r for r in add_roles if r}

    new_roles = (current_roles - remove_roles) | add_roles

    await staff.edit(
        roles=list(new_roles),
        reason="LOA assigned"
    )

    await ctx.reply(embed=simple_embed(response.get("message")))

async def RemoveLOA(ctx: commands.Context, staff: discord.Member):
    response = await remove_loa({"staff_id": staff.id, "guild_id" : ctx.guild.id})

    if not response.get("success"):
        await ctx.reply(embed=simple_embed(response.get("message")))
        return

    roles_to_remove = set(response.get("roles_to_remove", ()))
    roles_to_add = set(response.get("roles_to_add", ()))

    current_roles = set(staff.roles)

    remove_roles = {
        ctx.guild.get_role(rid)
        for rid in roles_to_remove
    }
    remove_roles = {r for r in remove_roles if r}

    add_roles = {
        ctx.guild.get_role(rid)
        for rid in roles_to_add
    }
    add_roles = {r for r in add_roles if r}

    new_roles = (current_roles - remove_roles) | add_roles

    await staff.edit(
        roles=list(new_roles),
        reason="LOA removed"
    )

    await ctx.reply(embed=simple_embed(response.get("message")))
    
async def GetAllStaffRoles(ctx: commands.Context):
    try:
        cursor = await LSDA.sdb.execute(
            "SELECT role_id, role_name FROM roles WHERE guild_id = ? ORDER BY role_priority ASC",
            (ctx.guild.id,)
        )
        rows = await cursor.fetchall()

        if not rows:
            await ctx.reply(embed=simple_embed("No staff roles found in this guild.", 'cross'))
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

        await ctx.reply(embed=embed)

    except Exception as e:
        print(f"Exception [GetAllStaffRoles] {e}")
        await ctx.reply(embed=simple_embed(f"Error fetching staff roles", 'cross'))

async def UpdateStaff(ctx: commands.Context,staff: discord.Member,reason: str,update_type: str):
    if ctx.author.id == staff.id:
        await ctx.reply(embed=simple_embed("You cannot Update yourself", 'cross'))
        return

    payload: dict = {
        "guild_id": ctx.guild.id,
        "staff_id": staff.id,
        "update_type": update_type,
        "reason": reason,
        "updated_by": ctx.author.id
    }

    result = await update_staff(payload)

    if not result.get("success"):
        await ctx.send(embed=simple_embed(result.get("message"), 'cross'))
        return
    
    channel_id = result.get("staff_updates_channel")
    staff_updates_channel = ctx.guild.get_channel(channel_id)

    if staff_updates_channel is None and channel_id:
        try:
            staff_updates_channel = await ctx.guild.fetch_channel(channel_id)
        except Exception:
            staff_updates_channel = None

    old_role_id = result.get("old_role_id")
    new_role_id = result.get("new_role_id")

    old_role = ctx.guild.get_role(old_role_id)
    new_role = ctx.guild.get_role(new_role_id)

    try:
        current_roles = set(staff.roles)

        if old_role:
            current_roles.discard(old_role)

        if new_role:
            current_roles.add(new_role)

        await staff.edit(
            roles=list(current_roles),
            reason=f'Staff {update_type.title()} | {reason}'
        )

    except Exception as e:
        await ctx.send(
            embed=simple_embed(
                f"Database updated, but Discord role update failed: {e}",
                'cross'
            )
        )
        return

    act = "promoted" if update_type == "promotion" else "demoted"

    embed = discord.Embed(
        color=16777215,
        title=f"{update_type.title()} Information",
        description=f"### {staff.mention} has been {act.title()}!\n### <@&{old_role_id}> -> <@&{new_role_id}>"
    )
    embed.set_thumbnail(url=staff.display_avatar.url)
    embed.set_image(url=Configs.img['border'])


    embed.add_field(
        name=f"{act.title()} By",
        value=f"{ctx.author.mention}",
        inline=False,
    )

    embed.add_field(
        name="Reason",
        value=f"- {reason}",
        inline=False,
    )

    if staff_updates_channel:
        await staff_updates_channel.send(
            content=f'{staff.mention}',
            embed=embed
        ) 

    await ctx.send(
        embed=simple_embed(f"{staff.mention} has been {act}.")
    )

async def UpdateStaffBatch(ctx: commands.Context, content: str, update_type: str):
    mention_ids = re.findall(r"<@!?(\d+)>", content)
    raw_ids = re.findall(r"(?:^|\s)(\d{6,})(?:\s|$)", content)

    ids = list({int(i) for i in mention_ids + raw_ids})
    reason = re.sub(r"<@!?(\d+)>|\b\d{6,}\b", "", content).strip()

    if not ids:
        return await ctx.send(embed=simple_embed("No valid staff IDs found.", 'cross'))

    descriptions = []
    staff_updates_channel = None

    for staff_id in ids:
        if ctx.author.id == staff_id:
            continue

        payload = {
            "guild_id": ctx.guild.id,
            "staff_id": staff_id,
            "update_type": update_type,
            "reason": reason,
            "updated_by": ctx.author.id
        }

        result = await update_staff(payload)

        if not result.get("success"):
            await ctx.send(embed=simple_embed(result.get("message"), 'cross'))
            continue

        staff = ctx.guild.get_member(staff_id)

        if staff is None:
            try:
                staff = await ctx.guild.fetch_member(staff_id)
            except Exception:
                continue

        if not staff_updates_channel:
            channel_id = result.get("staff_updates_channel")
            staff_updates_channel = ctx.guild.get_channel(channel_id)

            if staff_updates_channel is None and channel_id:
                try:
                    staff_updates_channel = await ctx.guild.fetch_channel(channel_id)
                except Exception:
                    staff_updates_channel = None

        old_role = ctx.guild.get_role(result.get("old_role_id"))
        new_role = ctx.guild.get_role(result.get("new_role_id"))

        try:
            current_roles = set(staff.roles)

            if old_role:
                current_roles.discard(old_role)

            if new_role:
                current_roles.add(new_role)

            await staff.edit(
                roles=list(current_roles),
                reason=f'Staff {update_type.title()} | {reason}'
            )

            descriptions.append(
                f"### {staff.mention}: <@&{result.get('old_role_id')}> → <@&{result.get('new_role_id')}>"
            )

            await asyncio.sleep(2)

        except Exception as e:
            await ctx.send(
                embed=simple_embed(
                    f"Database updated, but Discord role update failed: {e}",
                    'cross'
                )
            )
            continue

    act = "promoted" if update_type == "promotion" else "demoted"

    embed = discord.Embed(
        color=16777215,
        title=f"{update_type.title()} Information",
        description="\n".join(descriptions) if descriptions else "No updates processed."
    )

    embed.set_image(url=Configs.img['border'])

    embed.add_field(
        name=f"{act.title()} By",
        value=ctx.author.mention,
        inline=False,
    )

    embed.add_field(
        name="Reason",
        value=f"- {reason}",
        inline=False,
    )

    if staff_updates_channel:
        await staff_updates_channel.send(content=" ".join(f"<@{i}>" for i in ids), embed=embed)

    await ctx.send(
        embed=simple_embed(f"Batch of staffs has been {act}.")
    )

async def MessageTracker(message: discord.Message):
    if not message.guild:
        return

    if message.content.startswith(Configs.bot_command_prefix):
        return
    
    try:
        guild_cache = LSDA.staff_management_cache.get(message.guild.id, {})

        approved_roles = guild_cache.keys()
        allowed_channels = guild_cache.get("message_count_channel", [])

        if (any(role.id in approved_roles for role in message.author.roles) and message.channel.id in allowed_channels):
            await LSDA.update_message({
                "guild_id": message.guild.id,
                "staff_id": message.author.id
            })
    except Exception as e:
        print(e)

async def AddStaffQuota(ctx: commands.Context,quota_role: discord.Role,minimum_ms: int,minimum_msg: int,on_quota_pass: types.OnQuotaEvent = None,on_quota_fail: types.OnQuotaEvent = None,check_by: types.QuotaCheckBy = None):
    if not ctx.guild:
        return await ctx.send("This command can only be used in a server.")

    payload = {
        "guild_id": ctx.guild.id,
        "role_id": quota_role.id,
        "min_msg": minimum_msg,
        "min_ms": minimum_ms,
        "on_quota_passed": on_quota_pass.value.lower(),
        "on_quota_failed": on_quota_fail.value.lower(),
        "check_by": check_by
    }

    result = await LSDA.add_staff_quota(payload)

    if not result.get("success"):
        await ctx.reply(embed=simple_embed(result.get("message"), 'cross'))
        return

    await ctx.reply(embed=simple_embed(result.get("message")))

async def RemoveStaffQuota(ctx: commands.Context, quota_id: str):
    payload = {
        "quota_id": int(quota_id)
    }

    result = await LSDA.remove_staff_quota(payload)

    if not result.get("success"):
        await ctx.reply(embed=simple_embed(result.get("message"), 'cross'))
        return


    await ctx.reply(embed=simple_embed(result.get("message")))

async def FetchStaffQuota(ctx: commands.Context):
    if not ctx.guild:
        return await ctx.send("This command can only be used in a server.")

    payload = {
        "guild_id": ctx.guild.id
    }

    quotas = await LSDA.fetch_staff_quota(payload)

    if not quotas:
        return await ctx.reply(embed=simple_embed("No staff quotas configured.", 'cross'))

    embed = discord.Embed(
        title="Staff Quota",
        description="- Showing all defined Staff Quota for this Server",
        color=16777215
    )

    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_image(url=Configs.img['border'])

    for quota in quotas:
        role = ctx.guild.get_role(quota["role_id"])
        role_mention = role.mention if role else f"`{quota['role_id']}`"

        embed.add_field(
            name=f"Quota #{quota['quota_id']}",
            value=(
                f"- Role : {role_mention}\n"
                f"- Minimum Messages : {quota['min_msg']}\n"
                f"- Minimum Moderation Stats : {quota['min_ms']}\n"
                f"- If Passed : {quota['on_quota_passed'] or 'None'}\n"
                f"- If Failed : {quota['on_quota_failed'] or 'None'}\n"
                f"- Quota Check By : {quota['check_by'] or 'None'}"
            ),
            inline=False
        )

    await ctx.reply(embed=embed)

async def CheckStaffQuota(ctx, staff: discord.Member):
    try:
        response = await get_staff_current_quota({
            "guild_id": ctx.guild.id,
            "staff_id": staff.id
        })

        if not response.get("success"):
            return await ctx.send(embed=simple_embed(f"{response.get("message")}", 'cross'))

        msgs = response["messages"]
        quota = response["quota"]
        result = response["result"]
        mod_stats = response.get("mod_stats_weekly", {})

        min_msg = quota.get("min_msg", 0) or 0
        min_ms = quota.get("min_ms", 0) or 0
        weekly = msgs.get("weekly", 0) or 0
        weekly_ms = mod_stats.get("weekly_ms", 0)
        weekly_ms = weekly_ms or 0

        remaining_msg = max(min_msg - weekly, 0)
        remaining_ms = max(min_ms - weekly_ms, 0)

        msg_status = (
            f"{Configs.emoji['checked']} Passed ({weekly}/{min_msg})"
            if result.get("message_quota_passed")
            else f"{Configs.emoji['cross']} Failed ({weekly}/{min_msg}, need {remaining_msg} more)"
        )
        
        ms_status = (
            f"{Configs.emoji['checked']} Passed ({weekly_ms}/{min_ms})"
            if result.get("ms_quota_passed")
            else f"{Configs.emoji['cross']} Failed ({weekly_ms}/{min_ms}, need {remaining_ms} more)"
        )

        embed = discord.Embed(
            title=f"Displaying Quota State for {staff}",
            color=16777215
        )

        embed.set_thumbnail(url=staff.display_avatar.url)

        embed.add_field(
            name="Message Stats",
            value=(
                f"- **Daily:** {msgs['daily']}\n"
                f"- **Weekly:** {msgs['weekly']}\n"
                f"- **Monthly:** {msgs['monthly']}\n"
                f"- **Total:** {msgs['total']}"
            ),
            inline=False
        )

        embed.add_field(
            name="Moderation Stats (7 Days)",
            value=f"- **Total Actions:** {weekly_ms}",
            inline=False
        )

        embed.add_field(
            name="Quota Requirements",
            value=(
                f"- **Min Messages:** {quota['min_msg']}\n"
                f"- **Min Mod Actions:** {quota['min_ms']}"
            ),
            inline=False
        )

        embed.add_field(
            name="Conclusion",
            value=(
                f"- **Messages:** {msg_status}\n"
                f"- **Moderation:** {ms_status}"
            ),
            inline=False
        )

        embed.set_footer(text=f"Staff ID: {response['staff_id']}")

        await ctx.reply(embed=embed)
    except Exception as e:
        print("CheckStaffQuota", e)

async def RemoveRole(ctx: commands.Context, role: int):
    response = await remove_role({"role_id": role})

    if response.get("success"):
        await ctx.reply(embed=simple_embed(f"{response.get("message")}"))
    else:
        await ctx.reply(embed=simple_embed(f"{response.get("message")}", 'cross'))

async def EvaluateStaffQuota(ctx: commands.Context):
    try:
        await ctx.defer()

        response = await get_all_staff_quota_status(ctx.guild.id)

        if not response.get("success"):
            return await ctx.reply(
                embed=simple_embed(response.get("message", "Error occurred"))
            )

        passed_staffs = response.get("passed_staff", [])
        failed_staffs = response.get("failed_staff", [])


        passed_staffs_str = "\n".join([
            f"<@{s['staff_id']}>"
            for s in passed_staffs
        ]) or "None"

        failed_staffs_str = ""

        for staff in failed_staffs:
            staff_id = staff["staff_id"]

            failed_staffs_str += (
                f"<@{staff_id}>\n"
            )

        embed = discord.Embed(
            title="Weekly Staff Quota Results",
            color=0xFFFFFF,
            description=(
                "### Results Based on\n"
                "- Weekly Messages\n"
                "- Weekly Mod Stats"
            ),
        )

        embed.add_field(
            name="Passed Staffs",
            value=passed_staffs_str,
            inline=False
        )

        embed.add_field(
            name="Failed Staffs",
            value=failed_staffs_str or "None",
            inline=False
        )

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        channel_id = response.get("staff_updates_channel_id")
        staff_updates_channel = None

        if channel_id:
            staff_updates_channel = ctx.guild.get_channel(channel_id)
            if staff_updates_channel is None:
                try:
                    staff_updates_channel = await ctx.guild.fetch_channel(channel_id)
                except Exception:
                    staff_updates_channel = None

        if staff_updates_channel:
            await staff_updates_channel.send(embed=embed)


        reset_response = await reset_messages({"guild_id": ctx.guild.id})

        if reset_response.get("success"):
            await ctx.send(embed=simple_embed(
                "Evaluated Staff Quota and Reset successfully!"
            ))
        else:
            await ctx.send(embed=simple_embed(
                "Evaluated Staff Quota but failed to reset messages!"
            ))
    except Exception as e:
        print(e)