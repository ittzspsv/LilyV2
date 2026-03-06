import discord
import Config.sBotDetails as Configs

from datetime import datetime

from typing import Sequence, Iterable, Union, List

def write_log_embed(timestamp: datetime, user_id: int, log_text: str):
    embed = (
        discord.Embed(
            color=16777215,
            title=f"{Configs.emoji['ticket']} Logging Information",
        )
        .set_footer(text=timestamp)
        .add_field(
            name=f"{Configs.emoji['member']} User",
            value=f"<@{user_id}>",
            inline=True,
        )
        .add_field(
            name=f"{Configs.emoji['pencil']} Reason",
            value=log_text,
            inline=False,
        )
    )

    return embed

def moderation_embed(moderator_id: int, target_user_id: int, mod_type: str, reason: str, proofs: Sequence[Union[discord.Attachment, str]], timestamp: datetime) -> list[discord.Embed]:
    main_embed = discord.Embed(
        color=0xFFFFFF,
        url="https://discohook.app#gallery-G2oFSRb8",
        title=f"{Configs.emoji['ticket']} Logging Information",
        timestamp=timestamp
    )

    main_embed.add_field(
        name=f"{Configs.emoji['bookmark']} Case Type",
        value=mod_type.title(),
        inline=True
    )
    main_embed.add_field(
        name=f"{Configs.emoji['member']} User",
        value=f"<@{target_user_id}>",
        inline=True
    )
    main_embed.add_field(
        name=f"{Configs.emoji['shield']} Moderator",
        value=f"<@{moderator_id}>",
        inline=True
    )
    main_embed.add_field(
        name=f"{Configs.emoji['pencil']} Reason",
        value=reason,
        inline=False
    )

    embeds: list[discord.Embed] = []

    if proofs:
        main_embed.add_field(
            name=f"{Configs.emoji['logs']} Proofs",
            value="",
            inline=False
        )

        first = proofs[0]

        if isinstance(first, discord.Attachment):
            main_embed.set_image(url=first.url)
        else:
            main_embed.set_image(url=first)

        embeds.append(main_embed)

        for proof in proofs[1:]:
            e = discord.Embed(url="https://discohook.app#gallery-G2oFSRb8")

            if isinstance(proof, discord.Attachment):
                e.set_image(url=proof.url)
            else:
                e.set_image(url=proof)

            embeds.append(e)

    else:
        main_embed.add_field(
            name=f"{Configs.emoji['logs']} Proofs",
            value="No Proofs Provided",
            inline=False
        )
        embeds.append(main_embed)

    return embeds