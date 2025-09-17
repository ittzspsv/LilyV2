from LilyRulesets.sLilyRulesets import PermissionEvaluator, rPermissionEvaluator
import LilyLogging.sLilyLogging as LilyLogging
import LilyModeration.sLilyRoleManagement as rLily
import LilyLeveling.sLilyLevelingCore as LLC
import LilyModeration.sLilyModeration as mLily
import Config.sValueConfig as ValueConfig
import Config.sValueConfig as VC

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

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles)
    @commands.hybrid_command(name="assign_channel", description="Assign Particular feature of the bot limited to the specific channel. Ex-Stock Update")
    async def assign_channel(self, ctx, bot_feature: Channels, channel_to_assign: discord.TextChannel):
        if bot_feature == self.Channels.StockUpdate:
            await ValueConfig.cdb.execute("UPDATE ConfigData SET bf_stock_channel_id = ? WHERE guild_id = ?", (channel_to_assign.id, ctx.guild.id))
            await ValueConfig.cdb.commit()
            await ctx.send(f"Stock Update receives in <#{channel_to_assign.id}>")
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
        else:
            await ctx.send(f"Unable to Assign the Channel")

    # MESSAGING UTILITY
    @PermissionEvaluator(RoleAllowed=lambda: Config.StaffRoles)
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

    #UID UTILITY
    @commands.hybrid_command(name='id', description='returns the id of a specific usertype')
    async def id(self, ctx:commands.Context, user:discord.Member=None):
        if user== None:
            await ctx.send(ctx.author.id)
        else:
            await ctx.send(user.id)

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles)
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

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles)
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
                max_rows = 30  # cap for safety
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

    @PermissionEvaluator(RoleAllowed=lambda: Config.DeveloperRoles + Config.OwnerRoles)
    @commands.hybrid_command(name='set_stock_type', description='stock type 0 = embed; 1 = image')
    async def set_stock_type(self, ctx:commands.Context, type:int):
        await ValueConfig.cdb.execute("UPDATE stock_config SET value = ? WHERE key = ?", (type, "StockImage"))
        await ValueConfig.cdb.commit()
        await ctx.send(f"Setted Stock Type to {type}")

async def setup(bot):
    await bot.add_cog(LilyUtility(bot))