from discord.ext import commands
import discord
import io
from ui.sWantedPoster import PosterGeneration

class LilyLeveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='profile', description='Generates a wanted poster image')
    async def profile(self, ctx: commands.Context, member:discord.Member=None):
        if member == None:
            try:
                message = await ctx.reply("Thinking......")
                input_image = ctx.author.display_avatar.url
                poster = await PosterGeneration(input_image, ctx.author.name.upper(), "", 77777777777777777, 100, "Seventh Skeleton Warlord", "Human")

                buffer = io.BytesIO()
                poster.save(buffer, format="PNG")
                buffer.seek(0)

                await message.edit(content=None, attachments=[discord.File(buffer, filename="wanted.png")])

            except Exception as e:
                await message.edit(content=f"Exception {e}")
        else:
            try:
                message = await ctx.reply("Thinking......")
                input_image = member.display_avatar.url
                poster = await PosterGeneration(input_image, member.name.upper(), "", 77777777777777777, 100, "Seventh Skeleton Warlord!", "Human")

                buffer = io.BytesIO()
                poster.save(buffer, format="PNG")
                buffer.seek(0)

                await message.edit(content=None, attachments=[discord.File(buffer, filename="wanted.png")])

            except Exception as e:
                await message.edit(content=f"Exception {e}")

async def setup(bot):
    await bot.add_cog(LilyLeveling(bot))