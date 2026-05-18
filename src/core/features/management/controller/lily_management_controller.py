from ....database.integrations.management import ManagementDatabase
from ....database.integrations.bot_globals import BotGlobalsDatabaseAccess
from core.configs.sBotDetails import emoji, img, bot_command_prefix
from discord.ext import commands
from core.utils.embeds.sLilyEmbed import simple_embed
from ..types.staff_management_types import RoleType, OnQuotaEvent, QuotaCheckBy
from typing import Optional
from ..embeds.staff_management_embed import *

from ..components.staff_management_components import (
    StaffsView
)

import discord
import asyncio
import re

class LilyManagementController:
    def __init__(self, db: ManagementDatabase, bot_db: BotGlobalsDatabaseAccess) -> None:
        self.db = db
        self.bot_db: BotGlobalsDatabaseAccess = bot_db

    async def fetch_staff_detail(self, ctx: commands.Context ,staff: discord.Member) -> None:
        try:
            data_dict = await self.db.fetch_staff_detail(staff.id)

            if not data_dict:
                raise ValueError("Staff data not found in database.")

            embed = build_staff_embed(staff, data_dict)
            await ctx.reply(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                color=0xFF0000,
                description=f"{emoji['cross']} failed to fetch staff data. please check the database.",
            )

            await ctx.reply(embed=embed)
        
    async def fetch_all_staffs(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without an guild object",
                colour=0xf50000
            )

            await ctx.reply(embed=embed)
            return
        try:
            data = await self.db.fetch_all_staffs(ctx.guild.id)

            overall_details = data["overall"]
            role_user_map = data["roles"]

            view = StaffsView(ctx, self.db ,overall_details, role_user_map)
            view.message = await ctx.reply(view=view)

        except Exception as e:
            print(f"Error fetching staff list: {e}")

            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Failed to fetch staff data. Please check the database.",
                colour=0xf50000
            )

            await ctx.reply(embed=embed)
        
    async def update_all_staffs(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without an guild object",
                colour=0xf50000
            )

            await ctx.reply(embed=embed)
            return

        guild_id = ctx.guild.id

        rows = await self.db.fetch_all(
            "SELECT staff_id FROM staffs WHERE retired = 0 AND on_loa = 0 AND guild_id = ?",
            (guild_id,)
        )
        staff_ids = [row[0] for row in rows]

        db_roles = await self.db.fetch_all("""
            SELECT role_id, role_type
            FROM roles
            WHERE guild_id = ?
        """, (guild_id,))

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

                await self.db.execute(
                    "DELETE FROM staff_roles WHERE staff_id = ?",
                    (staff_id,),
                    commit=False
                )

                if top_staff_role is None and not discord_responsibilities:
                    await self.db.execute("""
                        UPDATE staffs
                        SET retired = 1
                        WHERE staff_id = ? AND guild_id = ?
                    """, (staff_id, guild_id), commit=False)

                    continue

                await self.db.execute("""
                    UPDATE staffs
                    SET retired = 0, avatar_url = ?
                    WHERE staff_id = ? AND guild_id = ?
                """, (staff_member.display_avatar.url, staff_id, guild_id), commit=False)

                assert top_staff_role is not None
                await self.db.execute("""
                    INSERT INTO staff_roles (staff_id, role_id)
                    VALUES (?, ?)
                """, (staff_id, top_staff_role.id), commit=False)

                if discord_responsibilities:
                    await self.db.executemany("""
                        INSERT INTO staff_roles (staff_id, role_id)
                        VALUES (?, ?)
                    """, [(staff_id, rid) for rid in discord_responsibilities], commit=False)

                print(f"[Update_All_Staffs] Updated {staff_member.name}")

            except Exception as e:
                print(f"Exception [Update_All_Staffs] {e}")
                continue

            await asyncio.sleep(1)

        await self.db.commit()
        await ctx.reply(embed=simple_embed(f"Updated Every staff roles on the Database!"))
    
    async def add_staff(self, ctx: commands.Context, staff: discord.Member) -> None:
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without an guild object",
                colour=0xf50000
            )

            await ctx.reply(embed=embed)
            return
        response = await self.db.add_staff(staff.id, ctx.guild.id, staff.display_name, staff.display_avatar.url)

        if not response.get("success"):
            await ctx.reply(embed=simple_embed(response.get("message") or "Unknown Object Passed and Failed", "cross"))
            return

        roles_to_add = set(response.get("roles_to_add", ()))

        add_roles = {
            ctx.guild.get_role(role_id)
            for role_id in roles_to_add
        }
        add_roles = {r for r in add_roles if r}

        if add_roles:
            await staff.add_roles(*add_roles, reason=f"Staff added by {ctx.author.id}")

        await ctx.reply(embed=simple_embed(response.get("message") or "Unknown object passed as an output, But it's a success!"))
    
    async def add_staff_batch(self, ctx: commands.Context, staffs: str) -> None:
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without an guild object",
                colour=0xf50000
            )

            await ctx.reply(embed=embed)
            return

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

            response = await self.db.add_staff(staff_id, ctx.guild.id, staff.display_name, staff.display_avatar.url)

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
    
    async def remove_staff(self, ctx: commands.Context,staff: discord.Member | int,reason: str) -> None:
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without an guild object",
                colour=0xf50000
            )

            await ctx.reply(embed=embed)
            return
        if isinstance(staff, int):
            staff_id = staff
            member = None
        else:
            staff_id = staff.id
            member = staff

        response = await self.db.remove_staff(staff_id, ctx.guild.id)

        if not response.get("success"):
            await ctx.reply(embed=simple_embed(response.get("message") or "Unknown object has been passed and it failed!", "cross"))
            return
        
        roles_to_remove = set(response.get("roles_to_remove", ()))
        channel_id = self.bot_db.get_channel(ctx.guild.id, "staff_updates")

        if member is None:
            try:
                member = await ctx.guild.fetch_member(staff_id)
            except Exception:
                member = None

        staff_updates_channel: discord.TextChannel | None = None

        if channel_id is not None:
            channel = ctx.guild.get_channel(channel_id)

            if channel is None:
                try:
                    channel = await ctx.guild.fetch_channel(channel_id)
                except Exception:
                    channel = None

            if isinstance(channel, discord.TextChannel):
                staff_updates_channel = channel

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
                embed = build_staff_update_embed(
                    staff=staff,
                    handled_staff=ctx.author,
                    reason=reason,
                    img=img
                )
                await staff_updates_channel.send(
                    embed=embed
                )
        await ctx.reply(embed=simple_embed(response.get("message") or "Unknown object has been passed, but it's an success!"))

    async def edit_staff(self, ctx: commands.Context,staff_id: int,name: str ,joined_on: Optional[str] = None,timezone: Optional[str] = None, responsibility: Optional[str] = None):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without an guild object",
                colour=0xf50000
            )

            await ctx.reply(embed=embed)
            return
        payload = {
            "staff_id": staff_id,
            "guild_id": ctx.guild.id,
            "name": name,
            "joined_on": joined_on,
            "timezone": timezone,
            "responsibility": responsibility
        }

        result = await self.db.edit_staff(**payload)

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

    async def strike_staff(self, ctx: commands.Context, staff: discord.Member, reason: str):
        try:
            if ctx.guild is None:
                embed = discord.Embed(
                    title=f"{emoji['cross']} Error",
                    description="Cannot execute this command without an guild object",
                    colour=0xf50000
                )

                await ctx.reply(embed=embed)
                return
            payload = {
                "staff_id": staff.id,
                "guild_id": ctx.guild.id,
                "issued_by": ctx.author.id,
                "reason": reason
            }

            response = await self.db.strike_staff(**payload)

            if not response.get("success"):
                await ctx.reply(embed=simple_embed(response.get("message") or "An unknown object has been returned and failed", "cross"))
                return

            message = response.get("message")
            issued_by = response.get("issued_by")
            strike_reason = response.get("reason")


            channel_id = self.bot_db.get_channel(ctx.guild.id, "staff_updates")

            staff_updates_channel: discord.TextChannel | None = None

            if channel_id is not None:
                channel = ctx.guild.get_channel(channel_id)

                if channel is None:
                    try:
                        channel = await ctx.guild.fetch_channel(channel_id)
                    except Exception:
                        channel = None

                if isinstance(channel, discord.TextChannel):
                    staff_updates_channel = channel

            embed = discord.Embed(
                color=16777215,
                title="Strike Information",
                description=f"### {staff.mention} has been Striked!"
            )
            embed.set_thumbnail(url=staff.display_avatar.url)
            embed.set_image(url=img['border'])


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

            await ctx.reply(embed=simple_embed(message or "An unknown object has been returned, but It's an success!"))

            if staff_updates_channel:
                await staff_updates_channel.send(
                    content=staff.mention,
                    embed=embed
                )
        except Exception as e:
            print(e)

    async def remove_strike_staff(self, ctx: commands.Context, strike_id: int):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without an guild object",
                colour=0xf50000
            )

            await ctx.reply(embed=embed)
            return
        payload = {
            "strike_id": strike_id,
            "guild_id": ctx.guild.id
        }

        result = await self.db.remove_strike(**payload)

        status: bool = bool(result.get("success"))
        message: str = str(result.get("message") or "An unknown error occurred")

        if status:
            await ctx.reply(embed=simple_embed(message))
        else:
            await ctx.reply(embed=simple_embed(message, "cross"))

    async def list_strikes(self, ctx: commands.Context, staff: discord.Member):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return

        result = await self.db.fetch_staff_strikes(
            staff_id=staff.id,
            guild_id=ctx.guild.id
        )

        if not result["success"] and not result["data"]:
            embed = build_no_strikes_embed(staff)
            await ctx.reply(embed=embed)
            return
        
        strikes = result.get("data")
        if not isinstance(strikes, list):
            strikes = []

        embed = build_strikes_list_embed(staff, strikes)
        await ctx.reply(embed=embed)

    async def edit_strike(self, ctx: commands.Context, strike_id: int ,new_reason: str):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return
        response = await self.db.edit_strike(**{
            "guild_id" : ctx.guild.id, 
            "strike_id": strike_id,
            "staff_id": ctx.author.id,
            "new_reason":  new_reason
        })

        if not response.get("success"):
            await ctx.reply(embed=simple_embed(str(response.get("message")), 'cross'))
            return
        
        await ctx.reply(embed=simple_embed(str(response.get("message"))))

    async def add_loa(self, ctx: commands.Context, staff: discord.Member, reason: str):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return
        try:
            response = await self.db.add_loa(**{
                "staff_id": staff.id,
                "reason": reason,
                "loa_issued_by": ctx.author.id,
                "guild_id": ctx.guild.id
            })

            if not response.get("success"):
                await ctx.reply(embed=simple_embed(str(response.get("message")), 'cross'))
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

            await ctx.reply(embed=simple_embed(str(response.get("message"))))
        except Exception as e:
            print(f"Exception [AddLOA] {e}")

    async def remove_loa(self, ctx: commands.Context, staff: discord.Member):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return
        response = await self.db.remove_loa(**{"staff_id": staff.id, "guild_id" : ctx.guild.id})

        if not response.get("success"):
            await ctx.reply(embed=simple_embed(str(response.get("message"))))
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

        await ctx.reply(embed=simple_embed(str(response.get("message"))))

    async def get_all_staff_roles(self, ctx: commands.Context):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return
        try:
            rows = await self.db.fetch_all(
                "SELECT role_id, role_name FROM roles WHERE guild_id = ? ORDER BY role_priority ASC",
                (ctx.guild.id,)
            )

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

    async def update_staff(self, ctx: commands.Context, staff: discord.Member, reason: str, update_type: str):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return

        if ctx.author.id == staff.id:
            await ctx.reply(embed=simple_embed(
                "You cannot update yourself",
                "cross"
            ))
            return

        result = await self.db.update_staff(
            guild_id=ctx.guild.id,
            staff_id=staff.id,
            update_type=update_type,
            reason=reason,
            updated_by=ctx.author.id
        )

        if not result.get("success"):
            await ctx.send(embed=simple_embed(
                str(result.get("message")),
                "cross"
            ))
            return

        channel_id = self.bot_db.get_channel(
            ctx.guild.id,
            "staff_updates"
        )

        staff_updates_channel: discord.TextChannel | None = None

        if channel_id is not None:
            channel = ctx.guild.get_channel(channel_id)

            if channel is None:
                try:
                    channel = await ctx.guild.fetch_channel(channel_id)
                except Exception:
                    channel = None

            if isinstance(channel, discord.TextChannel):
                staff_updates_channel = channel

        old_role_id = result.get("old_role_id")
        new_role_id = result.get("new_role_id")

        old_role = ctx.guild.get_role(old_role_id) if old_role_id else None
        new_role = ctx.guild.get_role(new_role_id) if new_role_id else None

        try:
            current_roles = set(staff.roles)

            if old_role:
                current_roles.discard(old_role)

            if new_role:
                current_roles.add(new_role)

            await staff.edit(
                roles=list(current_roles),
                reason=f"Staff {update_type.title()} | {reason}"
            )

        except Exception as e:
            await ctx.send(embed=simple_embed(
                f"Database updated, but Discord role update failed: {e}",
                "cross"
            ))
            return

        embed = build_staff_update_result_embed(
            staff=staff,
            ctx=ctx,
            old_role_id=old_role_id,
            new_role_id=new_role_id,
            reason=reason,
            update_type=update_type
        )


        if staff_updates_channel:
            await staff_updates_channel.send(
                content=staff.mention,
                embed=embed
            )

        act = "promoted" if update_type == "promotion" else "demoted"

        await ctx.send(
            embed=simple_embed(f"{staff.mention} has been {act}.")
        )

    async def update_staff_batch(self, ctx: commands.Context, content: str, update_type: str):
        mention_ids = re.findall(r"<@!?(\d+)>", content)
        raw_ids = re.findall(r"(?:^|\s)(\d{6,})(?:\s|$)", content)

        ids = list({int(i) for i in mention_ids + raw_ids})
        reason = re.sub(r"<@!?(\d+)>|\b\d{6,}\b", "", content).strip()

        if not ctx.guild:
            return await ctx.send(embed=simple_embed("Guild context missing.", "cross"))

        if not ids:
            return await ctx.send(embed=simple_embed("No valid staff IDs found.", "cross"))

        staff_updates_channel: discord.TextChannel | None = None

        channel_id = self.bot_db.get_channel(ctx.guild.id, "staff_updates")

        if channel_id:
            channel = ctx.guild.get_channel(channel_id)

            if channel is None:
                try:
                    channel = await ctx.guild.fetch_channel(channel_id)
                except Exception:
                    channel = None

            if isinstance(channel, discord.TextChannel):
                staff_updates_channel = channel

        descriptions: list[str] = []

        for staff_id in ids:

            if ctx.author.id == staff_id:
                continue

            result = await self.db.update_staff(
                    guild_id=ctx.guild.id,
                    staff_id=staff_id,
                    update_type=update_type,
                    reason=reason,
                    updated_by=ctx.author.id
                )

            if not result.get("success"):
                await ctx.send(embed=simple_embed(
                    str(result.get("message")),
                    "cross"
                ))
                continue

            staff = ctx.guild.get_member(staff_id)

            if staff is None:
                try:
                    staff = await ctx.guild.fetch_member(staff_id)
                except Exception:
                    continue

            old_role_id = result.get("old_role_id")
            new_role_id = result.get("new_role_id")

            old_role = ctx.guild.get_role(old_role_id) if old_role_id else None
            new_role = ctx.guild.get_role(new_role_id) if new_role_id else None

            try:
                current_roles = set(staff.roles)

                if old_role:
                    current_roles.discard(old_role)

                if new_role:
                    current_roles.add(new_role)

                await staff.edit(
                    roles=list(current_roles),
                    reason=f"Staff {update_type.title()} | {reason}"
                )

                descriptions.append(
                    f"### {staff.mention}: "
                    f"<@&{old_role_id}> → <@&{new_role_id}>"
                )

                await asyncio.sleep(1.5)

            except Exception as e:
                await ctx.send(embed=simple_embed(
                    f"DB updated but Discord update failed: {e}",
                    "cross"
                ))


        embed = build_staff_batch_update_embed(
            ctx=ctx,
            descriptions=descriptions,
            update_type=update_type,
            reason=reason
        )

        if staff_updates_channel:
            await staff_updates_channel.send(
                content=" ".join(f"<@{i}>" for i in ids),
                embed=embed
            )

        act = "promoted" if update_type == "promotion" else "demoted"

        await ctx.send(
            embed=simple_embed(f"Batch of staff has been {act}.")
        )
    
    # FIX THIS IN FUTURE
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        if message.content.startswith(bot_command_prefix):
            return
        
        if isinstance(message.author, discord.User):
            return
        
        try:
            approved_roles = self.db.get_staff_roles(message.guild.id)
            allowed_channels = self.bot_db.get_channels(message.guild.id, "valid_channel")

            if (any(role.id in approved_roles for role in message.author.roles) and message.channel.id in allowed_channels):
                await self.db.update_message(**{
                    "guild_id": message.guild.id,
                    "staff_id": message.author.id
                })
        except Exception as e:
            pass

    async def add_staff_quota(self, ctx: commands.Context,quota_role: discord.Role,minimum_ms: int,minimum_msg: int,on_quota_pass: OnQuotaEvent,on_quota_fail: OnQuotaEvent,check_by: QuotaCheckBy):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return

        payload = {
            "guild_id": ctx.guild.id,
            "role_id": quota_role.id,
            "min_msg": minimum_msg,
            "min_ms": minimum_ms,
            "on_quota_passed": on_quota_pass.value.lower(),
            "on_quota_failed": on_quota_fail.value.lower(),
            "check_by": check_by
        }

        result = await self.db.add_staff_quota(**payload)

        if not result.get("success"):
            await ctx.reply(embed=simple_embed(str(result.get("message")), 'cross'))
            return

        await ctx.reply(embed=simple_embed(str(result.get("message"))))

    async def remove_staff_quota(self, ctx: commands.Context, quota_id: str):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return
        payload = {
            "guild_id": ctx.guild.id,
            "quota_id": int(quota_id)
        }

        result = await self.db.remove_staff_quota(**payload)

        if not result.get("success"):
            await ctx.reply(embed=simple_embed(str(result.get("message")), 'cross'))
            return


        await ctx.reply(embed=simple_embed(str(result.get("message"))))

    async def fetch_staff_quota(self, ctx: commands.Context):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return

        quotas = await self.db.fetch_staff_quota(ctx.guild.id)

        if not quotas:
            return await ctx.reply(embed=simple_embed("No staff quotas configured.", 'cross'))

        embed = discord.Embed(
            title="Staff Quota",
            description="- Showing all defined Staff Quota for this Server",
            color=16777215
        )

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_image(url=img['border'])

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

    async def check_staff_quota(self, ctx: commands.Context, staff: discord.Member):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return
        try:
            response = await self.db.get_staff_current_quota(**{
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
                f"{emoji['checked']} Passed ({weekly}/{min_msg})"
                if result.get("message_quota_passed")
                else f"{emoji['cross']} Failed ({weekly}/{min_msg}, need {remaining_msg} more)"
            )
            
            ms_status = (
                f"{emoji['checked']} Passed ({weekly_ms}/{min_ms})"
                if result.get("ms_quota_passed")
                else f"{emoji['cross']} Failed ({weekly_ms}/{min_ms}, need {remaining_ms} more)"
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

    async def remove_role(self, ctx: commands.Context, role: int):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return
        response = await self.db.remove_role(role)

        if response.get("success"):
            await ctx.reply(embed=simple_embed(f"{response.get("message")}"))
        else:
            await ctx.reply(embed=simple_embed(f"{response.get("message")}", 'cross'))

    async def evaluate_staff_quota(self, ctx: commands.Context):
        if ctx.guild is None:
            embed = discord.Embed(
                title=f"{emoji['cross']} Error",
                description="Cannot execute this command without a guild object",
                colour=0xf50000
            )
            await ctx.reply(embed=embed)
            return
        try:
            await ctx.defer()

            response = await self.db.get_all_staff_quota_status(ctx.guild.id)

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


            await ctx.reply(embed=embed)
            
        except Exception as e:
            print(e)