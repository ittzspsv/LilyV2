from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator
import LilyLogging.sLilyLogging as LilyLogging
import re
import json

import Misc.sLilyComponentV2 as CV2
import Config.sValueConfig as ValueConfig
import Config.sValueConfig as VC
import LilyManagement.sLilyStaffManagement as LSM
from Misc.sLilyEmbed import simple_embed
import ui.sGreetingGenerator as GG

from Misc.sLIlyGlobalComponents import CommandInfo as CI
from LilyUtility.sLilyUtilityComponents import ProfileInformationComponent
import LilyBloxFruits.sLilyBloxFruitsCache as BFC

import LilyUtility.sLilyUtility as Util
import discord
from discord.ext import commands

import io
import secrets
from enum import Enum

import random

import random
from collections import Counter

from Misc.sLilyEmbed import simple_embed

import asyncio


class LilyUtility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.afk_cache: dict = {"automod_rule_id": None, "currently_afk": []}
    # CHANNEL UTILITY

    class Channels(str, Enum):
        WORL = "WORL"
        FruitValues = "FruitValues"
        Combo = "Combo"

    def initialize_cache(self):
        with open("storage/configs/AutomodConfig.json", "r") as file:
            self.afk_cache = json.load(file)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.author.id in self.afk_cache.get("currently_afk", []):
            self.afk_cache["currently_afk"].remove(message.author.id)

            automod_rule_id = self.afk_cache.get("automod_rule_id")
            mention_keyword = f"<@{message.author.id}>"

            if automod_rule_id:
                try:
                    lily_automod = await message.guild.fetch_automod_rule(automod_rule_id)
                    automod_keywords = lily_automod.trigger.keyword_filter
                    if mention_keyword in automod_keywords:
                        updated_keywords = [kw for kw in automod_keywords if kw != mention_keyword]
                        new_trigger = discord.AutoModTrigger(keyword_filter=updated_keywords)
                        await lily_automod.edit(trigger=new_trigger)
                except discord.NotFound:
                    pass

            with open("storage/configs/AutomodConfig.json", "w") as file:
                json.dump(self.afk_cache, file, indent=4)

            await message.reply(embed=simple_embed(f"{message.author.mention} is no longer AFK. Welcome back!"))

    @commands.Cog.listener()
    async def on_ready(self):
        self.initialize_cache()

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
        await ValueConfig.initialize_cache()
        await ctx.send(msg)

    '''
    # MESSAGING UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.hybrid_command(name='direct_message', description='Direct Messages to an user using the bot')
    async def dm(self, ctx: commands.Context, user: discord.User, message: str, type: int=0):
        if user is None:
            await ctx.reply(view=CI(ctx, "Direct User", ["/direct_message user: message: type: ", f"/direct_message user: {ctx.me.mention} message: Hello! type: 1"]))
            return
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
                await ctx.send(embed=simple_embed("Sent Successfully"))
            else:
                await user.send(content=message)
                await LilyLogging.WriteLog(ctx, ctx.author.id, f"Sent Message to {user.id} DM : {message}")
                await ctx.send(embed=simple_embed("Sent Successfully"))

        except discord.Forbidden:
            await ctx.send(embed=simple_embed("I can't DM this user. They may have DMs disabled.", 'cross'))

        except Exception as e:
            print(f"Exception [USER DM] {e}")
            await ctx.send(embed=simple_embed("Failed to send Direct Message", 'cross'))

    '''        

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
        '''
        if(isinstance(ctx.channel, discord.Threads)):
            cursor = await LilyLogging.mdb.execute("SELECT ticket_values FROM tickets WHERE ticket_id = ?", (ctx.channel.id,))
            row = await cursor.fetchone()

            if row:
                pass
            else:
                if user== None:
                    await ctx.send(ctx.author.id)
                else:
                    await ctx.send(user.id)
        else:'''
        if user== None:
            await ctx.send(ctx.author.id)
        else:
            await ctx.send(user.id)

    @commands.hybrid_command(name='info', description='returns the information of the user globally')
    async def info(self, ctx: commands.Context, user: str = None):
        if user is None:
            target = ctx.author
        else:
            try:
                target = await commands.UserConverter().convert(ctx, user)
            except commands.BadArgument:
                await ctx.reply(embed=simple_embed("User not found", 'cross'))
                return

        user = await self.bot.fetch_user(target.id)

        view = ProfileInformationComponent(user)
        await ctx.reply(view=view)
        

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)), allow_per_server_owners=True)
    @commands.hybrid_command(name='purge',description='Purge Message with specified amount')
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def purge(self, ctx, amount: int=0, member: discord.Member = None):
        if amount <= 0:
            await ctx.reply(view=CI(ctx, "Purge", ["purge n", "purge 30"]))
            return

        def check(msg):
            return True if member is None else msg.author == member

        try:
            deleted = await ctx.channel.purge(limit=amount, check=check, bulk=True)
            await ctx.send(embed=simple_embed(f"Deleted {len(deleted)} message(s)."), delete_after=5)
        except discord.Forbidden:
            await ctx.send(embed=simple_embed("I do not have permission to delete messages.", 'cross'))
        except discord.HTTPException as e:
            await ctx.send(embed=simple_embed("An Unknown error occured", 'cross'))

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='latency',description='sends the latency of the bot')
    async def latency(self, ctx: commands.Context):
        await ctx.send(f'`{round(self.bot.latency * 1000, 2)}ms`')

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager', 'Giveaway Administrator', 'Administrator','Head Administrator', 'Giveaway Host', 'Event Administrator')))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='role',description='Assigns/Removes a specified role from the user (not case-sensitive)')
    async def role(self, ctx: commands.Context, user: discord.Member=None, *, role_input: str=None):
        if user is None and role_input is None:
            await ctx.reply(view=CI(ctx, "Role", ["role user role", f"role {ctx.me.mention} Moderator", f"role {ctx.me.mention} 1324893524184793130"]))
            return

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
        
        await ctx.send(embed=simple_embed("Successfully Assigned Log Channel!"))

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
        
        await ctx.send(embed=simple_embed("Successfully Assigned Welcome Channel!"))

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

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager')))
    @commands.hybrid_command(name='set_role_icon', description='Sets a role icon for a specific role')
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def role_icon(self, ctx: commands.Context, role: discord.Role=None, icon: discord.Attachment=None):        
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
    async def check_reaction(self, ctx: commands.Context, member: discord.Member=None, message_id: int=None, emoji_str: str=None):
        if member is None or message_id is None or emoji_str is None:
            await ctx.reply(view=CI(ctx, "Check Reaction", ["check_reaction user message_id emoji", f"check_reaction {ctx.me.mention} 1488478394361446470 😊"]))
            return
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
            await ctx.send(embed=simple_embed(f"{member.mention} has reacted"))
        else:
            await ctx.send(embed=simple_embed(f"{member.mention} has not reacted", 'cross'))
        
    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff',)))
    @commands.hybrid_command(name="afk", description="Puts the user to afk mode")
    async def afk(self, ctx: commands.Context, * ,message: str="AFK"):
        await ctx.defer()

        if ctx.author.id in self.afk_cache.get("currently_afk"):
            await ctx.reply(embed=simple_embed("You are already in afk", 'cross'))
            return 

        mention_keyword: str = f"<@{ctx.author.id}>"
        automod_rule_id = self.afk_cache.get("automod_rule_id")

        if automod_rule_id:
            try:
                lily_automod = await ctx.guild.fetch_automod_rule(automod_rule_id)
                automod_keywords = lily_automod.trigger.keyword_filter
                if mention_keyword not in automod_keywords:
                    updated_keywords = automod_keywords + [mention_keyword]
                    new_trigger = discord.AutoModTrigger(keyword_filter=updated_keywords)
                    await lily_automod.edit(trigger=new_trigger)
            except discord.NotFound:
                automod_rule_id = None

        if not automod_rule_id:
            lily_automod = await ctx.guild.create_automod_rule(
                name="LilyAutomod",
                event_type=discord.AutoModRuleEventType.message_send,
                trigger=discord.AutoModTrigger(keyword_filter=[mention_keyword]),
                enabled=True,
                actions=[discord.AutoModRuleAction(custom_message="Shh… this user is away for a bit. Let's not disturb them!")]
            )
            automod_rule_id = lily_automod.id

        self.afk_cache["automod_rule_id"] = automod_rule_id
        if ctx.author.id not in self.afk_cache["currently_afk"]:
            self.afk_cache["currently_afk"].append(ctx.author.id)

        with open("storage/configs/AutomodConfig.json", "w") as file:
            json.dump(self.afk_cache, file, indent=4)

        await ctx.reply(embed=simple_embed(f"{ctx.author.mention} is now AFK : {message}"))


    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff Manager', 'Developer', 'Senior Administrator', 'Head Administrator')))
    @commands.hybrid_command(name="add_keyword_automod", description="Puts the user to afk mode")
    async def add_keyword_automod(self, ctx: commands.Context, *, keyword: str):
        automod_rule_id = self.afk_cache.get("automod_rule_id")
        if automod_rule_id:
            try:
                lily_automod = await ctx.guild.fetch_automod_rule(automod_rule_id)
                automod_keywords = lily_automod.trigger.keyword_filter
                if keyword not in automod_keywords:
                    updated_keywords = automod_keywords + [keyword]
                    new_trigger = discord.AutoModTrigger(keyword_filter=updated_keywords)
                    await lily_automod.edit(trigger=new_trigger, reason=f"Automod keyword added by {ctx.author}")
                    await ctx.reply(embed=simple_embed(f"Successfully added `{keyword}` to Automod"))
            except Exception as e:
                await ctx.reply(embed=simple_embed(f"Failed to added `{keyword}` to Automod"))
                print(f"Exception [add_keyword_automod] {e}")

    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff Manager', 'Developer', 'Senior Administrator', 'Head Administrator')))
    @commands.hybrid_command(name="list_keyword_automod", description="Lists all automod keywords")
    async def list_keyword_automod(self, ctx: commands.Context):
        automod_rule_id = self.afk_cache.get("automod_rule_id")

        if not automod_rule_id:
            return await ctx.reply(embed=simple_embed("Automod rule not configured"))

        try:
            lily_automod = await ctx.guild.fetch_automod_rule(automod_rule_id)
            automod_keywords = lily_automod.trigger.keyword_filter

            if not automod_keywords:
                return await ctx.reply(embed=simple_embed("No keywords found in Automod"))

            keywords_text = "\n".join([f"- `{kw}`" for kw in automod_keywords])
            await ctx.reply(f"**Automod Keywords:**\n{keywords_text}")

        except Exception as e:
            await ctx.reply(embed=simple_embed("Failed to fetch Automod keywords"))
            print(f"Exception [list_keyword_automod] {e}")

    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff Manager', 'Developer', 'Senior Administrator', 'Head Administrator')))
    @commands.hybrid_command(name="remove_keyword_automod", description="Removes a keyword from automod")
    async def remove_keyword_automod(self, ctx: commands.Context, *, keyword: str):
        automod_rule_id = self.afk_cache.get("automod_rule_id")

        if not automod_rule_id:
            return await ctx.reply(embed=simple_embed("Automod rule not configured"))

        try:
            lily_automod = await ctx.guild.fetch_automod_rule(automod_rule_id)
            automod_keywords = lily_automod.trigger.keyword_filter

            if keyword not in automod_keywords:
                return await ctx.reply(embed=simple_embed(f"`{keyword}` not found in Automod"))

            updated_keywords = [kw for kw in automod_keywords if kw != keyword]

            new_trigger = discord.AutoModTrigger(keyword_filter=updated_keywords)
            await lily_automod.edit(trigger=new_trigger, reason=f"Automod keyword removed by {ctx.author}")

            await ctx.reply(embed=simple_embed(f"Successfully removed `{keyword}` from Automod"))

        except Exception as e:
            await ctx.reply(embed=simple_embed(f"Failed to remove `{keyword}` from Automod"))
            print(f"Exception [remove_keyword_automod] {e}")


    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff Manager', 'Developer')))
    async def show_overrides_json(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel

        data = {}
        for target, overwrite in channel.overwrites.items():
            allow, deny = overwrite.pair()

            allow_perms = [perm for perm, value in allow if value]
            deny_perms = [perm for perm, value in deny if value]

            key = f"{target.id}"

            data[key] = {
                "name": getattr(target, "name", str(target)),
                "type": "role" if isinstance(target, discord.Role) else "member",
                "allow": allow_perms,
                "deny": deny_perms,
                "allow_value": allow.value,
                "deny_value": deny.value
            }

        json_str = json.dumps(data, indent=4)

        file = discord.File(
            fp=io.StringIO(json_str),
            filename=f"{channel.id}_overrides.json"
        )
        await ctx.send(file=file)
          
    @commands.hybrid_command(name="about", description="Know something about the bot")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def about(self, ctx: commands.Context):
        embed = discord.Embed(
            title="About Me!",
            description="## Name : Lily\n- No Idea about this name to be honest.",
            color=0xFFFFFF
        )

        embed.add_field(
            name="Developers",
            value="- Shree (Lead)\n- Texio\n- Lily.cs",
            inline=False
        )

        embed.add_field(
            name="Code Maintainer",
            value="- ~~--------~~ Shree.",
            inline=False
        )

        embed.add_field(
            name="Profile and Banner Information",
            value=(
                "- [Avatar](https://danganronpa.fandom.com/wiki/Chiaki_Nanami_(Danganronpa_2))\n"
                "- Character Source : Chaiki Nanami (Danganronpa 2 Goodbye Despair)\n"
                "- Banner Source : Please Insert Coin"
            ),
            inline=False
        )

        embed.add_field(
            name="Licensing Terms",
            value="- Open Source Free to Modify/Redistribute Licensing. (Incl. Credits)",
            inline=False
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LilyUtility(bot))