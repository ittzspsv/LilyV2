import discord
import Config.sValueConfig as VC
import ui.sGreetingGenerator as GG

import Misc.sLilyComponentV2 as CV2

async def PostWelcomeGreeting(bot, member: discord.Member):
    try:
        buffer = await GG.GenerateWelcome(member)
        file = discord.File(fp=buffer, filename="welcome.png")

        view = CV2.GreetingComponent(member)

        cursor = await VC.cdb.execute(
            "SELECT welcome_channel FROM ConfigData WHERE guild_id = ?", 
            (member.guild.id,) 
        )
        row = await cursor.fetchone()

        if row and row[0]:
            channel = bot.get_channel(row[0]) 
            if channel:
                await channel.send(file=file, view=view)
    except Exception as e:
        print(f"Exception: {e}")
