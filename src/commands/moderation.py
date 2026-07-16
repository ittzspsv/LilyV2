import discord
from discord.ext import commands
from typing import Optional

from src.core.utils.components.sLIlyGlobalComponents import CommandInfo
from src.core.utils.embeds.sLilyEmbed import simple_embed
from src.core.features.moderation.controller.lily_moderation_controller import LilyModerationController
from src.core.features.moderation.components.sLilyModerationComponents import AppealForumCustomize
from src.core.features.permissions.lily_permissions import permission
from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess



class LilyModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.controller: Optional[LilyModerationController] = None

    async def on_load(self):
        self.controller = LilyModerationController(self.bot.db, self.bot.logging_controller)

    @commands.hybrid_group()
    async def mod(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Moderation System Command Hierarchy!"))

    @commands.hybrid_group()
    async def case(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily case system Command Hierarchy!"))

    @commands.hybrid_group()
    async def appeal(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Moderation Appeal system Command Hierarchy!"))

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(name='ban', description='Ban a user from the server', aliases=['b'])
    @permission(command_name="ban")
    async def ban(self, ctx: commands.Context, member: discord.User | discord.Member | None = None, *, reason="No reason provided"):
        if self.controller is None:
            return
        if not member:
            return await ctx.reply(
                view=CommandInfo(ctx, "Ban", ["ban user reason", f"ban {ctx.me.mention} Toxicity!", f"b {ctx.me.mention} Not obeying rules!"])
            )
        
        return await ctx.reply(
            embed=simple_embed("This command doesn't works, Try again later", 'cross')
        )

        await ctx.defer()

        attachments = (ctx.message.attachments if ctx.message else [])

        proofs = [
            att for att in attachments
            if att.content_type and att.content_type.startswith(("image/", "video/"))
        ]

        target_user = await self.resolve_user(ctx, member)
        if not target_user:
            return

        await self.controller.ban_user(ctx, target_user, reason, proofs)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(name='quarantine', description='Quarantines an user from this server', aliases=['jail', 'j', 'q'])
    @permission(command_name="quarantine")
    async def quarantine(self, ctx: commands.Context, member: discord.Member | discord.User | None = None, *, reason="No reason provided"):
        if self.controller is None:
            return
        if not member:
            return await ctx.reply(
                view=CommandInfo(ctx, "Quarantine", ["quarantine user reason", f"j {ctx.me.mention} Toxicity!", f"q {ctx.me.mention} Not obeying rules" , f"quarantine {ctx.me.mention} breaking server rules",f"jail {ctx.me.mention} Toxicity!"])
            )

        await ctx.defer()

        attachments = (ctx.message.attachments if ctx.message else [])

        proofs = [
            att for att in attachments
            if att.content_type and att.content_type.startswith(("image/", "video/"))
        ]

        await self.controller.quarantine_user(ctx, member, reason, proofs)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(name='unban', description='Unban a Particular User', aliases=['ub'])
    @permission(command_name="unban")
    async def unban(self, ctx, user: discord.User | None = None, * ,reason: str="No reason provided"):
        if self.controller is None:
            return
        if user is None:
            await ctx.reply(view=CommandInfo(ctx, "Unban", ["unban user", f"unban {ctx.me.mention} Appealed", f"ub {ctx.me.mention} Appealed"]))
            return
        
        await self.controller.unban(ctx, user, self.bot, reason)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(name='release', description='Release a member from quarantine', aliases=['qr', 'r'])
    @permission(command_name="unban")
    async def release(self, ctx, user: discord.Member | None =None, * ,reason: str="No reason provided"):
        if self.controller is None:
            return
        if user is None:
            await ctx.reply(view=CommandInfo(ctx, "Release", ["release user reason", f"release {ctx.me.mention} Appealed", f"qr {ctx.me.mention} Appealed", f'r {ctx.me.mention} Appealed!']))
            return
        
        await self.controller.release(ctx, user, reason)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(name='mute', description='Mute a user with desired input', aliases=['m'])
    @permission(command_name="mute")
    async def mute(self, ctx:commands.Context, member:discord.Member | discord.User | None = None, duration:str="1",*, reason="No reason provided"):
        if self.controller is None:
            return
        await ctx.defer()

        if member is None:
            await ctx.reply(view=CommandInfo(ctx, "Mute", ["mute user time reason", f"mute {ctx.me.mention} 3d Not Obeying Rules", f"mute {ctx.me.mention} 22hr Toxicity!"]))
            return

        proofs = [att for att in ctx.message.attachments if att.content_type and any(att.content_type.startswith(t) for t in ["image/", "video/"])]
        await self.controller.mute_user(ctx, member, duration, reason, proofs)

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.command(name='warn', description='Warn a user with a specific reason')
    @permission(command_name="warn")
    async def warn(self, ctx:commands.Context, member:discord.Member | discord.User | None = None,*, reason="No reason provided"):
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
    async def unmute(self, ctx: commands.Context, member: discord.Member | discord.User | None =None, *, reason: str="No reason provided"):
        if self.controller is None:
            return
        if member is None:
            return await ctx.reply(
                view=CommandInfo(ctx, "Unmute", ["unmute user reason", f"unmute {ctx.me.mention} Appealed"])
            )

        await ctx.defer()
        await self.controller.unmute(ctx, member, reason)

    @mod.command(name='stats', description='checks stats for a particular moderator or yourself')
    @permission(command_name="ms")
    async def ms(self, ctx, member: discord.Member | discord.User | None = None, page_start: int = 0, page_end: int = 0):
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
        member: discord.User | discord.Member | None = None,
        mod_type: str = "all",
        page_start: int = 0,
        page_end: int = 5,
        moderator: discord.User | discord.Member | None = None
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

    @mod.command(name='insights', description='Get detailed moderation insights')
    @permission(command_name="moderation_insights")
    async def moderation_insights(self, ctx: commands.Context):
        if self.controller is None:
            return
        await self.controller.moderation_insights(ctx)

    @case.command(name='edit', description='Edit a case')
    @permission(command_name="case_edit")
    async def case_edit(self, ctx: commands.Context, case_id: str, *, new_reason: str):
        if self.controller is None:
            return
        if case_id is None or new_reason is None:
            return await ctx.reply(
                view=CommandInfo(ctx, "Case Edit", ["edit_case case_id new_reason"])
            )

        await self.controller.case_edit(ctx, int(case_id), new_reason, False)

    @case.command(name='edit_absolute', description='Edit any case')
    @permission(command_name="case_edit_absolute")
    async def case_edit_absolute(self, ctx: commands.Context, case_id: int, *, new_reason: str):
        if self.controller is None:
            return
        if not new_reason:
            return await ctx.reply(
                view=CommandInfo(ctx, "Case Edit Absolute", ["edit_case_absolute case_id new_reason"])
            )

        await self.controller.case_edit(ctx, case_id, new_reason, True)

    @case.command(name='delete', description='Delete a case')
    @permission(command_name="case_delete")
    async def case_delete(self, ctx: commands.Context, case_id: str):
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
  
    @mod.command(name="acronym_add", description="Add an reason acronym")
    @permission(command_name = "mod_acronym_add")
    async def add_mod_acronym(self, ctx: commands.Context, key: str, * ,value: str):
        
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
        
        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        await bot_db.add_moderation_acronym(ctx.author.id, ctx.guild.id, key, value)
        await ctx.reply(embed=simple_embed(f"Successfully Added Moderation Acronym"))

    @mod.command(name="acronym_remove", description="Removes an reason acronym")
    @permission(command_name = "mod_acronym_remove")
    async def remove_mod_acronym(self, ctx: commands.Context, * ,key: str):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
        
        bot_db: BotGlobalsDatabaseAccess = self.bot.db

        await bot_db.remove_moderation_acronym(ctx.author.id, ctx.guild.id, key)
        await ctx.reply(embed=simple_embed(f"Successfully Removed Moderation Acronym"))

    @mod.command(name="acronym_update", description="Updates an reason acronym")
    @permission(command_name = "mod_acronym_update")
    async def update_mod_acronym(self, ctx: commands.Context, key: str, * ,value: str):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
        
        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        await bot_db.update_moderation_acronym(ctx.author.id, ctx.guild.id, key, value)

        await ctx.reply(embed=simple_embed(f"Successfully Updated Moderation Acronym"))

    @mod.command(name="acronyms", description="Display all moderation acronyms")
    @permission(command_name = "mod_acronyms")
    async def get_mod_acronym(self, ctx: commands.Context):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
        
        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        result: dict[str, str] = await bot_db.get_moderation_acronyms(ctx.author.id, ctx.guild.id)

        acronyms = ""
        for key, value in result.items():
            acronyms += f"- **{key}** : {value}\n"

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Moderation Acronyms",
            description=acronyms,
            color=16777215
        )
        await ctx.reply(embed=embed)

    @mod.command(name="acronym_transfer", description="Transfer an acronym to a members at a role")
    @permission(command_name = "mod_acronym_transfer")
    async def transfer_mod_acronym(self, ctx: commands.Context, target: discord.Member):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
        
        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        result: dict[str, str] = await bot_db.get_moderation_acronyms(ctx.author.id, ctx.guild.id)

        for key, value in result.items():
            await bot_db.add_moderation_acronym(target.id, ctx.guild.id, key, value)

        await ctx.reply(embed=simple_embed(f"Successfully transferred moderation acronym to {target.mention}"))

        
    @appeal.command(name="setup", description="Setup Moderation Appeal for this server")
    @permission(command_name = "mod_appeal_management")
    async def setup_appeal(self, ctx: commands.Context):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
        
        if self.controller is not None:
            await self.controller.setup_mod_appeal(
                ctx
            )

    @appeal.command(
        name="forum",
        description="Configure the appeal forum that users can fill out."
    )
    @permission(command_name="mod_appeal_management")
    async def configure_appeal_forum(
        self,
        ctx: commands.Context,
    ):
        if ctx.guild is None:
            return await ctx.reply(
                embed=simple_embed(
                    "This command can only be used inside a guild.",
                    "cross",
                )
            )
        
        if ctx.interaction is None:
            return await ctx.reply(
                embed=simple_embed(
                    "Use this command as an Interaction based one.",
                    "cross",
                )
            )

        if self.controller is not None:
            await ctx.interaction.response.send_modal(
                AppealForumCustomize(self.bot.db)
            )


    @appeal.command(name="accept", description="Accept an appeal")
    @permission(command_name = "mod_appeal_handlers")
    async def accept_appeal(self, ctx: commands.Context):
        if self.controller is not None:
            await self.controller.accept_appeal(ctx)

    @appeal.command(name="reject", description="Deny an appeal")
    @permission(command_name = "mod_appeal_handlers")
    async def reject_appeal(self, ctx: commands.Context, reason: str):
        if self.controller is not None:
            await self.controller.reject_appeal(ctx, reason)


async def setup(bot):
    cog = LilyModeration(bot)
    await bot.add_cog(cog)

    if hasattr(cog, "on_load"):
        await cog.on_load()