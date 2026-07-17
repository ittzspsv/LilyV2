import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple

import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from src.core.configs.sBotDetails import appeal_server_link
from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess, BanLimitStatus
from src.core.features.moderation.components.sLilyModerationComponents import *
from src.core.features.moderation.utils.moderation_utils import mute_parser
from src.core.logging.lily_logging import LilyLoggingController
from src.core.utils.embeds.sLilyEmbed import simple_embed
from src.core.utils.lily_utility import utcnow

from ..components.sLilyModerationComponents import CaseProofsView, ProofsView
from ....utils.components.sLIlyGlobalComponents import CommandInfo


class LilyModerationController:
    def __init__(self, bot_db: BotGlobalsDatabaseAccess, logging_controller: LilyLoggingController) -> None:
        self.logging_controller: LilyLoggingController = logging_controller
        self.bot_db: BotGlobalsDatabaseAccess = bot_db

    """ Ban / Quarantine command helpers """
    async def _validate_moderation_target(
        self, ctx: commands.Context, user_input: discord.User | discord.Member
    ) -> Optional[Tuple[discord.Member | discord.User, BanLimitStatus, List[int]]]:
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("Command requires a guild object to execute.", "cross"))
            return None

        if not isinstance(ctx.author, discord.Member):
            await ctx.reply(embed=simple_embed("Please execute this command inside a guild!", "cross"))
            return None

        user_id = getattr(user_input, "id", None)
        if not user_id:
            await ctx.reply(embed=simple_embed("Invalid user.", "cross"))
            return None

        member: discord.Member | discord.User = user_input
        
        if isinstance(member, discord.Member):
            if member.id == ctx.author.id:
                await ctx.reply(embed=simple_embed("You cannot moderate yourself.", "cross"))
                return None
            
            if member.id == ctx.bot.user.id:
                await ctx.reply(embed=simple_embed("You cannot moderate me baka~.", "cross"))
                return None

            if member.id == ctx.guild.owner_id:
                await ctx.reply(embed=simple_embed("You cannot moderate the server owner.", "cross"))
                return None

            if member.top_role >= ctx.guild.me.top_role:
                await ctx.reply(embed=simple_embed(
                    "I cannot act on this user their role is higher than or equal to mine.", "cross"
                ))
                return None

            if member.top_role >= ctx.author.top_role:
                await ctx.reply(embed=simple_embed(
                    "You cannot act on this user their role is higher than or equal to yours.", "cross"
                ))
                return None

        author_roles = [role.id for role in ctx.author.roles if role.name != "@everyone"]
        status = await self.bot_db.get_ban_limit_status(ctx.guild.id, ctx.author.id, author_roles)

        if status.exceeded:
            await ctx.reply(embed=simple_embed(
                f"Daily limit exceeded.\n{status.remaining_time}", "cross"
            ))
            return None

        return member, status, author_roles

    """ This is common for ban/quarantine, so isolated them seperately """
    async def _notify_and_log(
        self,
        ctx: commands.Context,
        target: discord.Member,
        user: discord.Member | discord.User,
        action: str,
        reason: str,
        proofs: list,
    ) -> int | None:
        try:
            assert isinstance(ctx.author, discord.Member)
            assert isinstance(ctx.guild, discord.Guild)
        except Exception:
            pass

        return await self.logging_controller.log_moderation_action(
            ctx, ctx.author, user, action, reason, proofs.copy()
        )

    async def ban_user(self, ctx: commands.Context, user_input, reason="No reason provided", proofs: list = []):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
            return
        assert isinstance(ctx.author, discord.Member)
        assert isinstance(ctx.guild, discord.Guild)

        """ Validate the target first """
        result = await self._validate_moderation_target(ctx, user_input)
        if result is None:
            return
        member, status, author_roles = result

        await ctx.guild.ban(
            discord.Object(id=member.id),
            reason=f"By {ctx.author} | {reason}",
        )
        ban_message: str = f"Banned: <@{member.id}>\n**Remaining:** {max(0, status.remaining_count - 1)}"

        if proofs:
            await ctx.reply(embed=simple_embed(ban_message))
            await self._notify_and_log(ctx, user_input, member, "ban", reason, proofs)
        else:
            case_id = await self._notify_and_log(ctx, user_input, member, "ban", reason, proofs)
            if case_id:
                view = CaseProofsView(case_id, self.logging_controller, None)
                msg = await ctx.reply(embed=simple_embed(ban_message), view=view)
                view.message = msg
            else:
                await ctx.reply(embed=simple_embed(ban_message))

    async def quarantine_user(self, ctx: commands.Context, user_input, reason="No reason provided", proofs: list = []):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
            return

        assert isinstance(ctx.guild, discord.Guild)

        result = await self._validate_moderation_target(ctx, user_input)
        if result is None:
            return
        member, status, author_roles = result

        if not isinstance(member, discord.Member):
            await ctx.reply(embed=simple_embed("User should be in the guild inorder to quarantine them", 'cross'))
            return

        quarantine_role = (
            discord.utils.get(ctx.guild.roles, name="Quarantine")
            or discord.utils.get(ctx.guild.roles, name="Prisoner")
        )

        if not quarantine_role or quarantine_role >= ctx.guild.me.top_role:
            return await ctx.reply(embed=simple_embed("Quarantine role issue.", "cross"))

        if quarantine_role in member.roles:
            return await ctx.reply(embed=simple_embed("Already quarantined.", "cross"))

        await member.add_roles(quarantine_role, reason=f"Quarantine by {ctx.author} | {reason}")

        quarantine_message: str = f"Quarantined: <@{member.id}>\n**Remaining:** {max(0, status.remaining_count - 1)}"

        if proofs:
            await ctx.reply(embed=simple_embed(quarantine_message))
            await self._notify_and_log(ctx, user_input, member, "quarantine", reason, proofs)
        else:
            case_id = await self._notify_and_log(ctx, user_input, member, "quarantine", reason, proofs)
            if case_id:
                view = CaseProofsView(case_id, self.logging_controller, None)
                msg = await ctx.reply(embed=simple_embed(quarantine_message), view=view)
                view.message = msg
            else:
                await ctx.reply(embed=simple_embed(quarantine_message))

    async def mute_user(self, ctx: commands.Context, user: discord.Member | discord.User, duration: str, reason: str = "No reason provided", proofs: list = []):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("Command requires guild object inorder to execute", 'cross'))
            return
        
        if isinstance(ctx.author, discord.User):
            await ctx.reply(embed=simple_embed("Command requires member object inorder to execute", 'cross'))
            return
        
        if user.id == ctx.bot.user.id:
            await ctx.reply(embed=simple_embed("You cannot mute me baka~.", "cross"))
            return
        
        if isinstance(user, discord.User):
            await ctx.reply(embed=simple_embed("The user has left the server", 'cross'))
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

        if user.id in {ctx.guild.owner_id}:
            await ctx.reply(embed=simple_embed("You cannot mute the server owner", 'cross'))
            return
        
        if user.id == ctx.author:
            await ctx.reply(embed=simple_embed("You cannot mute yourself.", 'cross'))

        try:
            seconds = mute_parser(duration)
            until = utcnow() + timedelta(seconds=seconds)

            await user.edit(timed_out_until=until, reason=reason)

            if len(proofs) > 0:
                await ctx.reply(embed=simple_embed(
                    f"Muted: <@{user.id}>"
                ))

            case_id: int | None = await self.logging_controller.log_moderation_action(ctx, ctx.author, user, "mute", reason, proofs)

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
            await ctx.reply(embed=simple_embed("Failed to mute the user", 'cross'))
        except Exception as e:
            print(f"[MuteUser] {e}")
            await ctx.reply(embed=simple_embed("Failed to mute the user", 'cross'))

    async def unmute(self, ctx: commands.Context, user: discord.Member | discord.User, reason: str="No reason provided"):
        if isinstance(ctx.author, discord.User):
            await ctx.reply(embed=simple_embed("Command requires member object inorder to execute", 'cross'))
            return
        
        if isinstance(user, discord.User):
            await ctx.reply(embed=simple_embed("The user has left the server", 'cross'))
            return
        if not user.timed_out_until or user.timed_out_until <= discord.utils.utcnow():
            await ctx.reply(embed=simple_embed("That user is not muted currently", 'cross'))
            return

        try:
            await user.edit(timed_out_until=None, reason=f"Manual unmute by moderator {ctx.author.mention}")
            await ctx.reply(embed=simple_embed(f"Unmuted: <@{user.id}>"))

            await self.logging_controller.log_moderation_action(
                ctx,
                ctx.author,
                user,
                "unmute",
                reason
            )

        except discord.HTTPException as e:
            await ctx.reply(embed=simple_embed(f"Failed to unmute user. {e}", 'cross'))
        except Exception as e:
            await ctx.reply(embed=simple_embed(f"Exception: {e}", 'cross'))

    async def unban(self, ctx: commands.Context, user: discord.User, bot ,reason: str = "No reason provided"):
        if user is None:
            await ctx.reply(view=CommandInfo(ctx, "Unban", ["unban user", f"unban {ctx.me.mention} Appealed"]))
            return
        
        assert ctx.guild is not None

        try:
            await ctx.guild.unban(user, reason=f"By {ctx.author} | {reason}")
            await ctx.reply(embed=simple_embed(f"Unbanned {user.mention}"))
            await self.logging_controller.log_moderation_action(
                ctx,
                ctx.author,
                user,
                "unban",
                reason
            )
        except discord.NotFound:
            await ctx.reply(embed=simple_embed("This user is not banned.", "cross"))
        except discord.Forbidden:
            await ctx.reply(embed=simple_embed("I don't have permission to unban this user.", "cross"))
        except discord.HTTPException as e:
            await ctx.reply(embed=simple_embed(f"Exception Raised: {e}", "cross"))

    async def release(self, ctx: commands.Context, member: discord.Member | None = None, reason: str = "No reason provided"):
        if member is None:
            await ctx.reply(view=CommandInfo(ctx, "Release", ["release @user", f"release @user Appealed"]))
            return
        
        assert ctx.guild is not None

        quarantine_role = (
            discord.utils.get(ctx.guild.roles, name="Quarantine")
            or discord.utils.get(ctx.guild.roles, name="Prisoner")
        )

        if not quarantine_role:
            await ctx.reply(embed=simple_embed("No Quarantine/Prisoner role found in this server.", "cross"))
            return

        if quarantine_role not in member.roles:
            await ctx.reply(embed=simple_embed(f"{member.mention} is not quarantined.", "cross"))
            return

        try:
            await member.remove_roles(quarantine_role, reason=f"By {ctx.author} | {reason}")
            await ctx.reply(embed=simple_embed(f"Released {member.mention} from quarantine."))
            await self.logging_controller.log_moderation_action(
                ctx,
                ctx.author,
                member,
                "quarantine_release",
                reason
            )
        except discord.Forbidden:
            await ctx.reply(embed=simple_embed("I don't have permission to remove the Quarantine role.", "cross"))
        except discord.HTTPException as e:
            await ctx.reply(embed=simple_embed(f"Failed to remove Quarantine role: {e}", "cross"))

    async def warn(self, ctx: commands.Context, member: discord.Member | discord.User, reason: str, proofs=[]):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("Command requires guild object inorder to execute", 'cross'))
            return
        
        if isinstance(ctx.author, discord.User):
            await ctx.reply(embed=simple_embed("Command requires member object inorder to execute", 'cross'))
            return
        
        if isinstance(member, discord.User):
            await ctx.reply(embed=simple_embed("The user has left the server", 'cross'))
            return
        
        if member.id == ctx.bot.user.id:
            await ctx.reply(embed=simple_embed("You cannot warn me baka~.", "cross"))
            return
        
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.reply(embed=simple_embed("I cannot warn this user", 'cross'))
            return

        if member.top_role >= ctx.author.top_role:
            await ctx.reply(embed=simple_embed("I cannot warn a user with a role equal to or higher than yours.", 'cross'))
            return
        
        if len(proofs) > 0:
            await ctx.reply(embed=simple_embed(f"{member.mention} has been warned"))

        case_id: int | None = await self.logging_controller.log_moderation_action(ctx, ctx.author, member, "warn", reason, proofs)

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

    async def ms(self, ctx: commands.Context, moderator: discord.Member | discord.User, page_start: int = 0, page_end: int = 5):
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
        user: discord.Member | discord.User,
        moderator: discord.User | discord.Member | None = None,
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
        """ This is basically to handle secondary guild.  IN cases where you guys need to have an appeal server and you wanna fetch the modlogs from an secondary server only """

        _guild_id = self.bot_db.get_secondary_guild_id(ctx.guild.id) or ctx.guild.id
        logging_channel_id = self.bot_db.get_channel(_guild_id, "logs_channel")
        if logging_channel_id is not None and result["proofs_exists"]:
            view = ProofsView(result["logs"], logging_channel_id, _guild_id)
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
        
        await ctx.defer()
        
        """ Create an image of moderation last 30 days analytics using matplotlib """
        data = await self.bot_db.get_moderation_monthly_analysis(ctx.guild.id)
        days = [
            datetime.strptime(item["day"], "%Y-%m-%d")
            for item in data
        ]

        totals = [
            item["total"]
            for item in data
        ]

        x_date = mdates.date2num(days)

        plt.figure(figsize=(12, 5))

        plt.plot(
            x_date,
            totals,
            marker="o",
            linewidth=2
        )

        plt.title("Moderation Actions - Last 30 Days")
        plt.xlabel("Date")
        plt.ylabel("Actions")

        plt.xticks(rotation=45)

        plt.grid(True, alpha=0.3)

        for x, y in zip(x_date, totals):
            plt.text(
                x,
                y,
                str(y),
                ha="center",
                va="bottom"
            )

        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(
            buffer,
            format="png",
            dpi=300,
            bbox_inches="tight"
        )

        buffer.seek(0)
        plt.close()

        
        """ Returns the total, monthly, weekly, daily modlogs in a server """
        view = ModerationInsights(ctx.guild.me, self.bot_db)
        view.message = await ctx.reply(view=view, file=discord.File(buffer, filename="moderation_analytics.png"))

    async def setup_mod_appeal(self, ctx: commands.Context):
        if ctx.guild is None:
            return
        
        me = ctx.guild.me

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
            ),

            me: discord.PermissionOverwrite(
                view_channel=True,
                manage_channels=True,
                manage_threads=True,
                send_messages=True,
                read_message_history=True,
            ),

            ctx.author: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                send_messages_in_threads=True,
                attach_files=True,
                embed_links=True,
                add_reactions=True,
                use_external_emojis=True,
                use_external_stickers=True,
            ),
        }

        try:
            forum = await ctx.guild.create_forum(
                name="moderation-appeal",
                available_tags=[
                    discord.ForumTag(name="Pending", emoji="⏳"),
                    discord.ForumTag(name="Accepted", emoji="✅"),
                    discord.ForumTag(name="Denied", emoji="❌"),
                ],
                overwrites=overwrites,
                reason=f"Moderation appeal forum created by {ctx.author}",
            )

            await self.bot_db.set_channel(
                ctx.guild.id,
                forum.id,
                "moderation_appeal"
            )

            await self.bot_db.upsert_appeal_forum(
                ctx.guild.id,
                """
                [
                    {
                        "label": "Why should we remove the punishment?",
                        "description": "Explain why the punishment should be removed and how you will follow the rules in future."
                    },
                    {
                        "label": "Why did this happen?",
                        "description": "Explain what caused the punishment and what you will do to prevent it from happening again."
                    }
                ]
                """
            )

            webhook = await forum.create_webhook(
                name="Lily Webhook"
            )

            await self.bot_db.set_webhook(
                ctx.guild.id,
                "moderation_appeal_dm",
                webhook.url
            )

            await ctx.reply(
                embed=simple_embed(
                    f"Successfully created Appeal forums {forum.mention}.  Appeals will be posted on that forums\nPlease do not delete the `Pending` Tag from the forum"
                )
            )

        except discord.Forbidden:
            raise discord.app_commands.CheckFailure(
                "I don't have permission to create forum channels."
            )

        except discord.HTTPException as e:
            raise discord.app_commands.CheckFailure(
                f"Failed to create the moderation appeal forum: {e}"
            )
        
    async def accept_appeal(self, ctx: commands.Context):
        if ctx.guild is None:
            return

        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.reply(
                embed=simple_embed(
                    "Unable to accept an invalid instigator appeal.",
                    "cross",
                ),
                delete_after=5,
            )

        appeal = await self.bot_db.get_appeal(ctx.channel.id)
        if appeal is None:
            return await ctx.reply(
                embed=simple_embed(
                    "Unable to accept an invalid instigator appeal.",
                    "cross",
                ),
                delete_after=5,
            )
        if appeal["status"] != "pending":
            return await ctx.reply(
                embed=simple_embed(
                    "This appeal is no longer in a valid state for this action.",
                    "cross",
                ),
                delete_after=5,
            )
        
        case = await self.bot_db.get_case(appeal["case_id"])

        if case is None:
            await ctx.reply(embed=simple_embed("Unable to find the case", 'cross'))
            return

        try:
            member = await ctx.guild.fetch_member(case["target_user_id"])
            if case["mod_type"] == "mute":
                await member.edit(timed_out_until=None, reason=f"Appeal accepted by {ctx.author.mention}")
                await self.bot_db.log_moderation_action(
                    ctx.guild.id,
                    ctx.author.id,
                    member.id,
                    "unmute",
                    "Appealed"
                )

            elif case["mod_type"] == "quarantine":
                role = discord.utils.get(ctx.guild.roles, name="Quarantine")
                if role:
                    await member.remove_roles(role, reason=f"Appeal accepted by {ctx.author.mention}")
                    await self.bot_db.log_moderation_action(
                        ctx.guild.id,
                        ctx.author.id,
                        member.id,
                        "quarantine_release",
                        "Appealed"
                    )

            await member.send(embed=simple_embed("Your appeal has been accepted and the action has been lifted"))
        except:
            pass

        assert isinstance(ctx.channel, discord.Thread)
        assert isinstance(ctx.channel.parent, discord.ForumChannel)
        accepted = discord.utils.get(ctx.channel.parent.available_tags, name="Accepted")

        if accepted is None:
            return
        
        await ctx.channel.edit(applied_tags=[accepted])

        await self.bot_db.set_appeal_status(appeal["case_id"], "accepted")
        await ctx.reply(embed=simple_embed(f"Successfully Accepted the appeal and their punishment has been lifted."))

    async def reject_appeal(self, ctx: commands.Context, reason: str | None = None):
        if ctx.guild is None:
            return

        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.reply(
                embed=simple_embed(
                    "Unable to reject an invalid instigator appeal.",
                    "cross",
                ),
                delete_after=5,
            )

        appeal = await self.bot_db.get_appeal(ctx.channel.id)
        if appeal is None:
            return await ctx.reply(
                embed=simple_embed(
                    "Unable to reject an invalid instigator appeal.",
                    "cross",
                ),
                delete_after=5,
            )
        
        if appeal["status"] != "pending":
            return await ctx.reply(
                embed=simple_embed(
                    "This appeal is no longer in a valid state for this action.",
                    "cross",
                ),
                delete_after=5,
            ) 
            
        case = await self.bot_db.get_case(appeal["case_id"])

        if case is None:
            await ctx.reply(embed=simple_embed("Unable to find the case", 'cross'))
            return
        try:
            member = await ctx.guild.fetch_member(case["target_user_id"])
            await member.send(embed=simple_embed(f"Your appeal has been denied. Sorry\n- Reason: {reason or "No reason Provided"}", 'cross'))
        except:
            pass

        assert isinstance(ctx.channel, discord.Thread)
        assert isinstance(ctx.channel.parent, discord.ForumChannel)
        rejected = discord.utils.get(ctx.channel.parent.available_tags, name="Denied")

        if rejected is None:
            print("Tag is not found")
            return
        
        await ctx.channel.edit(applied_tags=[rejected])
        await self.bot_db.set_appeal_status(appeal["case_id"], "rejected")
        await ctx.reply(embed=simple_embed(f"Successfully rejected the appeal."))