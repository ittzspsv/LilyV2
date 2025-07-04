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

            if not mLily.exceeded_ban_limit(ctx, ctx.author.id, role_ids):
                await mLily.ban_user(ctx, target_user, reason, proofs)
            else:
                await ctx.send(embed=mLily.SimpleEmbed(
                    f"Cannot ban the user! I'm Sorry But you have exceeded your daily limit\n"
                    f"You can ban in {mLily.remaining_Ban_time(ctx, ctx.author.id, role_ids)}"
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
    @commands.hybrid_command(name='logs', description='checks logs for a particular moderator (ban informations)')
    async def logs(self, ctx, slice_exp: str = None, member: str = ""):
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
                    embed = mLily.display_logs(ctx,ctx.author.id, user, slice_expr=slice(start, stop))
                except Exception as e:
                    await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch user or display logs: {e}"))
                    return
            else:
                try:
                    user = await self.bot.fetch_user(int(member))
                    embed = mLily.display_logs(ctx, int(member), user, slice_expr=slice(start, stop))
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

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='fetchbanlog', description='fetches ban log of an user in a .csv format for quick analysis')
    async def fetchbanlog(self, ctx, user: str = None):
        if user is None:
            target = ctx.author
        else:
            try:
                user_id = int(user.replace("<@", "").replace(Config.bot_command_prefix, "").replace(">", ""))
                target = await ctx.guild.fetch_member(user_id)
            except (ValueError, discord.NotFound):
                return await ctx.send(embed=mLily.SimpleEmbed("Could not find that user."))

        file_name = f"storage/{ctx.guild.id}/banlogs/{target.id}-logs.csv"
        try:
            with open(file_name, "rb") as f:
                await ctx.send(file=discord.File(f, filename=file_name))
        except FileNotFoundError:
            await ctx.send(embed=mLily.SimpleEmbed(f"No logs found for user {target.mention}."))
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Excepted Error : {e}."))


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

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name="vmute", description="mutes a user specific to voice channel only")
    async def vmute(self, ctx:commands.Context, user:discord.Member, timeframe:str="10", *, reason:str=""):
        try:
            await mLily.VoiceMute(user, timeframe, reason, ctx.channel)
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Exception {e}"))
        
    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name="vunmute", description="unmutes a user specific to voice channel only")
    async def vunmute(self, ctx:commands.Context, user:discord.Member):
        try:
            await mLily.VoiceUnmute(user, ctx.channel)
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Exception {e}"))


async def setup(bot):
    await bot.add_cog(LilyModeration(bot))