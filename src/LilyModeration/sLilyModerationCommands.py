import discord
from discord.ext import commands

import LilyLogging.sLilyLogging as LilyLogging

import Config.sBotDetails as Config
import LilyModeration.sLilyModeration as mLily
from LilyRulesets.sLilyRulesets import PermissionEvaluator




class LilyModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=lambda: list(Config.limit_Ban_details.keys()))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='ban', description='bans a user with config = limited')
    async def ban(self, ctx:commands.Context, member: str = "", *, reason="No reason provided"):
        proofs = []
        role_ids = [role.id for role in ctx.author.roles if role.name != "@everyone"]

        for attachment in ctx.message.attachments:
            if attachment.content_type and any(attachment.content_type.startswith(t) for t in ["image/", "video/"]):
                file = await attachment.to_file()
                proofs.append(file)
            else:
                await ctx.send(f"File type {attachment.filename} Not Supported, so it will not be sent to logs channel")

        try:
            target_user = None
            try:
                target_user = await commands.MemberConverter().convert(ctx, member)
            except commands.MemberNotFound:
                try:
                    user_id = int(member)
                    target_user = await ctx.bot.fetch_user(user_id)
                except ValueError as v:
                    await ctx.send(embed=mLily.SimpleEmbed(f"Value Error {v}"))
                    return
                except discord.NotFound:
                    await ctx.send(embed=mLily.SimpleEmbed(f"User ID {member} not found. Please check the ID."))
                    return
                except discord.HTTPException as e:
                    await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch user data: {e}"))
                    return

            if not target_user:
                await ctx.send(embed=mLily.SimpleEmbed("No Valid Users to Ban"))
                return
            if target_user.id in Config.ids:
                await ctx.send(embed=mLily.SimpleEmbed(f"you can't use my commands against a developer {ctx.author.mention}"))
                return

            if not await mLily.exceeded_ban_limit(ctx, ctx.author.id, role_ids):
                await mLily.ban_user(ctx, target_user, reason, proofs)
            else:
                await ctx.send(embed=mLily.SimpleEmbed(
                    f"Cannot ban the user! I'm Sorry But you have exceeded your daily limit\n"
                    f"You can ban in {await mLily.remaining_Ban_time(ctx, ctx.author.id, role_ids)}"
                ))

        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"An error occurred: {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: list(Config.limit_Ban_details.keys()))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='unban', description='unbans a particular user')
    async def unban(self, ctx, user_id: str):
        user_id = int(user_id.replace("<@", "").replace(Config.bot_command_prefix, "").replace(">", ""))    
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(embed=mLily.SimpleEmbed(f"Unbanned {user.mention}"))
        except discord.NotFound:
            await ctx.send(embed=mLily.SimpleEmbed("This user is not banned!"))
        except discord.Forbidden:
            await ctx.send(f"Exception Raised: {discord.Forbidden}")
        except discord.HTTPException as e:
            await ctx.send(f"Exception Raised: {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='mute', description='mutes a user with desired input')
    async def mute(self, ctx:commands.Context, member:discord.Member=None, duration:str="1",*, reason="No reason provided"):
        await mLily.mute_user(ctx, member, duration, reason)

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='unmute', description='unmutes a user with desired input')
    async def unmute(self, ctx:commands.Context, member:discord.Member=None):
        await mLily.unmute(ctx, member)

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='ms', description='checks logs for a particular moderator')
    async def ms(self, ctx, slice_exp: str = None, member: discord.Member=None):
        try:
            try:
                start, stop = (int(x) if x else 0 for x in slice_exp.split(":"))
            except ValueError:
                await ctx.send(embed=mLily.SimpleEmbed("Slicing Error. Make sure your slicing is in the format 'start:stop'"))
                return
            except Exception as e:
                await ctx.send(embed=mLily.SimpleEmbed(f"Error while parsing slice: {e}"))
                return

            if not member:
                try:
                    user = await self.bot.fetch_user(ctx.author.id)
                    embed = await mLily.ms(ctx,ctx.author.id, user, slice_expr=slice(start, stop))
                except Exception as e:
                    await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch user or display logs: {e}"))
                    return
            else:
                try:
                    user = await self.bot.fetch_user(member.id)
                    embed = await mLily.ms(ctx, member.id, user, slice_expr=slice(start, stop))
                except ValueError:
                    await ctx.send(embed=mLily.SimpleEmbed("Member ID must be a integer"))
                    return
                except Exception as e:
                    await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch member ban logs csv: {e}"))
                    return

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"An unexpected error occurred: {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='modlogs', description='checks logs for particular user')
    async def modlogs(self, ctx, slice_exp: str = None, member: discord.User = None):
        try:
            try:
                start, stop = (int(x) if x else 0 for x in slice_exp.split(":"))
            except ValueError:
                await ctx.send(embed=mLily.SimpleEmbed("Slicing Error. Make sure your slicing is in the format 'start:stop'"))
                return
            except Exception as e:
                await ctx.send(embed=mLily.SimpleEmbed(f"Error while parsing slice: {e}"))
                return

            if not member:
                try:
                    user = await self.bot.fetch_user(ctx.author.id)
                    embed = await mLily.mod_logs(ctx,ctx.author.id, user, slice_expr=slice(start, stop))
                except Exception as e:
                    await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch user or display logs: {e}"))
                    return
            else:
                try:
                    user = await self.bot.fetch_user(member.id)
                    embed = await mLily.mod_logs(ctx, member.id, user, slice_expr=slice(start, stop))
                except ValueError as v:
                    await ctx.send(embed=mLily.SimpleEmbed(f"{v}"))
                    return
                except Exception as e:
                    await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch member ban logs csv: {e}"))
                    return

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"An unexpected error occurred: {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='checkbanlog', description='checks ban log for a particular user')
    async def checkbanlog(self, ctx, member: str = ""):
        try:
            if not member:
                await ctx.send("No Member has been passed in!")
            else:
                try:
                    await mLily.checklogs(ctx, member)
                except ValueError:
                    await ctx.send(embed=mLily.SimpleEmbed("Member ID must be a literal"))
                    return
                except Exception as e:
                    await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch logs for the member: {e}"))
                    return


        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"An unexpected error occurred: {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles)
    @commands.hybrid_command(name="blacklist_user", description="Blacklist a user ID from using limited ban command.")
    async def blacklist_user(self, ctx: commands.Context, user: discord.Member):
        current_ids = await Config.load_exceptional_ban_ids(ctx)

        if user.id in current_ids:
            await ctx.send(embed=mLily.SimpleEmbed("User is already blacklisted"))
            return
        if user.id in Config.ids:
            await ctx.send(embed=mLily.SimpleEmbed(f"you can't use my commands against me {ctx.author.mention}"))
            return

        current_ids.append(user.id)
        await Config.save_exceptional_ban_ids(ctx, current_ids)

        await ctx.send(embed=mLily.SimpleEmbed(f"<@{user.id}> Got Blacklisted"))
        await LilyLogging.WriteLog(ctx, ctx.author.id, f"has Blacklisted <@{user.id}> from using **Limited Bans**")

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles)
    @commands.hybrid_command(name="unblacklist_user", description="Remove a user ID from the limited ban blacklist.")
    async def unblacklist_user(self, ctx: commands.Context, user: discord.Member):
        current_ids = await Config.load_exceptional_ban_ids(ctx)

        if user.id not in current_ids:
            await ctx.send(embed=mLily.SimpleEmbed("User is not blacklisted."))
            return

        current_ids.remove(user.id)
        await Config.save_exceptional_ban_ids(ctx, current_ids)

        await ctx.send(embed=mLily.SimpleEmbed(f"<@{user.id}> has been removed from the blacklist."))
        await LilyLogging.WriteLog(ctx, ctx.author.id, f"has removed <@{user.id}> from the **Limited Bans** blacklist.")

async def setup(bot):
    await bot.add_cog(LilyModeration(bot))