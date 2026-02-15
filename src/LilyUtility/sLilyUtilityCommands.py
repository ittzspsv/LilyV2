from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator
import LilyLogging.sLilyLogging as LilyLogging
import LilyLeveling.sLilyLevelingCore as LLC
import LilyModeration.sLilyModeration as mLily
import re

import Misc.sLilyComponentV2 as CV2
import Config.sValueConfig as ValueConfig
import Config.sValueConfig as VC
import LilyManagement.sLilyStaffManagement as LSM
import Misc.sLilyEmbed as LE
import ui.sGreetingGenerator as GG

import discord
from discord.ext import commands

import Config.sBotDetails as Config
from enum import Enum

import asyncio



class RoleButton(discord.ui.Button):
    def __init__(self, label: str, role_id: int):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        member = interaction.user

        if not role:
            await interaction.response.send_message("❌ Role not found!", ephemeral=True)
            return

        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"🧹 Removed **{role.name}** role!", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ Added **{role.name}** role!", ephemeral=True)


class LilyUtility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    # CHANNEL UTILITY

    class Channels(str, Enum):
        WORL = "WORL"
        FruitValues = "FruitValues"
        Combo = "Combo"

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(("Developer",)),allow_per_server_owners=True)
    @commands.hybrid_command(name="assign_channel",description="Assign Particular feature of the bot limited to the specific channel.")
    async def assign_channel(self,ctx,bot_feature: Channels,channel_to_assign: discord.TextChannel):
        cursor = await ValueConfig.cdb.execute(
            "SELECT channel_config_id FROM ConfigData WHERE guild_id = ?",
            (ctx.guild.id,)
        )
        row = await cursor.fetchone()

        if not row:
            return await ctx.send("ConfigData row missing for this server.")

        channel_config_id = row[0]

        if channel_config_id is None:
            cursor = await ValueConfig.cdb.execute(
                "INSERT INTO ConfigChannels DEFAULT VALUES"
            )
            channel_config_id = cursor.lastrowid

            await ValueConfig.cdb.execute(
                """
                UPDATE ConfigData
                SET channel_config_id = ?
                WHERE guild_id = ?
                """,
                (channel_config_id, ctx.guild.id)
            )

        if bot_feature == self.Channels.WORL:
            column = "bf_win_loss_channel_id"
            msg = f"Win or Loss is calibrated in <#{channel_to_assign.id}>"

        elif bot_feature == self.Channels.FruitValues:
            column = "bf_fruit_values_channel_id"
            msg = f"Fruit Values calibrated in <#{channel_to_assign.id}>"

        elif bot_feature == self.Channels.Combo:
            column = "bf_combo_channel_id"
            msg = f"Combo channel set to <#{channel_to_assign.id}>"

        else:
            return await ctx.send("Invalid feature.")

        await ValueConfig.cdb.execute(
            f"""
            UPDATE ConfigChannels
            SET {column} = ?
            WHERE channel_config_id = ?
            """,
            (channel_to_assign.id, channel_config_id)
        )

        await ValueConfig.cdb.commit()
        await ctx.send(msg)

    # MESSAGING UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.hybrid_command(name='direct_message', description='direct messages using the bot')
    async def dm(self, ctx: commands.Context, user: discord.User, message: str, type: int=0):
        await ctx.defer()
        try:
            if type == 0:
                embed = discord.Embed(
                    title=f"Message From {ctx.guild.name}",
                    description=f"- {message}",
                    colour=0xffffff
                )

                embed.set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.display_avatar.url
                )

                await user.send(embed=embed)
                await ctx.send(embed=mLily.SimpleEmbed("Sent Successfully"))
            else:
                await user.send(content=message)
                await LilyLogging.WriteLog(ctx, ctx.author.id, f"Sent Message to {user.id} DM : {message}")
                await ctx.send(embed=mLily.SimpleEmbed("Sent Successfully"))

        except discord.Forbidden:
            await ctx.send(embed=mLily.SimpleEmbed("I can't DM this user. They may have DMs disabled.", 'cross'))

        except Exception as e:
            print(f"Exception [USER DM] {e}")
            await ctx.send(embed=mLily.SimpleEmbed("Failed to send Direct Message", 'cross'))

    # SLASH COMMAND SYNCING UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.command()
    async def sync(self, ctx:commands.Context):
        guild = ctx.guild
        synced = await self.tree.sync(guild=guild)
        await ctx.send(f"Synced {len(synced)} slash commands w.r.t the guild")

    # SERVER UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='list', description='lists the total number of users in the server')
    async def ServerList(self, ctx: commands.Context):
        try:
            guilds = self.bot.guilds
            chunk_size = 10

            for i in range(0, len(guilds), chunk_size):
                chunk = guilds[i:i+chunk_size]
                description = ""
                for guild in chunk:
                    description += f"**{guild.name} - {guild.member_count}**\n"
                
                embed = discord.Embed(
                    title=f"Server List (Page {i//chunk_size + 1}/{(len(guilds) + chunk_size - 1)//chunk_size})",
                    description=description,
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Exception [SERVER LIST] {e}")

    #UID UTILITY
    @commands.hybrid_command(name='id', description='returns the id of a specific usertype')
    async def id(self, ctx:commands.Context, user:discord.Member=None):
        if user== None:
            await ctx.send(ctx.author.id)
        else:
            await ctx.send(user.id)


    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name='purge',description='Purges Message')
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        if amount <= 0:
            await ctx.send("You must delete at least 1 message.")
            return

        def check(msg):
            return True if member is None else msg.author == member

        try:
            deleted = await ctx.channel.purge(limit=amount, check=check, bulk=True)
            await ctx.send(f"✅ Deleted {len(deleted)} message(s).", delete_after=5)
        except discord.Forbidden:
            await ctx.send("I do not have permission to delete messages.")
        except discord.HTTPException as e:
            await ctx.send(f"Exception: {e}")

    '''
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='reaction_roles',description='Adds or updates reaction roles.  Follows role hierrachy of user who is triggering this')
    async def reactionroles(self, ctx: commands.Context, roles: str, title: str,channel_to_send: discord.TextChannel):
        try:
            role_map = json.loads(roles)
        except Exception:
            await ctx.reply("Invalid JSON format. Use `{ \"Button Name\": RoleID }`")
            return

        view = discord.ui.View(timeout=None)

        for button_label, role_id in role_map.items():
            role = ctx.guild.get_role(int(role_id))
            if not role:
                await ctx.send(f"Role ID {role_id} not found.")
                continue

            if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send(f"You cannot assign {role.name} because it is higher or equal to your top role.")
                continue

            if role >= ctx.guild.me.top_role:
                await ctx.send(f"I can't manage the role {role.name} because it's higher than my top role.")
                continue

            view.add_item(RoleButton(label=button_label, role_id=role.id))

        if len(view.children) == 0:
            await ctx.reply("No valid roles to add buttons for. Command cancelled.")
            return

        embed = discord.Embed(
            title=title,
            description="Click the buttons below to toggle your roles!",
            color=discord.Color.blurple()
        )

        sent_message = await channel_to_send.send(embed=embed, view=view)
        await ctx.reply(f"Reaction role message sent in {channel_to_send.mention}!")
    '''

    '''
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='telecast_message',description='Sends Message to All webhooks linked')
    async def telecast(self, ctx: commands.Context, msg_config: str):
        try:
            data = json.loads(msg_config)

            content, embed = LE.ParseAdvancedEmbed(data)
            cursor = await VC.cdb.execute(
                "SELECT pvb_stock_webhook FROM PVB_StockHandler WHERE guild_id != ?", (ctx.guild.id,)
            )
            row_1 = await cursor.fetchall()

            cursor = await VC.cdb.execute(
                "SELECT bf_stock_webhook FROM BF_StockHandler WHERE guild_id != ?", (ctx.guild.id,)
            )
            row_2 = await cursor.fetchall()

            row_merged = row_1 + row_2
            if not row_merged:
                await ctx.send("No webhooks found to telecast the message.")
                return

            sent_count = 0
            async with aiohttp.ClientSession() as session:
                for webhook_row in row_merged:
                    webhook_url = webhook_row[0]
                    if not webhook_url:
                        continue
                    try:
                        webhook = discord.Webhook.from_url(webhook_url, session=session)
                        await webhook.send(content=content, embeds=embed)
                        sent_count += 1
                    except Exception as wh_err:
                        print(f"Failed to send to webhook {webhook_url}: {wh_err}")

            await ctx.send(f"Telecast completed. Message sent to {sent_count} webhooks.")

        except Exception as e:
            await ctx.send(f"An error occurred while telecasting: {e}")
    '''
            
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='latency',description='sends the latency of the bot')
    async def latency(self, ctx: commands.Context):
        await ctx.send(f'`{round(self.bot.latency * 1000, 2)}ms`')

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager', 'Giveaway Manager', 'Administrator','Head Administrator')))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='role',description='assign role or removes a specified role from the user')
    async def role(self, ctx: commands.Context, user: discord.Member, *, role_input: str):
        if (
            ctx.author != ctx.guild.owner 
            and ctx.author != user
            and ctx.author.top_role <= user.top_role
        ):
            return await ctx.send("You cannot modify someone with equal or higher top role.")

        role = None

        mention_match = re.match(r'<@&(\d+)>', role_input)
        if mention_match:
            role = ctx.guild.get_role(int(mention_match.group(1)))

        if role is None and role_input.isdigit():
            role = ctx.guild.get_role(int(role_input))

        if role is None:
            role_name = role_input.replace('*', ' ').lower()
            role = discord.utils.find(lambda r: r.name.lower() == role_name, ctx.guild.roles)

        if role is None:
            return await ctx.send(f"Role `{role_input}` not found on this server.")

        if role > ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("You cannot assign a role that is higher than your top role.")

        if ctx.guild.me.top_role <= role:
            return await ctx.send("I cannot manage that role because it is above my top role.")

        role_allotment = await LSM.GetAssignableRoles(ctx.author.roles)
        if role_allotment:
            mode, role_ids = next(iter(role_allotment.items()))
            if mode == 'all':
                if role in user.roles:
                    await user.remove_roles(role, reason=f"Role removed by {ctx.author}")
                    return await ctx.send(f"Removed role **{role.name}** from **{user.name}**.")
                else:
                    await user.add_roles(role, reason=f"Role given by {ctx.author}")
                    return await ctx.send(f"Added role **{role.name}** to **{user.name}**.")
            elif mode == 'specified':
                if role.id in role_ids:
                    if role in user.roles:
                        await user.remove_roles(role, reason=f"Role removed by {ctx.author}")
                        return await ctx.send(f"Removed role **{role.name}** from **{user.name}**.")
                    else:
                        await user.add_roles(role, reason=f"Role given by {ctx.author}")
                        return await ctx.send(f"Added role **{role.name}** to **{user.name}**.")
                else:
                    return await ctx.send(f"You are not allowed to assign this role.")
            elif mode == 'except':
                if role.id not in role_ids:
                    if role in user.roles:
                        await user.remove_roles(role, reason=f"Role removed by {ctx.author}")
                        return await ctx.send(f"Removed role **{role.name}** from **{user.name}**.")
                    else:
                        await user.add_roles(role, reason=f"Role given by {ctx.author}")
                        return await ctx.send(f"Added role **{role.name}** to **{user.name}**.")
                else:
                    return await ctx.send(f"You are not allowed to assign this role.")
        else:
            return await ctx.send(f"Column encountered a NULL parameter which is not expected")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager', 'Manager')))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='setup_logging',description='assign logs channel')
    async def setup_logging(self, ctx: commands.Context, channel: discord.TextChannel):
        await VC.cdb.execute(
            "INSERT OR IGNORE INTO ConfigData (guild_id) VALUES (?)",
            (ctx.guild.id,)
        )
        
        await VC.cdb.execute(
            "UPDATE ConfigData SET logs_channel = ? WHERE guild_id = ?",
            (channel.id, ctx.guild.id)
        )
        await VC.cdb.commit()
        
        await ctx.send(embed=mLily.SimpleEmbed("Successfully Assigned Log Channel!"))

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager', 'Manager')))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='setup_welcome',description='setup welcome messages channel')
    async def setup_welcome(self, ctx: commands.Context, channel: discord.TextChannel):
        await VC.cdb.execute(
            "INSERT OR IGNORE INTO ConfigData (guild_id) VALUES (?)",
            (ctx.guild.id,)
        )
        
        await VC.cdb.execute(
            "UPDATE ConfigData SET welcome_channel = ? WHERE guild_id = ?",
            (channel.id, ctx.guild.id)
        )
        await VC.cdb.commit()
        
        await ctx.send(embed=mLily.SimpleEmbed("Successfully Assigned Welcome Channel!"))

    @commands.hybrid_command(name='welcome_demo', description='Welcome Demo')
    async def welcome_demo(self, ctx: commands.Context, member: discord.Member):
        try:
            await ctx.defer()
            buffer = await GG.GenerateWelcome(member)
            view = CV2.GreetingComponent(member)
            file = discord.File(fp=buffer, filename="welcome.png")
            await ctx.send(content=member.mention, view=view,file=file)
        except Exception as e:
            print(e)

    class Roles(str, Enum):
        Giveaways = "Giveaways"
        Events = "Events"
        Null = "null"

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Giveaway Manager', 'Developer', 'Event Manager')))
    @commands.hybrid_command(name='ping_role', description='Ping a predefined role')
    @commands.cooldown(rate=1, per=600, type=commands.BucketType.user)
    async def ping_role(self, ctx: commands.Context, role: Roles, channel: discord.TextChannel):
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
        else:
            await ctx.defer()

        if role == self.Roles.Giveaways:
            role_obj = discord.utils.get(ctx.guild.roles, name="Giveaways")
        elif role == self.Roles.Events:
            role_obj = discord.utils.get(ctx.guild.roles, name="Events")
        else:
            role_obj = None

        if role_obj is None:
            if ctx.interaction:
                await ctx.interaction.followup.send("Role not found.", ephemeral=True)
            else:
                await ctx.reply("Role not found.")
            return

        await channel.send(role_obj.mention)

        if ctx.interaction:
            await ctx.interaction.followup.send("Sent Successfully!", ephemeral=True)
        else:
            await ctx.reply("Sent Successfully!")
        embed = discord.Embed(
            title="ROLE PING ACTION",
            description=f"{ctx.author.mention} pinged {role_obj.mention} in {channel.mention}",
            colour=0xffffff
        )

        await LilyLogging.PostLog(ctx, embed, "Role Ping Action")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager')))
    @commands.hybrid_command(name='set_role_icon', description='Sets a role icon')
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def role_icon(self, ctx: commands.Context, role: discord.Role, icon: discord.Attachment):
        await ctx.defer()
        if icon.content_type not in ("image/png", "image/jpeg"):
            return await ctx.reply("Role icons must be a **PNG or JPG** image.",ephemeral=True)
        try:
            icon_bytes = await icon.read()

            await role.edit(
                display_icon=icon_bytes,
                reason=f"Role icon updated by {ctx.author}"
            )
            await ctx.reply(
                f"Successfully updated icon for **{role.name}**."
            )
        except Exception as e:
            await ctx.reply("An Unknown Error Occured.", ephemeral=True)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('StrictEnforcing')))
    @commands.hybrid_command(name='edit_profile', description='Sets the profile of the bot per server')
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def edit_profile(self, ctx: commands.Context, bio: str, avatar: discord.Attachment, banner: discord.Attachment):
        await ctx.defer()
        try:
            guild = ctx.guild
            bot_member = guild.me
            avatar_bytes = await avatar.read()
            banner_bytes = await banner.read()
            await bot_member.edit(avatar=avatar_bytes,banner=banner_bytes,bio=bio)

            await ctx.send("Profile Edit Success, Will be updated within few mins.")
        except Exception as e:
            print(f"Exception [edit_profile] {e}")
            await ctx.send("An Unknown error Occured")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff')))
    @commands.hybrid_command(name='check_reaction', description='Checks if an user has reacted to an message')
    async def check_reaction(self, ctx: commands.Context, member: discord.Member, message_id: int, emoji_str: str):
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("Message not found!")

        reacted = False
        for reaction in message.reactions:
            if str(reaction.emoji) == emoji_str:
                async for user in reaction.users():
                    if user.id == member.id:
                        reacted = True
                        break
                if reacted:
                    break

        if reacted:
            await ctx.send(embed=mLily.SimpleEmbed(f"{member.mention} has reacted"))
        else:
            await ctx.send(embed=mLily.SimpleEmbed(f"{member.mention} has not reacted", 'cross'))

async def setup(bot):
    await bot.add_cog(LilyUtility(bot))