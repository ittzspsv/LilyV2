from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator
import LilyLogging.sLilyLogging as LilyLogging
import LilyModeration.sLilyRoleManagement as rLily
import LilyModeration.sLilyModeration as mLily

import discord
from discord.ext import commands
import Config.sBotDetails as Config
from enum import Enum

import asyncio

class LilyUtility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ROLE UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles + Config.TrustedStaffRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name="assign_role", description="Assign a role to a user if it's allowed")
    async def assign_role(self, ctx: commands.Context, user: discord.Member, role: discord.Role):
        assignable_roles = await Config.load_roles(ctx)
        role_id_str = str(role.id)

        if role_id_str not in assignable_roles:
            await ctx.reply(f"The role {role.name} is not assignable.")
            return

        role_priority = assignable_roles[role_id_str].lower()

        if role_priority == "low":
            if not rPermissionEvaluator(ctx, RoleAllowed=Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles + Config.TrustedStaffRoles):
                    await ctx.reply("You are not allowed to assign role.")
                    return
        elif role_priority == "high":
            if not rPermissionEvaluator(ctx, RoleAllowed=Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=Config.BlacklistedRoles):
                    await ctx.reply("You are not allowed to give high priority roles")
                    return
        else:
            await ctx.reply(f"Invalid priority level {role_priority} for role {role.name}.")
            return

        if role in user.roles:
            await ctx.reply(f"{user.display_name} already has the {role.name} role.")
            return

        if role.position >= ctx.author.top_role.position and ctx.author.id not in Config.owner_ids:
            await ctx.reply("You cannot assign a role that is higher than or equal to your highest role.")
            return

        try:
            await user.add_roles(role, reason=f"Assigned by {ctx.author}")
            await ctx.reply(f"Assigned {role.name} to {user.display_name}.")
            await self.bot.WriteLog(ctx, ctx.author.id, f"Assigned <@&{role.id}> to {user.display_name}.")
        except discord.Forbidden:
            await ctx.reply("I don't have permission to assign that role.")
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=lambda: Config.BlacklistedRoles)
    @commands.hybrid_command(name="unassign_role", description="Remove a role from a user if it's allowed")
    async def unassign_role(self, ctx: commands.Context, user: discord.Member, role: discord.Role):
        assignable_roles = await Config.load_roles(ctx)
        role_id_str = str(role.id)

        if role_id_str not in assignable_roles:
            await ctx.reply(f"The role {role.name} is not assignable, so it can't be removed.")
            return

        role_priority = assignable_roles[role_id_str].lower()

        if role_priority == "low":
            if rPermissionEvaluator(RoleAllowed=Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles + Config.TrustedStaffRoles):
                await ctx.reply("You are not allowed to remove this role.", ephemeral=True)
                return
        elif role_priority == "high":
            if rPermissionEvaluator(RoleAllowed=Config.StaffManagerRoles + Config.DeveloperRoles + Config.OwnerRoles, RoleBlacklisted=Config.BlacklistedRoles):
                await ctx.reply("You are not allowed to remove this high-priority role.", ephemeral=True)
                return
        else:
            await ctx.reply(f"Invalid priority level `{role_priority}` for role {role.name}.", ephemeral=True)
            return

        if role not in user.roles:
            await ctx.reply(f"{user.display_name} does not have the {role.name} role.")
            return

        if role.position >= ctx.author.top_role.position and ctx.author.id not in Config.owner_ids:
            await ctx.reply("You cannot remove a role that is higher than or equal to your highest role.")
            return
        try:
            await user.remove_roles(role, reason=f"Removed by {ctx.author}")
            await ctx.reply(f"Removed {role.name} from {user.display_name}.")
            await self.bot.WriteLog(ctx, ctx.author.id, f"Removed <@&{role.id}> from {user.display_name}.")
        except discord.Forbidden:
            await ctx.reply("I don't have permission to remove that role.")
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")


    class Priority(str, Enum):
        low = "low"
        high = "high"
    @PermissionEvaluator(RoleAllowed=lambda: Config.OwnerRoles)
    @commands.hybrid_command(name="make_role_assignable", description="Allows specific users to assign this role")
    async def make_roles_assignable(self, ctx: commands.Context, role: discord.Role, priority: Priority):
        try:
            assignable_roles = await Config.load_roles(ctx)
        except Exception as e:
            await ctx.reply(f"Failed to load assignable roles: {e}")
            return

        try:
            if str(role.id) not in assignable_roles:
                try:
                    await Config.save_roles(ctx, role.id, priority.value)
                    await ctx.reply(f"Added Role {role.name} to assignables with {priority.value} priority.")
                except Exception as e:
                    await ctx.reply(f"Failed to save role with exception: `{e}`")
            else:
                await ctx.reply(f"Role {role.name} already exists in assignables.")
        except Exception as e:
            await ctx.reply(f"Unhandled Exception: `{e}`", ephemeral=True)


    ''' UNCOMMENTED NOT IN USE
    @commands.hybrid_command(name="create_role", description="Creates a role with config = LIMITED")
    async def create_role(self, ctx: commands.Context,name: str,color: str = "",assignable_priority: Priority = Priority.high,position_type: rLily.PositionType = rLily.PositionType.Bottom,role: str = ""):
        await ctx.defer()

        validated_data, error_embed = await rLily.validate_data(ctx, name, color, position_type, role)
        if error_embed:
            await ctx.send(embed=error_embed)
            return

        try:
            new_role = await rLily.create_guild_role(ctx,
                guild=validated_data["guild"],
                name=name,
                role_color=validated_data["role_color"],
                icon_bytes=validated_data["icon_bytes"],
                position=validated_data["position"],
                author=ctx.author,
                assignable_priority=assignable_priority
            )
            await ctx.send(embed=mLily.SimpleEmbed(f"Role **{name}** created at position **{validated_data['position']}**"))
            await LilyLogging.WriteLog(ctx, ctx.author.id, f"Role Named <@&{new_role.id}> has been created with priority {assignable_priority}")
        except discord.Forbidden:
            await ctx.send(embed=mLily.SimpleEmbed("Missing permissions to create or move the role."))
        except Exception as e:
            await ctx.send(embed=mLily.SimpleEmbed(f"Role creation failed: {e}"))

    @commands.hybrid_command(name="delete_role", description="deletes a role with config = LIMITED")
    async def delete_role(ctx: commands.Context,id: discord.Role):
        if ctx.author.id not in Config.staff_manager_ids + Config.owner_ids:
            await ctx.send("Permission Denied")
            return
        success = await rLily.DeleteRole(ctx, id)
        if success:
            await LilyLogging.WriteLog(ctx, ctx.author.id, f"Deleted a Role with id {id} ")

    '''

    # CHANNEL UTILITY

    class Channels(str, Enum):
        StockUpdate = "StockUpdate"
        WORL = "WORL"
        FruitValues = "FruitValues"
        Combo = "Combo"

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles)
    @commands.hybrid_command(name="assign_channel", description="Assign Particular feature of the bot limited to the specific channel. Ex-Stock Update")
    async def assign_channel(self, ctx, bot_feature: Channels, channel_to_assign: discord.TextChannel):
        if bot_feature == self.Channels.StockUpdate:
            await Config.save_channel(ctx, "stock_update_channel_id", channel_to_assign.id)
            await ctx.send(f"Stock Update receives in <#{channel_to_assign.id}>")
        elif bot_feature == self.Channels.WORL:
            await Config.save_channel(ctx, "w_or_l_channel_id", channel_to_assign.id)
            await ctx.send(f"Win or Loss is Caliberated in <#{channel_to_assign.id}>")
        elif bot_feature == self.Channels.FruitValues:
            await Config.save_channel(ctx, "fruit_values_channel_id", channel_to_assign.id)
            await ctx.send(f"Fruit Values is Caliberated in <#{channel_to_assign.id}>")
        elif bot_feature == self.Channels.Combo:
            await Config.save_channel(ctx, "combo_channel_id", channel_to_assign.id)
            await ctx.send(f"Combo Channel Set To <#{channel_to_assign.id}>")
        else:
            await ctx.send(f"Unable to Assign the Channel")


    # MESSAGING UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
    @commands.hybrid_command(name='direct_message', description='direct messages using the bot')
    async def dm(ctx, user: discord.User, *, message: str):
        try:
            embed = discord.Embed(title=f"Message from {ctx.author.name}",description=f"{message}",
                        colour=0xf500b4)
            await user.send(embed=embed)
            await ctx.send("Sent Successfully")
        except discord.Forbidden:
            await ctx.send(f"Exception Type Forbidden {e}")
        except Exception as e:
            await ctx.send(f"Exception {e}")



    # SLASH COMMAND SYNCING UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles)
    @commands.command()
    async def sync(self, ctx:commands.Context):
        guild = ctx.guild
        synced = await self.tree.sync(guild=guild)
        await ctx.send(f"Synced {len(synced)} slash commands w.r.t the guild")


    # SERVER UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles)
    @commands.hybrid_command(name='list', description='lists the total number of users in the server')
    async def ServerList(self, ctx: commands.Context):
        if not ctx.author.id in Config.ids + Config.owner_ids:
            return
        if not self.bot.guilds:
            await ctx.send("No Servers Fetched")
            return

        guilds = self.bot.guilds
        chunk_size = 10

        for i in range(0, len(guilds), chunk_size):
            chunk = guilds[i:i+chunk_size]
            description = ""
            for guild in chunk:
                description += f"**{guild.name}** — Owner: {guild.owner} (USER ID: {guild.owner.id})\n"
            
            embed = discord.Embed(
                title=f"Server List (Page {i//chunk_size + 1}/{(len(guilds) + chunk_size - 1)//chunk_size})",
                description=description,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            asyncio.sleep(0.5)


async def setup(bot):
    await bot.add_cog(LilyUtility(bot))