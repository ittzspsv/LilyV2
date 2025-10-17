import discord
import polars as pl

from discord.ext import commands
import LilyManagement.sLilyStaffManagement as LSM
from LilyRulesets.sLilyRulesets import PermissionEvaluator


import Config.sBotDetails as Config

class LilyLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer')))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    @commands.hybrid_command(name='bot_logs', description='gets core bot logs')
    async def botlogs(self, ctx:commands.Context):
        if ctx.author.id not in Config.ids:
            return
        path = 'storage/LilyLogs.txt' 
        try:
            with open(path, 'rb') as f:
                await ctx.send(file=discord.File(f, filename='LilyLogs.txt'))
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer')))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    @commands.hybrid_command(name='clear_bot_logs', description='clears all bot logs')
    async def clear_botlogs(self, ctx:commands.Context):
        if ctx.author.id not in Config.ids:
            await ctx.send("No Permission")
            return
        try:
            with open("storage/LilyLogs.txt", 'r+') as f:
                f.truncate(0)
            await ctx.send("Successfully Cleared Logs")
        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Staff')))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    @commands.hybrid_command(name='user_logs', description='shows current logs for users')
    async def user_logs(self, ctx: commands.Context,user_id: str = None,log_range: str = "0:10"):
        try:
            if ':' in log_range:
                log_min, log_max = map(int, log_range.split(":"))
            else:
                log_min, log_max = 0, int(log_range)
        except ValueError:
            log_min, log_max = 0, 10

        log_file_path = f"storage/{ctx.guild.id}/botlogs/logs.csv"

        try:
            df = pl.read_csv(log_file_path)

            if user_id:
                df = df.filter(pl.col("user_id") == int(user_id))

            df = df.reverse()
            total_rows = df.height
            log_min = max(0, log_min)
            log_max = min(total_rows, log_max)

            df = df.slice(log_min, log_max)

            embed = discord.Embed(
                title="📜 LOGS",
                description=f"Showing logs for user <@{user_id}>" if user_id else "Latest logs",
                colour=0xfe169d
            )
            embed.set_author(name=f"{Config.bot_name}")

            for row in df.iter_rows():
                user_id_val, timestamp, log_text = row
                embed.add_field(
                    name="",
                    value=f"**User:** <@{user_id_val}> at {timestamp}\n**Log:** {log_text}",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"Exception {e}")

    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer')))
    @commands.hybrid_command(name='clearlogs', description='clear bot logs.  taking a override command which takes in how much logs to preserve from latest logs')
    async def clear_logs(self, ctx:commands.Context, last:int=0):
                log_file_path = f"storage/{ctx.guild.id}/botlogs/logs.csv"

                try:
                    df = pl.read_csv(log_file_path)

                    if df.height > last:
                        df = df.tail(last)

                        df.write_csv(log_file_path)
                        await ctx.send(f"Logs deleted, keeping the last {last} logs!")
                    else:
                        await ctx.send("Not enough logs to delete. Keeping existing logs.")

                except Exception as e:
                    await ctx.send(f"Error clearing logs: {e}")

async def setup(bot):
    await bot.add_cog(LilyLogging(bot))