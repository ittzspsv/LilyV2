import discord
import LilyMiddleman.sLilyMiddlemanCore as LMC
from discord.ext import commands

class LilyMiddleman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @commands.hybrid_command(name="middleman_request", description="Request a middleman")
    async def middleman_request(self, ctx:commands.Context, buyer:discord.Member, seller:discord.Member, transaction:str, payment:str, payment_handler:discord.Member,game:LMC.Games):
        try:
            await LMC.SetupMiddleman(ctx, buyer, seller, transaction, payment, payment_handler, game)
            await ctx.send("Channel Created!")
        except Exception as e:
            await ctx.send(f"Exception {e}")

async def setup(bot):
    await bot.add_cog(LilyMiddleman(bot))