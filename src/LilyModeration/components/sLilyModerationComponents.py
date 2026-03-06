import discord

from typing import Optional

import Config.sBotDetails as Config


def ban_embed(moderator: discord.Member, reason: Optional[str], appealLink: Optional[str], server_name: str) -> discord.Embed:
    embed = (
        discord.Embed(
            color=0xFFFFFF,
            title=f"{Config.emoji['arrow']} You Have Been Banned!",
        )
        .set_image(url=Config.img['border'])
        .add_field(
            name=f"{Config.emoji['bookmark']} Reason",
            value=reason,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['shield']} Moderator",
            value=moderator.name,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['bot']} Server",
            value=server_name,
            inline=False,
        )
        .add_field(
            name=f"{Config.emoji['ban_hammer']} Appeal Your Ban Here",
            value=f"If you think your ban was wrongly done, please make an appeal here: {appealLink}",
            inline=False,
        )
    )
    return embed

def mute_embed(moderator: discord.Member, reason: Optional[str], guild_name: str) -> discord.Embed:
    embed = discord.Embed(
                    color=0xFFFFFF,
                    title=f"{Config.emoji['arrow']} YOU HAVE BEEN MUTED!",
                )
    embed.set_image(url=Config.img['border'])
    embed.add_field(
        name=f"{Config.emoji['bookmark']} Reason",
        value=reason,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['shield']} Moderator",
        value=moderator.mention,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['bot']} Server",
        value=guild_name,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['ban_hammer']} Appeal Your Ban Here",
        value=f"If you think your mute was wrongly done, please make an appeal here: {Config.appeal_server_link}",
        inline=False,
    )
    return embed

def warn_embed(moderator: discord.Member, reason: Optional[str], guild_name: str) -> discord.Embed:
    embed = discord.Embed(
        color=16777215,
        title=f"{Config.emoji['arrow']} You Have Been Warned!",
    )
    embed.set_thumbnail(url=Config.img['warn'])
    embed.add_field(
        name=f"{Config.emoji['bookmark']} Reason",
        value=reason,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['shield']} Moderator",
        value=moderator.mention,
        inline=False,
    )
    embed.add_field(
        name=f"{Config.emoji['bot']} Server",
        value=guild_name,
        inline=False,
    )

    return embed