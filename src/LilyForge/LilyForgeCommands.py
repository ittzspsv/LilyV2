import discord
from discord.ext import commands
import LilyForge.LilyForgeCore as LFC
import Misc.sLilyComponentV2 as CV2
from enum import Enum

class OreEnum(str, Enum):
    STONE          = "stone"
    SANDSTONE      = "sandstone"
    COPPER         = "copper"
    IRON           = "iron"
    TIN            = "tin"
    SILVER         = "silver"
    GOLD           = "gold"
    MUSHROOMITE    = "mushroomite"
    PLATINUM       = "platinum"
    BANANAITE      = "bananaite"
    CARDBOARDITE   = "cardboardite"
    AITE           = "aite"
    POOPITE        = "poopite"
    COBALT         = "cobalt"
    TITANIUM       = "titanium"
    VOLCANICROCK   = "volcanicrock"
    LAPISLAZULI    = "lapislazuli"
    QUARTZ         = "quartz"
    AMETHYST       = "amethyst"
    TOPAZ          = "topaz"
    DIAMOND        = "diamond"
    SAPPHIRE       = "sapphire"
    CUPRITE        = "cuprite"
    OBSIDIAN       = "obsidian"
    EMERALD        = "emerald"
    RUBY           = "ruby"
    RIVALITE       = "rivalite"
    URANIUM        = "uranium"
    MYTHRIL        = "mythril"
    EYEORE         = "eyeore"
    FIREITE        = "fireite"
    MAGMAITE       = "magmaite"
    LIGHTITE       = "lightite"
    DARKRYTE       = "darkryte"
    DEMONITE       = "demonite"
    MAGENTACRYSTAL = "magentacrystal"
    CRIMSONCRYSTAL = "crimsoncrystal"
    GREENCRYSTAL   = "greencrystal"
    ORANGECRYSTAL  = "orangecrystal"
    BLUECRYSTAL    = "bluecrystal"
    RAINBOWCRYSTAL = "rainbowcrystal"
    ARCANECRYSTAL  = "arcanecrystal"
    BONEITE        = "boneite"
    DARKBONEITE    = "darkboneite"
    SLIMEITE       = "slimeite"

class ItemType(str, Enum):
    Weapon = "Weapon"
    Armor = "Armor"


class LilyForgeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        for ore in LFC.ore_list:
            member_name = ore["name"].replace(" ", "_")
            member_value = ore["id"]
            setattr(OreEnum, member_name, member_value)

    @commands.hybrid_command(name="forge_chance",description="Select ores to see your forge chances. Seperate them by commas")
    async def ForgeChance(self, ctx: commands.Context, item_type:ItemType,*, ores: str):
        await ctx.defer()
        try:
            result_dict = LFC.ParseOres(ores)
            result = LFC.get_forge_chances_from_selection(result_dict, item_type)

            description = ""
            for r in result:
                description += f"- **{r.get("className", "None")} : {r.get('chance', 0)}%**\n"

            embed = discord.Embed(
                color=16777215,
                title="Forge Chances",
                description=description
            )

            await ctx.send(embed=embed)
        except:
            await ctx.send("Error Forging Chances", ephemeral=True)
    
    @commands.hybrid_command(name="suggest_best_crafts", description="Suggest Best Crafts")
    async def SuggestBestCrafts(self, ctx: commands.Context, item_type: ItemType, ores: str):
        await ctx.defer()
        try:
            result_dict = LFC.ParseOres(ores)
            result = LFC.suggest_best_crafts(result_dict)

            filtered_result = [item for item in result if item['category'].lower() == item_type.name.lower()]

            if not filtered_result:
                await ctx.send(f"No items found for category **{item_type.name}**.", ephemeral=True)
                return

            view = CV2.ForgeSuggestorView(filtered_result)
            await ctx.send(view=view)

        except Exception as e:
            print(e)
            await ctx.send("Error Forging Chances", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LilyForgeCommands(bot))