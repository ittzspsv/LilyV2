import discord
import polars as pl
import LilyManagement.sLilyStaffManagement as LSM
from datetime import datetime


def SimpleEmbed(stringformat):
    embed = discord.Embed(description=stringformat, colour=0x6600ff)
    return embed

def LogEmbed(user, moderator: discord.Member, reason: str):
    embed = discord.Embed(title="BANNED LOG", colour=0x6600ff, timestamp=datetime.now())

    user_display = f'**{user.mention}**' if isinstance(user, discord.Member) else f'<@{user.id}>'

    embed.add_field(name="**User:** ", value=user_display, inline=True)
    embed.add_field(name="**Moderator:**", value=f'**{moderator.mention}**', inline=True)
    embed.add_field(name="**Reason:**", value=f'{reason}', inline=False)
    embed.set_footer(text=f"ID : {user.id}")
    return embed

def BanEmbed(moderator: discord.Member, reason, appealLink, server_name):
    embed = discord.Embed(title=f"BANNED FROM {server_name}",
                      description="You have been banned!",
                      colour=0x00f5cc)
    embed.add_field(name="Moderator",
                    value=moderator.name,
                    inline=False)
    embed.add_field(name="Reason",
                    value=reason,
                    inline=False)
    embed.add_field(name="Appeal your Ban",
                    value=f"if you think your ban is wrongly done please make an appel here {appealLink}",
                    inline=False)

    return embed
