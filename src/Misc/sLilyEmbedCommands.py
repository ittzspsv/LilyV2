import aiohttp

import discord
import json
import LilyLogging.sLilyLogging as LilyLogging
import Config.sValueConfig as ValueConfig
import LilyManagement.sLilyStaffManagement as LSM
from discord import SelectOption, Interaction, ui

from discord.ext import commands
import Config.sBotDetails as Config
from LilyRulesets.sLilyRulesets import PermissionEvaluator
import Misc.sLilyEmbed as sLilyEmbed

class LilyEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @PermissionEvaluator(RoleAllowed=lambda: LSM.GetRoles(('Developer', 'Staff Manager', 'Manager', 'Head Administrator')))
    @commands.cooldown(rate=1, per=80, type=commands.BucketType.user)
    @commands.hybrid_command(name="embed_create", description="Creates an embed based on JSON config and sends it to a specific channel")
    async def create_embed(self, ctx: commands.Context, channel_to_send: discord.TextChannel, * ,embed_json_config: str = "{}"):
        try:
            if embed_json_config.startswith("http://") or embed_json_config.startswith("https://"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(embed_json_config) as resp:
                            if resp.status != 200:
                                await ctx.send("Failed to fetch data from the provided link.")
                                return
                            embed_json_config = await resp.text()
                except Exception as fetch_error:
                    await ctx.send(f"Fetch Failure {str(fetch_error)}")
                    return

            
            try:
                json_data = json.loads(embed_json_config)
            except json.JSONDecodeError:
                await ctx.send("Invalid JSON Format")
                return
            
            try:
                content, embeds = sLilyEmbed.ParseAdvancedEmbed(json_data)
                await channel_to_send.send(content=content, embeds=embeds)
                await ctx.send("Embed sent successfully.")
                await LilyLogging.WriteLog(ctx, ctx.author.id, f"Has Sent an Embed to <#{channel_to_send.id}>")
                await LilyLogging.PostLog(ctx, discord.Embed(description=f"**EMEBD SENT TO <#{channel_to_send.id}> BY <@{ctx.author.id}>**"))
            except Exception as embed_error:
                await ctx.send(f"Parser Failure: {str(embed_error)}")

        except Exception as e:
            await ctx.send(f"Unhandled Exception: {str(e)}")

async def setup(bot):
    await bot.add_cog(LilyEmbed(bot))