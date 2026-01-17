from discord.ext import commands
import discord
import aiohttp

class LilyGTO(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.hybrid_command(name='character', description='Displays the complete character detail from Gate to Oblivion')
    async def character(self, ctx: commands.Context, name: str):
        await ctx.defer()

        try:

            url = "http://51.75.118.5:20261/character"
            payload = {
                "name" : name.lower().replace(" ", "_")
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=payload) as response:
                    api_response = await response.json()
                    char = api_response["character_details"]
                    char_stats = api_response["character_stats"]

                    character_embed = discord.Embed(
                        color=16777215,
                        title=char["name"].upper(),
                        description=f"## DESCRIPTION\n> - {char['description']}\n\n## STATS"
                    )

                    if char["img"]:
                        character_embed.set_image(url=char["img"])
                    character_embed.set_footer(text=char["sex"])
                    character_embed.add_field(name="Max Health", value=str(char_stats["max_health"]), inline=True)
                    character_embed.add_field(name="Durability", value=str(char_stats["durability"]), inline=True)
                    character_embed.add_field(name="Stamina", value=str(char_stats["stamina"]), inline=True)
                    character_embed.add_field(name="Mana", value=str(char_stats["mana"]), inline=True)

                    sword = api_response["sword_details"]
                    sword_stats = api_response["sword_stats"]

                    sword_embed = discord.Embed(
                        color=16777215,
                        title=sword["name"].upper(),
                        description=f"## DESCRIPTION\n> - {sword['description']}\n\n## STATS"
                    )

                    if sword["img"]:
                        sword_embed.set_image(url=sword["img"])
                    sword_embed.add_field(name="Damage", value=str(sword_stats["damage"]), inline=False)

                    embeds = [character_embed, sword_embed]
                    await ctx.reply(embeds=embeds)
        except Exception as e:
            print(e)
            await ctx.reply("Character Not Found!")
async def setup(bot):
    await bot.add_cog(LilyGTO(bot))