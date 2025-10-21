from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator
import LilyLogging.sLilyLogging as LilyLogging
import LilyModeration.sLilyRoleManagement as rLily
import LilyLeveling.sLilyLevelingCore as LLC
import LilyModeration.sLilyModeration as mLily

import json
import Config.sValueConfig as ValueConfig
import Config.sValueConfig as VC
import LilyManagement.sLilyStaffManagement as LSM
import Misc.sLilyEmbed as LE
import aiohttp
import psutil

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
        StockUpdate = "StockUpdate"
        WORL = "WORL"
        FruitValues = "FruitValues"
        Combo = "Combo"
        GAGValues = "GAGValues"
        GAGWORL = "GAGWORL"
        PVBZStockUpdate = "PVBZStockUpdate"
        PVBWeatherUpdate = "PVBWeatherUpdate"

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer')))
    @commands.hybrid_command(name="assign_channel", description="Assign Particular feature of the bot limited to the specific channel. Ex-Stock Update")
    async def assign_channel(self, ctx, bot_feature: Channels, channel_to_assign: discord.TextChannel):
        if bot_feature == self.Channels.StockUpdate:
            await ctx.send(f"Stock Update will be sent in <#{channel_to_assign.id}>")
            webhook = await channel_to_assign.create_webhook(
                name=f"{Config.bot_name} Stock Updates"
            )

            cursor = await ValueConfig.cdb.execute(
                "SELECT guild_id FROM BF_StockHandler WHERE guild_id = ?",
                (ctx.guild.id,)
            )
            row = await cursor.fetchone()

            if row:
                await ValueConfig.cdb.execute(
                    "UPDATE BF_StockHandler SET bf_stock_webhook = ? WHERE guild_id = ?",
                    (webhook.url, ctx.guild.id)
                )
            else: 
                await ValueConfig.cdb.execute(
                    "INSERT INTO BF_StockHandler (guild_id, bf_stock_webhook) VALUES (?, ?)",
                    (ctx.guild.id, webhook.url)
                )

            await ValueConfig.cdb.commit()
            await ctx.send(f"Webhook created: Stock will be sent in {channel_to_assign.name}")
        elif bot_feature == self.Channels.WORL:
            await ValueConfig.cdb.execute("UPDATE ConfigData SET bf_win_loss_channel_id = ? WHERE guild_id = ?", (channel_to_assign.id, ctx.guild.id))
            await ValueConfig.cdb.commit()
            await ctx.send(f"Win or Loss is Caliberated in <#{channel_to_assign.id}>")
        elif bot_feature == self.Channels.FruitValues:
            await ValueConfig.cdb.execute("UPDATE ConfigData SET bf_fruit_value_channel_id = ? WHERE guild_id = ?", (channel_to_assign.id, ctx.guild.id))
            await ValueConfig.cdb.commit()
            await ctx.send(f"Fruit Values is Caliberated in <#{channel_to_assign.id}>")
        elif bot_feature == self.Channels.Combo:
            await ValueConfig.cdb.execute("UPDATE ConfigData SET bf_combo_channel_id = ? WHERE guild_id = ?", (channel_to_assign.id, ctx.guild.id))
            await ValueConfig.cdb.commit()
            await ctx.send(f"Combo Channel Set To <#{channel_to_assign.id}>")
        elif bot_feature == self.Channels.GAGValues:
            await ValueConfig.cdb.execute("UPDATE ConfigData SET gag_item_values_channel_id = ? WHERE guild_id = ?", (channel_to_assign.id, ctx.guild.id))
            await ValueConfig.cdb.commit()
            await ctx.send(f"GAG Values Channel Set To <#{channel_to_assign.id}>")
        elif bot_feature == self.Channels.GAGWORL:
            await ValueConfig.cdb.execute("UPDATE ConfigData SET gag_win_loss_channel_id = ? WHERE guild_id = ?", (channel_to_assign.id, ctx.guild.id))
            await ValueConfig.cdb.commit()
            await ctx.send(f"GAG WORL Channel Set To <#{channel_to_assign.id}>")
        elif bot_feature == self.Channels.PVBZStockUpdate:
            await ctx.send(f"Stock Update will be sent in <#{channel_to_assign.id}>")
            webhook = await channel_to_assign.create_webhook(
                name=f"{Config.bot_name} Stock Updates"
            )

            cursor = await ValueConfig.cdb.execute(
                "SELECT guild_id FROM PVB_StockHandler WHERE guild_id = ?",
                (ctx.guild.id,)
            )
            row = await cursor.fetchone()

            if row:
                await ValueConfig.cdb.execute(
                    "UPDATE PVB_StockHandler SET pvb_stock_webhook = ? WHERE guild_id = ?",
                    (webhook.url, ctx.guild.id)
                )
            else:
                await ValueConfig.cdb.execute(
                    "INSERT INTO PVB_StockHandler (guild_id, pvb_stock_webhook) VALUES (?, ?)",
                    (ctx.guild.id, webhook.url)
                )

            await ValueConfig.cdb.commit()
            await ctx.send(f"Webhook created: Stock will be sent in {channel_to_assign.name}")
        elif bot_feature == self.Channels.PVBWeatherUpdate:
            try:
                await ctx.send(f"Stock Update will be sent in <#{channel_to_assign.id}>")
                webhook = await channel_to_assign.create_webhook(
                    name=f"{Config.bot_name} Weather Updates"
                )

                cursor = await ValueConfig.cdb.execute(
                    "SELECT guild_id FROM PVB_WeatherHandler WHERE guild_id = ?",
                    (ctx.guild.id,)
                )
                row = await cursor.fetchone()

                if row:
                    await ValueConfig.cdb.execute(
                        "UPDATE PVB_WeatherHandler SET pvb_weather_webhook = ? WHERE guild_id = ?",
                        (webhook.url, ctx.guild.id)
                    )
                else:
                    await ValueConfig.cdb.execute(
                        "INSERT INTO PVB_WeatherHandler (guild_id, pvb_weather_webhook) VALUES (?, ?)",
                        (ctx.guild.id, webhook.url)
                    )

                await ValueConfig.cdb.commit()
                await ctx.send(f"Webhook created: Weather will be sent in {channel_to_assign.name}")
            except Exception as e:
                print(e)

    # MESSAGING UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff')))
    @commands.hybrid_command(name='direct_message', description='direct messages using the bot')
    async def dm(self, ctx, user: discord.User, message: str): 
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
    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
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

    #UID UTILITY
    @commands.hybrid_command(name='id', description='returns the id of a specific usertype')
    async def id(self, ctx:commands.Context, user:discord.Member=None):
        if user== None:
            await ctx.send(ctx.author.id)
        else:
            await ctx.send(user.id)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='run_value_query', description='executes arbitary query for the database ValueData.')
    async def run_value_query(self, ctx:commands.Context, *, query: str):
            try:
                cursor = await VC.vdb.execute(query)

                try:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description] if cursor.description else []
                except Exception:
                    rows = None
                    columns = []

                await VC.vdb.commit()

                if rows:
                    chunk_size = 5

                    col_widths = []
                    for i, col in enumerate(columns):
                        max_len = max(len(str(row[i])) for row in rows) if rows else 0
                        col_widths.append(max(len(col), max_len))

                    header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
                    separator = "-+-".join("-" * col_widths[i] for i in range(len(columns)))

                    for i in range(0, len(rows), chunk_size):
                        chunk = rows[i:i+chunk_size]
                        lines = []
                        for row in chunk:
                            line = " | ".join(str(row[j]).ljust(col_widths[j]) for j in range(len(columns)))
                            lines.append(line)
                        table = "\n".join([header, separator] + lines)
                        await ctx.send(f"```\n{table}\n```")
                        await asyncio.sleep(0.5)
                else:
                    await ctx.send("Execution Successful")

            except Exception as e:
                await ctx.send(f"Error: `{type(e).__name__}: {e}`")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='run_levels_query', description='executes arbitary query for the database Levels.')
    async def run_levels_query(self, ctx: commands.Context, *, query: str):
        try:
            cursor = await LLC.ldb.execute(query)

            try:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
            except Exception:
                rows = None
                columns = []

            await VC.vdb.commit()

            if rows:
                max_rows = 30
                total_rows = len(rows)
                rows = rows[:max_rows]

                col_widths = []
                for i, col in enumerate(columns):
                    max_len = max(len(str(row[i])) for row in rows) if rows else 0
                    col_widths.append(max(len(col), max_len))

                header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
                separator = "-+-".join("-" * col_widths[i] for i in range(len(columns)))

                lines = []
                for row in rows:
                    line = " | ".join(str(row[j]).ljust(col_widths[j]) for j in range(len(columns)))
                    lines.append(line)

                table = "\n".join([header, separator] + lines)

                if total_rows > max_rows:
                    table += f"\n... and {total_rows - max_rows} more rows not shown."

                await ctx.send(f"```\n{table}\n```")

            else:
                await ctx.send("Execution Successful")

        except Exception as e:
            await ctx.send(f"Error: `{type(e).__name__}: {e}`")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='run_config_query', description='executes arbitary query for the database Config.')
    async def run_config_query(self, ctx: commands.Context, *, query: str):
        try:
            cursor = await ValueConfig.cdb.execute(query)

            try:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
            except Exception:
                rows = None
                columns = []

            await VC.vdb.commit()

            if rows:
                max_rows = 30
                total_rows = len(rows)
                rows = rows[:max_rows]

                col_widths = []
                for i, col in enumerate(columns):
                    max_len = max(len(str(row[i])) for row in rows) if rows else 0
                    col_widths.append(max(len(col), max_len))

                header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
                separator = "-+-".join("-" * col_widths[i] for i in range(len(columns)))

                lines = []
                for row in rows:
                    line = " | ".join(str(row[j]).ljust(col_widths[j]) for j in range(len(columns)))
                    lines.append(line)

                table = "\n".join([header, separator] + lines)

                if total_rows > max_rows:
                    table += f"\n... and {total_rows - max_rows} more rows not shown."

                await ctx.send(f"```\n{table}\n```")

            else:
                await ctx.send("Execution Successful")

        except Exception as e:
            await ctx.send(f"Error: `{type(e).__name__}: {e}`")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='run_botlogs_query', description='executes arbitary query for the database BotLogs.')
    async def run_botlogs_query(self, ctx: commands.Context, *, query: str):
        try:
            cursor = await LilyLogging.bdb.execute(query)

            try:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
            except Exception:
                rows = None
                columns = []

            await VC.vdb.commit()

            if rows:
                max_rows = 30
                total_rows = len(rows)
                rows = rows[:max_rows]

                col_widths = []
                for i, col in enumerate(columns):
                    max_len = max(len(str(row[i])) for row in rows) if rows else 0
                    col_widths.append(max(len(col), max_len))

                header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
                separator = "-+-".join("-" * col_widths[i] for i in range(len(columns)))

                lines = []
                for row in rows:
                    line = " | ".join(str(row[j]).ljust(col_widths[j]) for j in range(len(columns)))
                    lines.append(line)

                table = "\n".join([header, separator] + lines)

                if total_rows > max_rows:
                    table += f"\n... and {total_rows - max_rows} more rows not shown."

                await ctx.send(f"```\n{table}\n```")

            else:
                await ctx.send("Execution Successful")

        except Exception as e:
            await ctx.send(f"Error: `{type(e).__name__}: {e}`")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='run_modlogs_query', description='executes arbitary query for the database Modlogs.')
    async def run_modlogs_query(self, ctx: commands.Context, *, query: str):
        try:
            cursor = await LilyLogging.mdb.execute(query)

            try:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
            except Exception:
                rows = None
                columns = []

            await VC.vdb.commit()

            if rows:
                max_rows = 30
                total_rows = len(rows)
                rows = rows[:max_rows]

                col_widths = []
                for i, col in enumerate(columns):
                    max_len = max(len(str(row[i])) for row in rows) if rows else 0
                    col_widths.append(max(len(col), max_len))

                header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
                separator = "-+-".join("-" * col_widths[i] for i in range(len(columns)))

                lines = []
                for row in rows:
                    line = " | ".join(str(row[j]).ljust(col_widths[j]) for j in range(len(columns)))
                    lines.append(line)

                table = "\n".join([header, separator] + lines)

                if total_rows > max_rows:
                    table += f"\n... and {total_rows - max_rows} more rows not shown."

                await ctx.send(f"```\n{table}\n```")

            else:
                await ctx.send("Execution Successful")

        except Exception as e:
            await ctx.send(f"Error: `{type(e).__name__}: {e}`")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.hybrid_command(name='set_stock_type', description='stock type 0 = embed; 1 = image')
    async def set_stock_type(self, ctx:commands.Context, type:int):
        await ValueConfig.cdb.execute("UPDATE GlobalConfigs SET value = ? WHERE key = ?", (type, "StockImage"))
        await ValueConfig.cdb.commit()
        addltext = "Image" if type == 1 else "Embed"
        await ctx.send(f"Stock Type set to {addltext}")

    @commands.hybrid_command(name='add_bloxfruits_stock_webhook',description='Adds or updates Blox Fruits stock webhook for a guild')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def add_bloxfruits_stock_webhook(self,ctx: commands.Context,guild_id: str,webhook_url: str,stock_ping_roll_id: int = 0):
        try:
            cursor = await ValueConfig.cdb.execute(
                "SELECT bf_stock_webhook, StockPingID FROM BF_StockHandler WHERE guild_id = ?",
                (int(guild_id),)
            )
            row = await cursor.fetchone()

            if row:
                current_webhook, current_stock_ping_id = row

                final_webhook = webhook_url or current_webhook
                final_stock_ping = stock_ping_roll_id or current_stock_ping_id

                await ValueConfig.cdb.execute(
                    """
                    UPDATE BF_StockHandler
                    SET bf_stock_webhook = ?, StockPingID = ?
                    WHERE guild_id = ?
                    """,
                    (final_webhook, final_stock_ping, int(guild_id))
                )
            else:
                await ValueConfig.cdb.execute(
                    """
                    INSERT INTO BF_StockHandler (guild_id, bf_stock_webhook, StockPingID)
                    VALUES (?, ?, ?)
                    """,
                    (int(guild_id), webhook_url, stock_ping_roll_id)
                )

            await ValueConfig.cdb.commit()
            await ctx.send(f"Webhook for guild {guild_id} has been set/updated successfully.", ephemeral=True)
            channel = await ctx.guild.fetch_channel(1430313688010719253)
            if channel:
                await channel.send(f'<@{ctx.author.id}> Assigned Blox Fruits Stock webhook to his guild with id {guild_id}')

        except Exception as e:
            await ctx.send(f"Error adding/updating webhook: `{e}`", ephemeral=True)
            print(e)

    @commands.hybrid_command(name='add_pvz_stock_webhook',description='Adds or updates PVZ stock webhook for a guild')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def add_pvb_stock_webhook(self,ctx: commands.Context,guild_id: str,webhook_url: str,mythical_ping: int = 0,godly_ping: int = 0,secret_ping: int = 0):
        try:
            cursor = await ValueConfig.cdb.execute(
                """
                SELECT pvb_stock_webhook, mythical_ping, godly_ping, secret_ping
                FROM PVB_StockHandler
                WHERE guild_id = ?
                """,
                (int(guild_id),)
            )
            row = await cursor.fetchone()

            if row:
                current_webhook, current_mythical, current_godly, current_secret = row

                final_webhook = webhook_url or current_webhook
                final_mythical = mythical_ping or current_mythical
                final_godly = godly_ping or current_godly
                final_secret = secret_ping or current_secret

                await ValueConfig.cdb.execute(
                    """
                    UPDATE PVB_StockHandler
                    SET pvb_stock_webhook = ?, mythical_ping = ?, godly_ping = ?, secret_ping = ?
                    WHERE guild_id = ?
                    """,
                    (final_webhook, final_mythical, final_godly, final_secret, int(guild_id))
                )
            else:
                await ValueConfig.cdb.execute(
                    """
                    INSERT INTO PVB_StockHandler (guild_id, pvb_stock_webhook, mythical_ping, godly_ping, secret_ping)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (int(guild_id), webhook_url, mythical_ping, godly_ping, secret_ping)
                )

            await ValueConfig.cdb.commit()
            await ctx.send(f"PVZ stock webhook for guild {guild_id} has been set/updated successfully.", ephemeral=True)
            channel = await ctx.guild.fetch_channel(1430313688010719253)
            if channel:
                await channel.send(f'<@{ctx.author.id}> Assigned PVB Stock webhook to his guild with id {guild_id}')

        except Exception as e:
            await ctx.send(f"Error adding/updating PVZ webhook: {e}", ephemeral=True)
            print(e)

    @commands.hybrid_command(name='add_pvz_weather_webhook',description='Adds or updates PVZ weather webhook for a guild')
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def add_pvb_weather_webhook(self,ctx: commands.Context,guild_id: str,webhook_url: str,weather_ping: int = 0):
        try:
            cursor = await ValueConfig.cdb.execute(
                """
                SELECT pvb_weather_webhook, weather_ping
                FROM PVB_WeatherHandler
                WHERE guild_id = ?
                """,
                (int(guild_id),)
            )
            row = await cursor.fetchone()

            if row:
                current_webhook, current_ping = row

                final_webhook = webhook_url or current_webhook
                final_ping = weather_ping or current_ping

                await ValueConfig.cdb.execute(
                    """
                    UPDATE PVB_WeatherHandler
                    SET pvb_weather_webhook = ?, weather_ping = ?
                    WHERE guild_id = ?
                    """,
                    (final_webhook, final_ping, int(guild_id))
                )
            else:
                await ValueConfig.cdb.execute(
                    """
                    INSERT INTO PVB_WeatherHandler (guild_id, pvb_weather_webhook, weather_ping)
                    VALUES (?, ?, ?)
                    """,
                    (int(guild_id), webhook_url, weather_ping)
                )

            await ValueConfig.cdb.commit()
            await ctx.send(f"PVZ weather webhook for guild {guild_id} has been set/updated successfully.", ephemeral=True)
            channel = await ctx.guild.fetch_channel(1430313688010719253)
            if channel:
                await channel.send(f'<@{ctx.author.id}> Assigned PVB Weather webhook to his guild with id {guild_id}')

        except Exception as e:
            await ctx.send(f"Error adding/updating PVZ weather webhook: {e}", ephemeral=True)
            print(e)

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer',)))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='reaction_roles',description='Adds or updates reaction roles')
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

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.hybrid_command(name='latency',description='sends the latency of the bot')
    async def latency(self, ctx: commands.Context):
        await ctx.send(f'`{round(self.bot.latency * 1000, 2)}ms`')

async def setup(bot):
    await bot.add_cog(LilyUtility(bot))