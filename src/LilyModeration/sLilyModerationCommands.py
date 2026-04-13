import discord
from discord.ext import commands

from Misc.sLIlyGlobalComponents import CommandInfo

import Config.sBotDetails as Config
import LilyManagement.sLilyStaffManagement as LSM
import LilyModeration.sLilyModeration as mLily
from Misc.sLilyEmbed import simple_embed
import Misc.sLilyComponentV2 as CV2
from LilyRulesets.sLilyRulesets import PermissionEvaluator




class LilyModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @PermissionEvaluator(RoleAllowed=LSM.GetBanRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='ban', description='bans a user with config = limited')
    async def ban(self, ctx: commands.Context, member: str = None, *, reason="No reason provided"):
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

        await mLily.ban_user(ctx, target_user, reason, proofs)

    @PermissionEvaluator(RoleAllowed=LSM.GetBanRoles)
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.hybrid_command(name='execute', description='Execute an user with cutscene (WIP)')
    async def execute(self, ctx: commands.Context, member: discord.Member):
        if not member:
            await ctx.reply(view=CommandInfo(ctx, "Execute", ["execute user", f"execute {ctx.me.mention}"]))
            return
        await mLily.execute(ctx, member)

    @PermissionEvaluator(RoleAllowed=LSM.GetBanRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='unban', description='Unban a Particular User')
    async def unban(self, ctx, user_id: str=None):
        await ctx.defer()
        if user_id is None:
            await ctx.reply(view=CommandInfo(ctx, "Unban", ["unban user", f"unban {ctx.me.mention} Appealed"]))
            return
        user_id = int(user_id.replace("<@", "").replace(Config.bot_command_prefix, "").replace(">", ""))
        
        try:
            user = await self.bot.fetch_user(user_id)
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
                member_obj = await ctx.guild.fetch_member(user_id)
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

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='mute', description='Mute a user with desired input')
    async def mute(self, ctx:commands.Context, member:discord.Member=None, duration:str="1",*, reason="No reason provided"):
        await ctx.defer()

        if member is None:
            await ctx.reply(view=CommandInfo(ctx, "Mute", ["mute user time reason", f"mute {ctx.me.mention} 3d Not Obeying Rules", f"mute {ctx.me.mention} 22hr Toxicity!"]))
            return
        proofs = [att for att in ctx.message.attachments if att.content_type and any(att.content_type.startswith(t) for t in ["image/", "video/"])]
        await mLily.mute_user(ctx, member, duration, reason, proofs)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='warn', description='Warn a user with a specific reason')
    async def warn(self, ctx:commands.Context, member:discord.Member=None,*, reason="No reason provided"):
        await ctx.defer()
        if member is None:
            await ctx.reply(view=CommandInfo(ctx, "Warn", ["warn user reason", f"warn {ctx.me.mention} Not Obeying Rules!"]))
            return
        proofs = proofs = [att for att in ctx.message.attachments if att.content_type and any(att.content_type.startswith(t) for t in ["image/", "video/"])]
        await mLily.warn(ctx, member, reason, proofs)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='unmute', description='unmutes a user with desired input')
    async def unmute(self, ctx:commands.Context, member:discord.Member=None):
        if member is None:
            await ctx.reply(view=CommandInfo(ctx, "Unmute", ["unmute user reason", f"warn {ctx.me.mention} Appealed"]))
            return
        await ctx.defer()
        await mLily.unmute(ctx, member)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='ms', description='checks logs for a particular moderator')
    async def ms(self, ctx, member: discord.Member=None, page_start: int=0, page_end: int=0):
        await ctx.defer()
        user: discord.Member = None
        try:
            if not member:
                user = ctx.author
            else:
                user = member
            embed = await mLily.ms(ctx=ctx, moderator=user, page_start=page_start, page_end=page_end)
            await ctx.reply(embeds=embed)

        except Exception as e:
            print(f"Exception [ms] {e}")
            await ctx.reply(embed=simple_embed(f"No Modlogs Available", 'cross'))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='modlogs', description='Checks logs for a particular user')
    async def modlogs(self, ctx, member: discord.User = None, mod_type: str = "all", page_start: int=0, page_end: int=5, moderator: discord.User = None):
        await ctx.defer()
        target_id = member.id if member else ctx.author.id
        try:
            user = await self.bot.fetch_user(target_id)
        except Exception:
            await ctx.reply(embed=simple_embed(f"No Mod Logs Returned", 'cross'))
            return

        try:
            embed = await mLily.mod_logs(
                ctx,
                target_user_id=target_id,
                user=user,
                moderator=moderator,
                mod_type=mod_type,
                page_start=page_start,
                page_end=page_end
            )
            await ctx.reply(embeds=embed)
        except Exception as e:
            print(f"Exception [ModLogs] : {e}")
            await ctx.reply(embed=simple_embed(f"No Mod Logs Returned", 'cross'))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='mod_insights', description='Get an detailed insights about moderation on this server')
    async def moderation_insights(self, ctx: commands.Context):
        await mLily.moderation_insights(ctx)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='fetch_ban_cd',description='Fetches all ban cooldowns less than or equal to 24 hours')
    async def ban_cd(self, ctx: commands.Context, member: discord.Member | None = None):
        target = member or ctx.author

        target_role_ids = [role.id for role in target.roles]

        cooldown_text = await mLily.remaining_Ban_time_text(
            ctx,
            moderator_id=target.id,
            moderator_role_ids=target_role_ids
        )

        if not cooldown_text:
            await ctx.reply(
                f"**{target.display_name}** has no active ban cooldowns."
            )
            return

        await ctx.reply(
            f"**Ban Cooldowns for {target.display_name}:**\n{cooldown_text}"
        )

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='edit_case',description='Edit a case (only cases initiated by the command interactor can be edited)')
    async def case_edit(self, ctx: commands.Context, case_id: int=None, * ,new_reason: str=None):
        if case_id is None or new_reason is None:
            await ctx.reply(
                view=CommandInfo(
                    ctx,
                    "Case Edit",
                    ["edit_case case_id new_reason", "edit_case 7777 Handled by mistake"]
                )
            )
            return
        await mLily.CaseEdit(ctx, case_id, new_reason, False)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff Manager', 'Head Administrator', 'Developer')))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='edit_case_absolute',description="Edit a case (can edit any user's case")
    async def case_edit_absolute(self, ctx: commands.Context, case_id: int=None, *, new_reason: str=None):
        if not new_reason:
            await ctx.reply(
                view=CommandInfo(
                    ctx,
                    "Case Edit Absolute",
                    [
                        "edit_case_absolute case_id new_reason",
                        "edit_case_absolute 7777 Handled by mistake"
                    ]
                )
            )
            return

        await mLily.CaseEdit(ctx, case_id, new_reason, True)


    
async def setup(bot):
    await bot.add_cog(LilyModeration(bot))