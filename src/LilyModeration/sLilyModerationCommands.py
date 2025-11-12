import discord
from discord.ext import commands

import LilyLogging.sLilyLogging as LilyLogging

import Config.sBotDetails as Config
import LilyManagement.sLilyStaffManagement as LSM
import LilyModeration.sLilyModeration as mLily
from LilyRulesets.sLilyRulesets import PermissionEvaluator




class LilyModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=LSM.GetBanRoles)
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

    @PermissionEvaluator(RoleAllowed=LSM.GetBanRoles)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='unban', description='unbans a particular user')
    async def unban(self, ctx, user_id: str):
        user_id = int(user_id.replace("<@", "").replace(Config.bot_command_prefix, "").replace(">", ""))
        
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            await ctx.send(embed=mLily.SimpleEmbed("User not found."))
            return
        except discord.HTTPException as e:
            await ctx.send(f"Exception Raised: {e}")
            return

        try:
            await ctx.guild.unban(user)
            await ctx.send(embed=mLily.SimpleEmbed(f"✅ Unbanned {user.mention}"))
        except discord.NotFound:
            quarantine_role = discord.utils.get(ctx.guild.roles, name="Quarantine")
            if quarantine_role:
                member_obj = ctx.guild.get_member(user_id)
                if member_obj and quarantine_role in member_obj.roles:
                    try:
                        await member_obj.remove_roles(
                            quarantine_role,
                            reason=f"Quarantine removed by {ctx.author} (unban fallback)"
                        )
                        await ctx.send(embed=mLily.SimpleEmbed(f"✅ Removed Quarantine from {member_obj.mention}"))
                        return
                    except discord.Forbidden:
                        await ctx.send("I don't have permission to remove the Quarantine role.")
                        return
                    except discord.HTTPException as e:
                        await ctx.send(f"Failed to remove Quarantine role: {e}")
                        return
            await ctx.send(embed=mLily.SimpleEmbed("This user is not banned and not quarantined!"))
        except discord.Forbidden:
            await ctx.send("I don't have permission to unban this user.")
        except discord.HTTPException as e:
            await ctx.send(f"Exception Raised: {e}")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='mute', description='mutes a user with desired input')
    async def mute(self, ctx:commands.Context, member:discord.Member=None, duration:str="1",*, reason="No reason provided"):
        await mLily.mute_user(ctx, member, duration, reason)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='warn', description='warns a user')
    async def warn(self, ctx:commands.Context, member:discord.Member=None,*, reason="No reason provided"):
        await mLily.warn(ctx, member, reason)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='unmute', description='unmutes a user with desired input')
    async def unmute(self, ctx:commands.Context, member:discord.Member=None):
        await mLily.unmute(ctx, member)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
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

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='modlogs', description='Checks logs for a particular user')
    async def modlogs(self, ctx, mod_type: str = "all", slice_exp: str = None, member: discord.User = None, moderator: discord.User = None):
        slice_obj = None
        if slice_exp:
            try:
                start, stop = (int(x) if x else None for x in slice_exp.split(":"))
                slice_obj = slice(start, stop)
            except Exception:
                await ctx.send(embed=mLily.SimpleEmbed("Slicing Error. Format must be 'start:stop'"))
                return

        target_id = member.id if member else ctx.author.id
        try:
            user = await self.bot.fetch_user(target_id)
        except Exception:
            await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch user with ID {target_id}"))
            return

        try:
            embed = await mLily.mod_logs(
                ctx,
                target_user_id=target_id,
                user=user,
                moderator=moderator,
                mod_type=mod_type,
                slice_expr=slice_obj
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Failed to fetch mod logs: {e}"))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
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

async def setup(bot):
    await bot.add_cog(LilyModeration(bot))