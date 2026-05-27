from core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from core.logging.lily_logging import LilyLoggingController
from discord.ext import commands
from core.utils.embeds.sLilyEmbed import simple_embed
from datetime import datetime, timedelta, timezone
from core.configs.sBotDetails import appeal_server_link
from typing import Optional
from core.utils.lily_utility import utcnow
from core.features.moderation.components.sLilyModerationComponents import *
from core.features.moderation.utils.moderation_utils import mute_parser
from ..components.sLilyModerationComponents import CaseProofsView, ProofsView


import discord
import asyncio

class LilyModerationController:
    def __init__(self, bot_db: BotGlobalsDatabaseAccess, logging_controller: LilyLoggingController) -> None:
        self.logging_controller: LilyLoggingController = logging_controller
        self.bot_db: BotGlobalsDatabaseAccess = bot_db

    async def ban_user(self, ctx: commands.Context, user_input, reason="No reason provided", proofs: list = []):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("Command requires guild object inorder to execute", 'cross'))
            return
        try:
            jail_value = self.bot_db.global_config.jail if self.bot_db.global_config else 1

            if not isinstance(ctx.author, discord.Member):
                await ctx.reply(embed=simple_embed("Please execute this command inside an guild!", 'cross'))
                return

            role_ids = [str(r.id) for r in ctx.author.roles]
            if not role_ids:
                return await ctx.reply(embed=simple_embed("No permission.", 'cross'))

            user_id = getattr(user_input, "id", None)
            if not user_id:
                return await ctx.reply(embed=simple_embed("Invalid user.", 'cross'))

            member = user_input if isinstance(user_input, discord.Member) else None
            target = user_input

            if not member:
                return await ctx.reply(embed=simple_embed("User not in guild.", 'cross'))

            if member:
                response = await self.bot_db.get_mod_queue_entry(member.id, ctx.guild.id)
                if response.get("success"):
                    return await ctx.reply(
                        embed=simple_embed(
                            f"This user already has a pending action request from <@{response.get('moderator_id')}>.\n"
                            f"Check `/moderation_queue` for details.",
                            "cross"
                        )
                    )

                if member.id == ctx.author.id:
                    return await ctx.reply(
                        embed=simple_embed(
                            "You cannot moderate yourself.",
                            "cross"
                        )
                    )

                if member.id == ctx.bot.user.id:
                    return await ctx.reply(
                        embed=simple_embed(
                            "You cannot moderate the bot.",
                            "cross"
                        )
                    )

                if member.id == ctx.guild.owner_id:
                    return await ctx.reply(
                        embed=simple_embed(
                            "You cannot moderate the server owner.",
                            "cross"
                        )
                    )

                if member.top_role >= ctx.guild.me.top_role:
                    return await ctx.reply(
                        embed=simple_embed(
                            "I cannot take action on this user because their role is higher than or equal to mine.",
                            "cross"
                        )
                    )

                if member.top_role >= ctx.author.top_role:
                    return await ctx.reply(
                        embed=simple_embed(
                            "You cannot take action on this user because their role is higher than or equal to yours.",
                            "cross"
                        )
                    )
            author_roles = [role.id for role in ctx.author.roles if role.name != "@everyone"]
            status = await self.bot_db.get_ban_limit_status(ctx.guild.id, ctx.author.id, author_roles)

            """ Validate status first """

            if status.exceeded:
                return await ctx.reply(embed=simple_embed(
                    f"Daily limit exceeded.\n{status.remaining_time}", 'cross'
                ))

            if self.bot_db.ban_queue(ctx.guild.id, author_roles):
                response = await self.bot_db.add_mod_queue(**{
                    "guild_id"       : ctx.guild.id,
                    "moderator_id"   : ctx.author.id,
                    "target_user_id" : member.id,
                    "mod_type"       : "quarantine" if jail_value == 1 else "ban",
                    "reason"         : reason,
                    "message_source" : ctx.message.jump_url,
                })

                try:
                    await member.edit(
                        timed_out_until=datetime.now(timezone.utc) + timedelta(hours=6),
                        reason=f"{reason} | In Ban Queue",
                    )
                except Exception:
                    pass

                if response.get("success"):
                    return await ctx.reply(embed=simple_embed(str(response.get("message"))))


            async def notify_and_log(action: str) -> int | None:
                if ctx.guild is None:
                    return

                if not isinstance(ctx.author, discord.Member):
                    return
                try:
                    await target.send(embed=ban_embed(
                        ctx.author, reason, appeal_server_link, ctx.guild.name
                    ))
                except Exception:
                    pass

                case_id = await self.logging_controller.log_moderation_action(
                    ctx, ctx.author.id, user_id, action, reason, proofs.copy()
                )

                return case_id

            if jail_value == 0:
                await ctx.guild.ban(
                    discord.Object(id=user_id),
                    reason=f"By {ctx.author} | {reason}",
                )
                await ctx.reply(embed=simple_embed(
                    f"Banned: <@{user_id}>\n**Remaining:** {max(0, status.remaining_count - 1)}"
                ))
                await notify_and_log("ban")

            quarantine_role = (
                discord.utils.get(ctx.guild.roles, name="Quarantine")
                or discord.utils.get(ctx.guild.roles, name="Prisoner")
            )

            if not quarantine_role or quarantine_role >= ctx.guild.me.top_role:
                return await ctx.reply(embed=simple_embed("Quarantine role issue.", 'cross'))

            if quarantine_role in member.roles:
                return await ctx.reply(embed=simple_embed("Already quarantined.", 'cross'))

            await member.add_roles(
                    quarantine_role,
                    reason=f"Quarantine by {ctx.author} | {reason}",
            )

            """ If no proofs has been attached always send a button view to attach proofs """
            if len(proofs) > 0:
                """ If there are proofs for the case """
                await ctx.reply(embed=simple_embed(
                    f"Quarantined: <@{user_id}>\n**Remaining:** {max(0, status.remaining_count - 1)}"
                ))
                await notify_and_log("quarantine")
                return
            else:
                """ Else log the case first, get the case ID for proofs attachment """
                case_id = await notify_and_log("quarantine")
                if case_id:
                    view = CaseProofsView(case_id, self.logging_controller, None)
                    msg = await ctx.reply(
                        embed=simple_embed(
                            f"Quarantined: <@{user_id}>\n**Remaining:** {max(0, status.remaining_count - 1)}"
                        ),
                        view=view
                    )

                    view.message = msg
                    
                else:
                    await ctx.reply(embed=simple_embed(
                    f"Quarantined: <@{user_id}>\n**Remaining:** {max(0, status.remaining_count - 1)}"
                ))
            

        except discord.HTTPException as e:
            return await ctx.reply(embed=simple_embed(f"HTTP Error: {e}", 'cross'))
        except Exception as e:
            return await ctx.reply(embed=simple_embed(f"Error: {e}", 'cross'))
        
    async def ban_queue_user(
        self,
        interaction: discord.Interaction,
        moderation_queue: list[dict]
    ) -> str:
        if interaction.guild is None:
            await interaction.response.send_message(embed=simple_embed("Command requires guild object inorder to execute", 'cross'), ephemeral=True)
            return "Nothing Processed"
        guild = interaction.guild
        results = []

        try:
            jail_value = self.bot_db.global_config.jail if self.bot_db.global_config else 1

            for item in moderation_queue:
                user_id: int = 0
                try:
                    mod_type = item.get("mod_type")
                    moderator_id: int = item.get("moderator_id") or 0
                    user_id = item.get("target_user_id") or 0 
                    reason = item.get("reason", "No reason provided")
                    source = item.get("message_source")

                    if not user_id:
                        results.append("Invalid user in queue")
                        continue

                    if mod_type == "ban" and jail_value == 0:
                        await guild.ban(
                            discord.Object(id=user_id),
                            reason=f"Queued | {reason}"
                        )

                        await self.logging_controller.log_moderation_action(
                            interaction, moderator_id, user_id, "ban", f'{reason} | Verified by {interaction.user.id}', []
                        )

                        results.append(f"Banned <@{user_id}>")

                    elif mod_type == "quarantine" or (mod_type == "ban" and jail_value == 1):
                        try:
                            member = guild.get_member(user_id) or await guild.fetch_member(user_id)
                        except Exception:
                            results.append(f"<@{user_id}> Not found!")
                            continue

                        quarantine_role = (
                            discord.utils.get(guild.roles, name="Quarantine")
                            or discord.utils.get(guild.roles, name="Prisoner")
                        )

                        if not quarantine_role:
                            results.append("No quarantine role")
                            continue

                        if quarantine_role >= guild.me.top_role:
                            results.append("Role hierarchy issue")
                            continue

                        if quarantine_role in member.roles:
                            results.append(f"<@{user_id}> already quarantined")
                            continue

                        await member.add_roles(
                            quarantine_role,
                            reason=f"{reason} | Verified by {interaction.user}"
                        )

                        await self.logging_controller.log_moderation_action(
                            interaction, moderator_id, user_id, "quarantine", f'{reason} | Verified by {interaction.user.id}', []
                        )

                        results.append(f"Quarantined <@{user_id}>")

                    else:
                        results.append(f"Unknown mod type for <@{user_id}>")
                    await asyncio.sleep(2)
                except discord.Forbidden:
                    results.append(f"Missing permissions for <@{user_id}>")
                    await asyncio.sleep(2)
                except discord.HTTPException as e:
                    results.append(f"HTTP error for <@{user_id}>: {e}")
                    await asyncio.sleep(2)
                except Exception as e:
                    results.append(f"Error for <@{user_id}>: {e}")
                    await asyncio.sleep(2)

            await self.bot_db.clear_mod_queue(interaction.guild.id)
            return "\n".join(results) if results else "Nothing processed."

        except Exception as e:
            return f"Error: {e}"

    async def mute_user(self, ctx: commands.Context, user: discord.Member, duration: str, reason: str = "No reason provided", proofs: list = []):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("Command requires guild object inorder to execute", 'cross'))
            return
        
        if isinstance(ctx.author, discord.User):
            await ctx.reply(embed=simple_embed("Command requires member object inorder to execute", 'cross'))
            return

        if user.timed_out_until and user.timed_out_until > discord.utils.utcnow():
            await ctx.reply(embed=simple_embed("This user is already muted", 'cross'))
            return

        if user.top_role >= ctx.guild.me.top_role:
            await ctx.reply(embed=simple_embed("I cannot mute this user", 'cross'))
            return

        if user.top_role >= ctx.author.top_role:
            await ctx.reply(embed=simple_embed("I cannot mute a user with a role equal to or higher than yours.", 'cross'))
            return

        if user.id in {ctx.guild.owner_id, ctx.bot.user.id, ctx.author.id}:
            await ctx.reply(embed=simple_embed("Exception!. Stupid action detected errno 77777", 'cross'))
            return

        try:
            seconds = mute_parser(duration)
            until = utcnow() + timedelta(seconds=seconds)

            try:
                embed = mute_embed(ctx.author, reason, ctx.guild.name)
                await user.send(embed=embed)
            except Exception as e:
                print("DM failed:", e)

            await user.edit(timed_out_until=until, reason=reason)

            if len(proofs) > 0:
                await ctx.reply(embed=simple_embed(
                    f"Muted: <@{user.id}>"
                ))

            case_id: int | None = await self.logging_controller.log_moderation_action(ctx, ctx.author.id, user.id, "mute", reason, proofs)

            if case_id and len(proofs) <= 0:
                view = CaseProofsView(case_id, self.logging_controller, None)
                msg = await ctx.reply(
                    embed=simple_embed(
                        f"Muted: <@{user.id}>"
                    ),
                    view=view
                )

                view.message = msg

        except ValueError as ve:
            await ctx.reply(embed=simple_embed(str(ve)))
        except discord.HTTPException as e:
            print(f"[MuteUser] {e}")
            await ctx.reply(embed=simple_embed(f"Failed to mute the user", 'cross'))
        except Exception as e:
            print(f"[MuteUser] {e}")
            await ctx.reply(embed=simple_embed(f"Failed to mute the user", 'cross'))

    async def unmute(self, ctx: commands.Context, user: discord.Member):
        
        if not user.timed_out_until or user.timed_out_until <= discord.utils.utcnow():
            await ctx.reply(embed=simple_embed("That user is not muted currently", 'cross'))
            return

        try:
            await user.edit(timed_out_until=None, reason=f"Manual unmute by moderator {ctx.author.mention}")
            await ctx.reply(embed=simple_embed(f"Unmuted: <@{user.id}>"))

        except discord.HTTPException as e:
            await ctx.reply(embed=simple_embed(f"Failed to unmute user. {e}", 'cross'))
        except Exception as e:
            await ctx.reply(embed=simple_embed(f"Exception: {e}", 'cross'))

    async def warn(self, ctx: commands.Context, member: discord.Member, reason: str, proofs=[]):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("Command requires guild object inorder to execute", 'cross'))
            return
        
        if isinstance(ctx.author, discord.User):
            await ctx.reply(embed=simple_embed("Command requires member object inorder to execute", 'cross'))
            return
        
        if len(proofs) > 0:
            await ctx.reply(embed=simple_embed(f"{member.mention} has been warned"))

        case_id: int | None = await self.logging_controller.log_moderation_action(ctx, ctx.author.id, member.id, "warn", reason, proofs)

        embed = warn_embed(ctx.author, reason, ctx.guild.name)
        try:
            await member.send(embed=embed)
        except Exception as e:
            print(e)

        if case_id and len(proofs) <= 0:
            view = CaseProofsView(case_id, self.logging_controller, None)
            msg = await ctx.reply(embed=simple_embed(f"{member.mention} has been warned"), view=view)
            view.message = msg

    async def case_edit(self, ctx: commands.Context, case_id: int, case_statement: str, absolute: bool=False):
        response = await self.bot_db.edit_case(**{"staff_id": ctx.author.id, "case_id": case_id, "case_statement": case_statement, "absolute": absolute})

        if response.get("success"):
            await ctx.reply(embed=simple_embed(str(response.get("message"))))
        else:
            await ctx.reply(embed=simple_embed(str(response.get("message")), 'cross'))

    async def case_delete(self, ctx: commands.Context, case_id: int):
        response = await self.bot_db.delete_case(case_id)
        if response.get("success"):
            await ctx.reply(embed=simple_embed(str(response.get("message"))))
        else:
            await ctx.reply(embed=simple_embed(str(response.get("message")), 'cross'))

    async def fetch_moderation_queue(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("Command requires guild object inorder to execute", 'cross'))
            return
        
        if isinstance(ctx.author, discord.User):
            await ctx.reply(embed=simple_embed("Command requires member object inorder to execute", 'cross'))
            return
        try:
            response = await self.bot_db.fetch_mod_queue(ctx.guild.id)
            if response.get("success"):
                view = ModerationQueueClear(response.get("items", []), ctx.author, self.ban_queue_user)
                message = await ctx.reply(view=view, embed=moderation_queue_embed(ctx, response.get("items", [])))
                view.message = message
            else:
                await ctx.reply(embed=simple_embed(response.get("message", "Unknown Error!"), 'cross'))
        except Exception as e:
            print(f"Exception [FetchModerationQueue] {e}")

    async def remove_member_from_queue(self, ctx: commands.Context, member: discord.Member):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("Command requires guild object inorder to execute", 'cross'))
            return
        try:
            response = await self.bot_db.clear_mod_queue_particular(**{"guild_id": ctx.guild.id, "user_id": member.id})
            if response.get("success"):
                await ctx.reply(embed=simple_embed(response.get("message", "Success!")))
            else:
                await ctx.reply(embed=simple_embed(response.get("message", "Success!"), 'cross'))
        except Exception as e:
            print(f"Exception [RemoveMemberFromQueue] {e}")

    async def ms(self, ctx: commands.Context, moderator: discord.Member, page_start: int = 0, page_end: int = 5):
        if ctx.guild is None:
            await ctx.reply(
                embed=simple_embed(
                    "Command requires guild object in order to execute",
                    "cross"
                )
            )
            return

        result = await self.bot_db.fetch_mod_stats(
            guild_id=ctx.guild.id,
            moderator_id=moderator.id,
            page_start=page_start,
            page_end=page_end
        )

        if not result["success"]:
            await ctx.reply(embed=simple_embed("No stats found For the given moderator ID"))
            return

        embeds = build_ms_embed(
            moderator=moderator,
            logs=result["logs"],
            stats=result["stats"],
            total_logs=result["total_logs"],
            page_start=page_start
        )

        await ctx.reply(embeds=embeds)
    
    async def mod_logs(
        self,
        ctx: commands.Context,
        target_user_id: int,
        user: discord.User,
        moderator: Optional[discord.User] = None,
        mod_type: str = "all",
        page_start: int = 0,
        page_end: int = 5
    ):

        if ctx.guild is None:
            await ctx.reply(
                embed=simple_embed(
                    "Command requires guild object in order to execute",
                    "cross"
                )
            )
            return

        payload = {
            "guild_id": ctx.guild.id,
            "target_user_id": target_user_id,
            "moderator_id": moderator.id if moderator else None,
            "mod_type": mod_type,
            "page_start": page_start,
            "page_end": page_end
        }

        result = await self.bot_db.fetch_mod_logs(**payload)

        if not result["success"]:
            await ctx.reply(embed=simple_embed("No cases found.", 'cross'))
            return

        embed =  build_mod_logs_embed(
            user=user,
            display_logs=result["logs"],
            mod_type_counts=result["counts"],
            total_count=result["total_logs"],
            page_start=page_start
        )
        logging_channel_id = self.bot_db.get_channel(ctx.guild.id, "logs_channel")
        if logging_channel_id is not None and result["proofs_exists"]:
            view = ProofsView(result["logs"], logging_channel_id)
            await ctx.reply(embeds=embed, view=view)
        else:
            await ctx.reply(embeds=embed)

    async def moderation_insights(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.reply(
                embed=simple_embed(
                    "Command requires guild object in order to execute",
                    "cross"
                )
            )
            return
        view = ModerationInsights(ctx.guild.me, self.bot_db)
        view.message = await ctx.reply(view=view)