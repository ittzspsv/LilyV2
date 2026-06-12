import re
import json
import discord
import aiohttp
import asyncio
import time


from io import BytesIO
from src.core.utils.embeds.sLilyEmbed import simple_embed
from src.core.features.permissions.lily_permissions import permission
from src.core.utils.components.sLIlyGlobalComponents import CommandInfo as CI
from src.core.utils.embeds.sLilyEmbed import ParseAdvancedEmbed
from src.core.utils.types.types import ChannelEnum, CommandEnum, NotifiersEnum
from src.core.logging.lily_logging import LilyLoggingController
from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from src.core.utils.components.sLIlyGlobalComponents import RoleCustomizationModal
from src.core.visuals.cards.quote import make_quote_card
from discord.ext import commands
from discord import app_commands


class LilyUtility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        if message.guild is None:
            return

        if not isinstance(message.author, discord.Member):
            return
        
        """ This only works for peoples with staff roles.  Nothing else, so we need to make sure staffs won't abuse this """
        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        allowed_roles = bot_db.get_permission_roles(message.guild.id, "mute")

        author_role_ids = {role.id for role in message.author.roles}

        if not any(role_id in author_role_ids for role_id in allowed_roles):
            return
         
        if message.content.startswith(f"<@{self.bot.user.id}>") or message.content.startswith(f"<@!{self.bot.user.id}>"):
            if message.reference is None:
                return
            content = message.content.lower()
            if "quote" not in content:
                return
            
            message_ref_id = message.reference.message_id

            if message_ref_id is None:
                return
            
            replied_msg = await message.channel.fetch_message(message_ref_id)
            author: discord.Member | discord.User = replied_msg.author
            content = replied_msg.content

            """ Delete the original message if possible """
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            avatar_bytes = await author.display_avatar.read()
            
            image = await asyncio.to_thread(
                make_quote_card,
                image=avatar_bytes,
                quote=content,
                author=author.display_name,
                handle=f"@{author.name}"
            )

            buffer = BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)

            await message.channel.send(file=discord.File(buffer, filename="quote.png"))
    
    @commands.hybrid_group()
    async def set(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Utility Setters"))

    @commands.hybrid_group()
    async def configure(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Utility Configurators"))

    @commands.hybrid_group()
    async def customize(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Utility Customizations"))

    @commands.hybrid_group()
    async def remove(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=simple_embed("Lily Utility Removers"))


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
                await ctx.reply(embed=simple_embed("Sent Successfully"))
            else:
                await user.send(content=message)
                await LilyLogging.WriteLog(ctx, ctx.author.id, f"Sent Message to {user.id} DM : {message}")
                await ctx.reply(embed=simple_embed("Sent Successfully"))

        except discord.Forbidden:
            await ctx.reply(embed=simple_embed("I can't DM this user. They may have DMs disabled.", 'cross'))

        except Exception as e:
            print(f"Exception [USER DM] {e}")
            await ctx.reply(embed=simple_embed("Failed to send Direct Message", 'cross'))

    '''        

    # SERVER UTILITY
    @commands.hybrid_command(name='list', description='lists the total number of users in the server')
    @permission(command_name="list", restrict=True)
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
                await ctx.reply(embed=embed)
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Exception [SERVER LIST] {e}")

    #UID UTILITY
    @commands.hybrid_command(name='id', description='returns the id of a specific usertype')
    async def id(self, ctx:commands.Context, user:discord.Member=None):
        if user== None:
            await ctx.reply(ctx.author.id)
        else:
            await ctx.reply(content=f'{user.id}')
        
    @commands.hybrid_command(name='purge',description='Purge Message with specified amount')
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @permission(command_name="purge")
    async def purge(self, ctx, amount: int=0, member: discord.Member = None):
        if amount > 1000:
            await ctx.reply(embed=simple_embed("You cannot purge more than 1000 messages!", 'cross'))
            return

        if amount <= 0:
            await ctx.reply(view=CI(ctx, "Purge", ["purge n", "purge 30"]))
            return

        def check(msg):
            return True if member is None else msg.author == member

        try:
            deleted = await ctx.channel.purge(limit=amount, check=check, bulk=True)
            await ctx.reply(embed=simple_embed(f"Deleted {len(deleted)} message(s)."), delete_after=5)
        except discord.Forbidden:
            await ctx.reply(embed=simple_embed("I do not have permission to delete messages.", 'cross'))
        except discord.HTTPException as e:
            await ctx.reply(embed=simple_embed("An Unknown error occured", 'cross'))

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='ping',description='sends the latency of the bot')
    async def ping(self, ctx: commands.Context):
        ws_latency = round(self.bot.latency * 1000, 2)

        start = time.perf_counter()
        msg = await ctx.reply("Evaluating...")
        roundtrip = round((time.perf_counter() - start) * 1000, 2)

        await msg.edit(
            content=(
                f"WebSocket Latency: `{ws_latency}ms`\n"
                f"Roundtrip: `{roundtrip}ms`"
            )
        )

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='role',description='Assigns/Removes a specified role from the user (not case-sensitive)')
    @permission(command_name="role")
    async def role(self, ctx: commands.Context, user: discord.Member=None, *, role_input: str=None):
        if ctx.guild is None or isinstance(ctx.author, discord.User):
            await ctx.reply(embed=simple_embed("You can only use this command inside an guild"))
            return
        if user is None and role_input is None:
            await ctx.reply(view=CI(ctx, "Role", ["role user role", f"role {ctx.me.mention} Moderator", f"role {ctx.me.mention} 1324893524184793130"]))
            return

        if (
            ctx.author != ctx.guild.owner 
            and ctx.author != user
            and ctx.author.top_role <= user.top_role
        ):
            return await ctx.reply(embed=simple_embed("You cannot modify someone with equal or higher top role.", 'cross'))

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
            return await ctx.reply(embed=simple_embed(f"Role `{role_input}` not found on this server.", 'cross'))

        if role > ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.reply(embed=simple_embed("You cannot assign a role that is higher than your top role.", 'cross'))

        if ctx.guild.me.top_role <= role:
            return await ctx.reply(embed=simple_embed("I cannot manage that role because it is above my top role.", 'cross'))
        
        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        author_role_ids = [role.id for role in ctx.author.roles]
        try:
            mode = bot_db.get_role_assignment_scope(ctx.guild.id, author_role_ids)
            role_ids = bot_db.get_role_assignment_roles(ctx.guild.id, author_role_ids)

            if mode:
                if mode == 'none':
                    return await ctx.reply(embed=simple_embed(f'You are not allowed for role assignment', 'cross'))

                if mode == 'all':
                    if role in user.roles:
                        await user.remove_roles(role, reason=f"Role removed by {ctx.author}")
                        return await ctx.reply(embed=simple_embed(f"Removed role **{role.name}** from **{user.name}**."))
                    else:
                        await user.add_roles(role, reason=f"Role given by {ctx.author}")
                        return await ctx.reply(embed=simple_embed(f"Added role **{role.name}** to **{user.name}**."))
                elif mode == 'specific':
                    if role.id in role_ids:
                        if role in user.roles:
                            await user.remove_roles(role, reason=f"Role removed by {ctx.author}")
                            return await ctx.reply(embed=simple_embed(f"Removed role **{role.name}** from **{user.name}**."))
                        else:
                            await user.add_roles(role, reason=f"Role given by {ctx.author}")
                            return await ctx.reply(embed=simple_embed(f"Added role **{role.name}** to **{user.name}**."))
                    else:
                        return await ctx.reply(embed=simple_embed(f"You are not allowed for role assignment", 'cross'))
                elif mode == 'except':
                    if role.id not in role_ids:
                        if role in user.roles:
                            await user.remove_roles(role, reason=f"Role removed by {ctx.author}")
                            return await ctx.reply(embed=simple_embed(f"Removed role **{role.name}** from **{user.name}**."))
                        else:
                            await user.add_roles(role, reason=f"Role given by {ctx.author}")
                            return await ctx.reply(embed=simple_embed(f"Added role **{role.name}** to **{user.name}**."))
                    else:
                        return await ctx.reply(embed=simple_embed(f"You are not allowed to assign this role.", 'cross'))
            else:
                return await ctx.reply(embed=simple_embed(f"Column encountered a NULL parameter which is not expected", 'cross'))
        except Exception as e:
            print(e)


    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @customize.command(name="role", description="Customize your role")
    async def customize_role(
        self,
        ctx: commands.Context,
        role: discord.Role,
        name: str = None,
        primary_color: str = None,
        secondary_color: str = None,
        icon: discord.Attachment = None
    ):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("You need to use this command inside a guild"))

        if role >= ctx.guild.me.top_role:
            return await ctx.reply(embed=simple_embed("I can't edit a role that is above me", 'cross'))

        assert isinstance(ctx.author, discord.Member)

        await ctx.defer()

        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        valid_roles = await bot_db.get_role_mapping(ctx.author.id, ctx.guild.id)

        if role.id not in valid_roles:
            return await ctx.reply(embed=simple_embed("You don't have any roles mapped that you can customize", 'cross'))

        def parse_hex_color(hex_str: str) -> discord.Color:
            hex_str = hex_str.strip().lstrip('#')
            if len(hex_str) != 6:
                raise ValueError(f"Invalid hex color: '{hex_str}'")
            return discord.Color(int(hex_str, 16))

        parameters = {}

        if name is not None:
            parameters["name"] = name

        if icon is not None:
            parameters["display_icon"] = await icon.read()

        if primary_color is not None:
            try:
                parameters["color"] = parse_hex_color(primary_color)
            except ValueError:
                return await ctx.reply(embed=simple_embed("Invalid color format.", 'cross'))

        if secondary_color is not None:
            try:
                parameters["secondary_color"] = parse_hex_color(secondary_color)
            except ValueError:
                return await ctx.reply(embed=simple_embed("Invalid color format.", 'cross'))

        try:
            await role.edit(**parameters, reason=f"Role customized by {ctx.author}")
            await ctx.reply("Successfully updated role!")
        except discord.Forbidden:
            await ctx.reply(embed=simple_embed("I don't have permission to edit roles", 'cross'))
        except ValueError as e:
            await ctx.reply(embed=simple_embed(f"Invalid parameter value: {e}", 'cross'))
        except discord.HTTPException as e:
            await ctx.reply(embed=simple_embed(f"An Unknown error occured while editing a role", 'cross'))



    @permission(command_name="set_rolecustomize")
    @set.command(name="rolecustomize", description="Allows a person to customize a role without manage roles")
    async def set_role_customize(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("You need to use this command inside an guild"))

        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        await bot_db.add_role_mapping(
            member.id,
            ctx.guild.id,
            role.id
        )
        
        await ctx.reply(embed=simple_embed(f"Successfully added customizable entry for {member.mention} with {role.mention}"))
        await member.send(f"Hey, You can now customize {role.name} (dev_id: {role.id}) in {ctx.guild.name}.  Use `/customize role` to see what happens!")

    @permission(command_name="remove_rolecustomize")
    @remove.command(name="rolecustomize", description="Removes a person from customizing a role without manage roles")
    async def remove_role_customize(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if ctx.guild is None:
            return await ctx.reply(embed=simple_embed("You need to use this command inside an guild"))
        bot_db: BotGlobalsDatabaseAccess = self.bot.db
        await bot_db.remove_role_mapping(
            member.id,
            ctx.guild.id,
            role.id
        )

        await ctx.reply(embed=simple_embed(f"Successfully removed customizable entry for {role.mention} assigned to {member.mention}"))
        await member.send(f"Hey, You can no longer customize {role.name} (dev_id: {role.id}) in {ctx.guild.name}.")


    @customize.command(name='bot', description='Customize the bot for this server (visually)')
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @permission(command_name="edit_profile", restrict=True)
    async def edit_profile(self, ctx: commands.Context, bio: str, avatar: discord.Attachment, banner: discord.Attachment):
        await ctx.defer()
        try:
            guild = ctx.guild
            bot_member = guild.me
            avatar_bytes = await avatar.read()
            banner_bytes = await banner.read()
            await bot_member.edit(avatar=avatar_bytes,banner=banner_bytes,bio=bio)

            await ctx.reply("Profile Edit Success. Will be updated within few mins.")
        except Exception as e:
            print(f"Exception [edit_profile] {e}")
            await ctx.reply("An Unknown error Occured")

    """
    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @commands.hybrid_command(name="afk", description="Puts the user to afk mode")
    @permission(command_name="afk")
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
    """
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
            value="- Senior Shree.",
            inline=False
        )

        embed.add_field(
            name="Profile and Banner Information",
            value=(
                "- [Avatar (Modified)](https://x.com/marmalade_icons/status/1116802730536906755?s=20)\n"
                "- Character Source : Kaede Akamatsu (Danganronpa V3: Killing Harmony)\n"
                "- Banner Source : Custom Fan art"
            ),
            inline=False
        )

        embed.add_field(
            name="Licensing Terms",
            value="- Open Source Free to Modify/Redistribute Licensing. (Incl. Credits)",
            inline=False
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.reply(embed=embed)
    
    @commands.cooldown(rate=1, per=80, type=commands.BucketType.user)
    @commands.hybrid_command(name="embed_create", description="Creates an embed based on JSON config and sends it to a specific channel")
    @permission(command_name="create_embed", restrict=True)
    async def create_embed(self, ctx: commands.Context, channel_to_send: discord.TextChannel, * ,embed_json_config: str = "{}"):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("This command can only be executed inside an guild", 'cross'))
            return
        try:
            if embed_json_config.startswith("http://") or embed_json_config.startswith("https://"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(embed_json_config) as resp:
                            if resp.status != 200:
                                await ctx.reply("Failed to fetch data from the provided link.")
                                return
                            embed_json_config = await resp.text()
                except Exception as fetch_error:
                    await ctx.reply(f"Fetch Failure {str(fetch_error)}")
                    return

            
            try:
                json_data = json.loads(embed_json_config)
            except json.JSONDecodeError:
                await ctx.reply("Invalid JSON Format")
                return
            
            try:
                logs_controller: LilyLoggingController = self.bot.logging_controller
                content, embeds = ParseAdvancedEmbed(json_data)
                await channel_to_send.send(content=content, embeds=embeds)
                await ctx.reply(embed=simple_embed("Embed sent successfully."))
                await logs_controller.write_log(ctx, ctx.author.id, f"Has Sent an Embed to <#{channel_to_send.id}>")
            except Exception as embed_error:
                await ctx.reply(f"Parser Failure: {str(embed_error)}")

        except Exception as e:
            await ctx.reply(f"Unhandled Exception: {str(e)}")

    @permission(command_name="set_channel")
    @set.command(name="channel", description="Creates an embed based on JSON config and sends it to a specific channel")
    async def assign_channel(self, ctx: commands.Context, type: ChannelEnum, channel: discord.TextChannel):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("This command can only be used inside an guild", 'cross'))
            return

        db: BotGlobalsDatabaseAccess = self.bot.db
        await db.set_channel(ctx.guild.id, channel.id, type.value)

        await ctx.reply(embed=simple_embed(f"Successfully assigned `{type.value.title()}` for {channel.mention}"))


    @commands.cooldown(rate=1, per=20, type=commands.BucketType.user)
    @permission(command_name="set_notifiers")
    @set.command(name="notifiers", description="Creates a notifier (webhook) when an value updates")
    async def set_notifiers(self, ctx: commands.Context, type: NotifiersEnum, channel: discord.TextChannel=None, webhook_url: str=None):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("This command can only be used inside an guild", 'cross'))
            return
        
        db: BotGlobalsDatabaseAccess = self.bot.db
        if channel is not None:
            await ctx.defer()
            webhook = await channel.create_webhook(name="Lily Listeners")
            webhook_url = webhook.url
            await db.set_webhook(ctx.guild.id, type.value, webhook_url)
            await ctx.reply(embed=simple_embed(f"Successfully created a webhook to listen `{type.value}`"))
        else:
            await db.set_webhook(ctx.guild.id, type.value, webhook_url)
            await ctx.reply(embed=simple_embed(f"Successfully assigned a webhook to listen `{type.value}`"))


    async def command_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        commands = list(CommandEnum)

        filtered = [
            app_commands.Choice(name=cmd.value, value=cmd.value)
            for cmd in commands
            if current.lower() in cmd.value.lower()
        ]
        return filtered[:25]
    
    @permission(command_name="set_permission")
    @set.command(name="permission", description="Allocates permission to certain role for a command")
    @app_commands.autocomplete(command=command_autocomplete)
    async def set_permission(self, ctx: commands.Context, command: str, role: discord.Role):
        try:
            cmd_enum = CommandEnum(command)
        except ValueError:
            await ctx.reply(embed=simple_embed(f"`{command}` is not a valid command", 'cross'))
            return

        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("This command can only be used inside a guild", 'cross'))
            return

        db: BotGlobalsDatabaseAccess = self.bot.db
        await db.set_permission(ctx.guild.id, role.id, cmd_enum.value)

        await ctx.reply(embed=simple_embed(f"Successfully assigned `{cmd_enum.value.replace("_", " ").title()}` permission to {role.mention}"))

    @permission(command_name="remove_permission")
    @remove.command("permission", description="Removes a command permission from certain role for a command")
    @app_commands.autocomplete(command=command_autocomplete)
    async def remove_permission(self, ctx: commands.Context, command: str, role: discord.Role):
        try:
            cmd_enum = CommandEnum(command)
        except ValueError:
            await ctx.reply(embed=simple_embed(f"`{command}` is not a valid command", 'cross'))
            return
        
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("This command can only be used inside a guild", 'cross'))
            return
        
        db: BotGlobalsDatabaseAccess = self.bot.db
        await db.remove_permission(ctx.guild.id, role.id, cmd_enum.value)

        await ctx.reply(embed=simple_embed(f"Successfully removed `{cmd_enum.value.replace("_", " ").title()}` permission from {role.mention}"))

    @permission(command_name="permissions")
    @commands.hybrid_command(name="permissions", description="List out permissions that a role has")
    async def permissions(self, ctx: commands.Context, role: discord.Role):
        if ctx.guild is None:
            await ctx.reply(
                embed=simple_embed(
                    "This command can only be used inside a guild",
                    "cross"
                )
            )
            return

        db: BotGlobalsDatabaseAccess = self.bot.db
        permissions = db.get_permissions(ctx.guild.id, role.id)

        if not permissions:
            await ctx.reply(
                embed=simple_embed(
                    f"{role.mention} has no configured permissions.",
                    "cross"
                )
            )
            return

        await ctx.reply(
            embed=discord.Embed(title="Permissions", description=", ".join(permissions), color=16777215)
        )

    @permission(command_name="set_prefix")
    @set.command(name="prefix", description="Change prefix of the bot")
    async def set_prefix(self, ctx: commands.Context, prefix: str):
        if ctx.guild is None:
            await ctx.reply(embed=simple_embed("This command can only be used inside an guild", 'cross'))
            return
        
        db: BotGlobalsDatabaseAccess = self.bot.db
        await db.set_prefix(ctx.guild.id, prefix)

        await ctx.reply(embed=simple_embed(f"Successfully assigned **{prefix}** as prefix"))

    @permission(command_name="configure_role")
    @configure.command(name="role", description="Configure some attributes of the role")
    async def configure_role(self, ctx: commands.Context, role: discord.Role):
        if ctx.interaction is None:
            await ctx.reply(embed=simple_embed(
                "This command can only be used as a slash command."
            ,'cross'), delete_after=5)
            return
        interaction = ctx.interaction
        try:
            await interaction.response.send_modal(RoleCustomizationModal(role.id, self.bot.db))
        except Exception as e:
            print(e)

    @commands.command(name="nick", description="Set a nickname for a member")
    @permission(command_name="nick")
    async def set_nickname(self, ctx: commands.Context, member: discord.Member=None, *, name: str=None):
        if member is None and name is None:
            await ctx.reply(view=CI(ctx, "Nick", ["nick {user} {nickname}", f"nick {ctx.me.mention} Lilyy", f"nick lily Lilly"]))
            return

        try:
            await member.edit(
                nick=name,
                reason=f"Changed by {ctx.author}"
            )

            await ctx.reply(
                embed=simple_embed(
                    f"Successfully changed {member.mention}'s nickname to **{name}**."
                )
            )

        except discord.Forbidden:
            await ctx.reply(
                embed=simple_embed(
                    "I don't have permission to change that member's nickname.", 'cross'
                )
            )

        except discord.HTTPException as e:
            await ctx.reply(
                embed=simple_embed(
                    f"Failed to change nickname: {e}", 'cross'
                )
            )

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name="quote", description="Create a quote")
    @permission(command_name="quote", restrict=True)
    async def quote(self, ctx: commands.Context, member: discord.Member, * ,quote: str) -> None:
        await ctx.defer()
        avatar_bytes = await member.display_avatar.read()
            
        image = await asyncio.to_thread(
            make_quote_card,
            image=avatar_bytes,
            quote=quote,
            author=member.display_name,
            handle=f"@{member.name}"
        )

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, filename="quote.png"))
        try:
            await ctx.message.delete()
        except:
            pass

async def setup(bot):
    await bot.add_cog(LilyUtility(bot))