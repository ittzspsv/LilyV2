import discord

from typing import Tuple, Optional

def build_level_embed(member: discord.Member, rank_display: str, level_exp: str, max_level_exp: str, current_level: str) -> discord.Embed:
    embed = discord.Embed(
        color=16777215,
        title=f"{member.name.title()} Current Level Details",
        description=f"# LEVEL : {current_level}",
    )

    embed.add_field(name="Rank", value=f"- {rank_display}",inline=True)
    embed.add_field(name="XP",value=f"- {level_exp}/ {max_level_exp}", inline=True)
    if member.avatar.url:
        embed.set_thumbnail(url=member.avatar.url)
    return embed

def build_profile_embed(member: discord.Embed, message_counts: Tuple[str, str, str], coins: str):
    embed = discord.Embed(
        color=16777215,
        title=f"{member.name.title()} Profile Details",
    )
    embed.add_field(
        name="Message Information",
        value=f"- Daily : {message_counts[0]} \n- Weekly : {message_counts[1]} \n- Total : {message_counts[2]}",
        inline=True,
    )
    embed.add_field(
        name="Economy Information",
        value=f"- ${coins}",
        inline=False,
    )

    return embed