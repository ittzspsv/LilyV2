from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator
import LilyLogging.sLilyLogging as LilyLogging
import LilyModeration.sLilyRoleManagement as rLily
import LilyLeveling.sLilyLevelingCore as LLC
import LilyModeration.sLilyModeration as mLily
import json
import Config.sValueConfig as ValueConfig
import Config.sValueConfig as VC
import LilyManagement.sLilyStaffManagement as LSM

import discord
from discord.ext import commands

import Config.sBotDetails as Config
from enum import Enum

import asyncio

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
    @commands.hybrid_command(name='set_stock_type', description='stock type 0 = embed; 1 = image')
    async def set_stock_type(self, ctx:commands.Context, type:int):
        await ValueConfig.cdb.execute("UPDATE GlobalConfigs SET value = ? WHERE key = ?", (type, "StockImage"))
        await ValueConfig.cdb.commit()
        addltext = "Image" if type == 1 else "Embed"
        await ctx.send(f"Stock Type set to {addltext}")

    @commands.hybrid_command(name='add_bloxfruits_stock_webhook',description='Adds or updates Blox Fruits stock webhook for a guild')
    async def add_bloxfruits_stock_webhook(self,ctx: commands.Context,guild_id: int,webhook_url: str,stock_ping_roll_id: int = 0):
        try:
            cursor = await ValueConfig.cdb.execute(
                "SELECT bf_stock_webhook, StockPingID FROM BF_StockHandler WHERE guild_id = ?",
                (guild_id,)
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
                    (final_webhook, final_stock_ping, guild_id)
                )
            else:
                await ValueConfig.cdb.execute(
                    """
                    INSERT INTO BF_StockHandler (guild_id, bf_stock_webhook, StockPingID)
                    VALUES (?, ?, ?)
                    """,
                    (guild_id, webhook_url, stock_ping_roll_id)
                )

            await ValueConfig.cdb.commit()
            await ctx.send(f"Webhook for guild {guild_id} has been set/updated successfully.")

        except Exception as e:
            await ctx.send(f"Error adding/updating webhook: `{e}`")
            print(e)


    @commands.hybrid_command(name='add_pvz_stock_webhook',description='Adds or updates PVZ stock webhook for a guild')
    async def add_pvz_stock_webhook(self,ctx: commands.Context,guild_id: int,webhook_url: str,mythical_ping: int = 0,godly_ping: int = 0,secret_ping: int = 0):
        try:
            cursor = await ValueConfig.cdb.execute(
                """
                SELECT pvb_stock_webhook, mythical_ping, godly_ping, secret_ping
                FROM PVB_StockHandler
                WHERE guild_id = ?
                """,
                (guild_id,)
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
                    (final_webhook, final_mythical, final_godly, final_secret, guild_id)
                )
            else:
                await ValueConfig.cdb.execute(
                    """
                    INSERT INTO PVB_StockHandler (guild_id, pvb_stock_webhook, mythical_ping, godly_ping, secret_ping)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (guild_id, webhook_url, mythical_ping, godly_ping, secret_ping)
                )

            await ValueConfig.cdb.commit()
            await ctx.send(f"PVZ stock webhook for guild {guild_id} has been set/updated successfully.")

        except Exception as e:
            await ctx.send(f"Error adding/updating PVZ webhook: {e}")
            print(e)

async def setup(bot):
    await bot.add_cog(LilyUtility(bot))