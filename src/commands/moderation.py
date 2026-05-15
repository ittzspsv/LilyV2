import discord
from discord.ext import commands

from core.utils.components.sLIlyGlobalComponents import CommandInfo
from core.utils.embeds.sLilyEmbed import simple_embed
from typing import Optional
from core.features.moderation.controller.lily_moderation_controller import LilyModerationController
from core.features.permissions.lily_permissions import permission



class LilyModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.controller: Optional[LilyModerationController] = None

    async def on_load(self):
        self.controller = LilyModerationController(self.bot.logs_db, self.bot.db, self.bot.logging_controller)

    async def resolve_user(self, ctx, member: str):
        try:
            return await commands.MemberConverter().convert(ctx, member)
        except commands.MemberNotFound:
            try:
                user_id = int(member)
                return await ctx.bot.fetch_user(user_id)
            except ValueError:
                await ctx.reply(embed=simple_embed("Invalid user ID", 'cross'))
            except discord.NotFound:
                await ctx.reply(embed=simple_embed("User not found.", 'cross'))
            except discord.HTTPException as e:
                await ctx.reply(embed=simple_embed(f"Fetch failed: {e}", 'cross'))
        return None

    @commands.hybrid_group()
    async def moderation(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Moderation System Command Hierarchy!"))

    @commands.hybrid_group()
    async def case(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily case system Command Hierarchy!"))

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='ban', description='ban/quarantine a user from the server')
    @permission(command_name="ban")
    async def ban(self, ctx: commands.Context, member: str = None, *, reason="No reason provided"):
        if self.controller is None:
            return
        if not member:
            return await ctx.reply(
                view=CommandInfo(ctx, "Ban", ["ban user reason", f"ban {ctx.me.mention} Toxicity!"])
            )

        await ctx.defer()

        attachments = (ctx.message.attachments if ctx.message else []) or \
                    (ctx.interaction.attachments if ctx.interaction else [])

        proofs = [
            att for att in attachments
            if att.content_type and att.content_type.startswith(("image/", "video/"))
        ]

        target_user = await self.resolve_user(ctx, member)
        if not target_user:
            return

        await self.controller.ban_user(ctx, target_user, reason, proofs)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='unban', description='Unban a Particular User')
    @permission(command_name="unban")
    async def unban(self, ctx, user_id: str=None):
        await ctx.defer()
        if user_id is None:
            await ctx.reply(view=CommandInfo(ctx, "Unban", ["unban user", f"unban {ctx.me.mention} Appealed"]))
            return
        usr_id: int = int(user_id.replace("<@", "").replace(">", ""))
        
        try:
            user = await self.bot.fetch_user(usr_id)
        except discord.NotFound:
            await ctx.reply(embed=simple_embed("User not found."))
            return
        except discord.HTTPException as e:
            await ctx.reply(f"Exception Raised: {e}")
            return

        try:
            await ctx.guild.unban(user)
            await ctx.reply(embed=simple_embed(f"Unbanned {user.mention}"))
        except discord.NotFound:
            quarantine_role = discord.utils.get(ctx.guild.roles, name="Quarantine")
            if quarantine_role:
                member_obj = await ctx.guild.fetch_member(usr_id)
                if member_obj and quarantine_role in member_obj.roles:
                    try:
                        await member_obj.remove_roles(quarantine_role, reason=f"Quarantine Removed by {ctx.author.mention}")

                        await ctx.reply(embed=simple_embed(f"Removed Quarantine from {member_obj.mention}"))
                        return
                    except discord.Forbidden:
                        await ctx.reply("I don't have permission to remove the Quarantine role.")
                        return
                    except discord.HTTPException as e:
                        await ctx.reply(f"Failed to remove Quarantine role: {e}")
                        return
            await ctx.reply(embed=simple_embed("This user is not banned and not quarantined!"))
        except discord.Forbidden:
            await ctx.reply("I don't have permission to unban this user.")
        except discord.HTTPException as e:
            await ctx.reply(f"Exception Raised: {e}")

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='mute', description='Mute a user with desired input')
    @permission(command_name="unban")
    async def mute(self, ctx:commands.Context, member:discord.Member, duration:str="1",*, reason="No reason provided"):
        if self.controller is None:
            return
        await ctx.defer()

        if member is None:
            await ctx.reply(view=CommandInfo(ctx, "Mute", ["mute user time reason", f"mute {ctx.me.mention} 3d Not Obeying Rules", f"mute {ctx.me.mention} 22hr Toxicity!"]))
            return
        proofs = [att for att in ctx.message.attachments if att.content_type and any(att.content_type.startswith(t) for t in ["image/", "video/"])]
        await self.controller.mute_user(ctx, member, duration, reason, proofs)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='warn', description='Warn a user with a specific reason')
    @permission(command_name="warn")
    async def warn(self, ctx:commands.Context, member:discord.Member,*, reason="No reason provided"):
        if self.controller is None:
            return
        await ctx.defer()
        if member is None:
            await ctx.reply(view=CommandInfo(ctx, "Warn", ["warn user reason", f"warn {ctx.me.mention} Not Obeying Rules!"]))
            return
        proofs = proofs = [att for att in ctx.message.attachments if att.content_type and any(att.content_type.startswith(t) for t in ["image/", "video/"])]
        await self.controller.warn(ctx, member, reason, proofs)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='unmute', description='unmutes a user with desired input')
    @permission(command_name="unmute")
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        if self.controller is None:
            return
        if member is None:
            return await ctx.reply(
                view=CommandInfo(ctx, "Unmute", ["unmute user reason", f"warn {ctx.me.mention} Appealed"])
            )

        await ctx.defer()
        await self.controller.unmute(ctx, member)

    @moderation.command(name='stats', description='checks stats for a particular moderator or yourself')
    @permission(command_name="ms")
    async def ms(self, ctx, member: discord.Member = None, page_start: int = 0, page_end: int = 0):
        if self.controller is None:
            return
        await ctx.defer()

        user = member or ctx.author

        await self.controller.ms(
            ctx=ctx,
            moderator=user,
            page_start=page_start,
            page_end=page_end
        )

    @case.command(name='list', description='Checks case logs for a particular user')
    @permission(command_name="modlogs")
    async def modlogs(
        self,
        ctx,
        member: discord.User = None,
        mod_type: str = "all",
        page_start: int = 0,
        page_end: int = 5,
        moderator: discord.User = None
    ):
        if self.controller is None:
            return

        await ctx.defer()

        target_id = member.id if member else ctx.author.id

        try:
            user = await self.bot.fetch_user(target_id)
        except Exception:
            return

        try:
            await self.controller.mod_logs(
                ctx,
                target_user_id=target_id,
                user=user,
                moderator=moderator,
                mod_type=mod_type,
                page_start=page_start,
                page_end=page_end
            )

        except Exception as e:
            print(f"Exception [ModLogs] : {e}")

    @moderation.command(name='insights', description='Get detailed moderation insights')
    @permission(command_name="moderation_insights")
    async def moderation_insights(self, ctx: commands.Context):
        if self.controller is None:
            return
        await self.controller.moderation_insights(ctx)

    @case.command(name='edit', description='Edit a case')
    @permission(command_name="case_edit")
    async def case_edit(self, ctx: commands.Context, case_id: str=None, *, new_reason: str=None):
        if self.controller is None:
            return
        if case_id is None or new_reason is None:
            return await ctx.reply(
                view=CommandInfo(ctx, "Case Edit", ["edit_case case_id new_reason"])
            )

        await self.controller.case_edit(ctx, int(case_id), new_reason, False)

    @case.command(name='edit_absolute', description='Edit any case')
    @permission(command_name="case_edit_absolute")
    async def case_edit_absolute(self, ctx: commands.Context, case_id: int = None, *, new_reason: str = None):
        if self.controller is None:
            return
        if not new_reason:
            return await ctx.reply(
                view=CommandInfo(ctx, "Case Edit Absolute", ["edit_case_absolute case_id new_reason"])
            )

        await self.controller.case_edit(ctx, case_id, new_reason, True)

    @case.command(name='delete', description='Delete a case')
    @permission(command_name="case_delete")
    async def case_delete(self, ctx: commands.Context, case_id: str = None):
        if self.controller is None:
            return
        if not case_id:
            return await ctx.reply(
                view=CommandInfo(ctx, "Case Delete", ["case_delete case_id"])
            )

        await self.controller.case_delete(ctx, int(case_id))

    @case.command(name='attach', description='Attach proofs for a case')
    @permission(command_name="case_attach")
    async def case_attach(self, ctx: commands.Context):
        if self.controller is None:
            return
        
        await self.controller.logging_controller.log_proofs(ctx)

    @case.command(name='proofs', description='Retrieve all proofs of an case')
    @permission(command_name="case_proofs")
    async def case_retrieve(self, ctx: commands.Context, case_id: str):
        if self.controller is None:
            return
        
        await self.controller.logging_controller.retrieve_proofs(ctx, int(case_id))



    @commands.hybrid_command(name='queue', description='Get moderation queue')
    @permission(command_name="queue")
    async def queue(self, ctx: commands.Context):
        if self.controller is None:
            return
        await self.controller.fetch_moderation_queue(ctx)

    @moderation.command(name='queue_remove', description='Remove member from queue')
    @permission(command_name="queue_remove")
    async def queue_remove(self, ctx: commands.Context, member: discord.Member):
        if self.controller is None:
            return
        await self.controller.remove_member_from_queue(ctx, member)
    
async def setup(bot):
    cog = LilyModeration(bot)
    await bot.add_cog(cog)

    if hasattr(cog, "on_load"):
        await cog.on_load()