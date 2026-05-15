import discord

from core.configs.sBotDetails import emoji, img
from discord.ext import commands

def build_staff_embed(staff: discord.Member, data: dict) -> discord.Embed:
    name = data.get("name")
    role_name = data.get("role_name")
    is_loa = data.get("is_loa")
    strikes_count = data.get("strikes_count")
    joined_on = data.get("joined_on")
    timezone = data.get("timezone")
    responsibility = data.get("responsibility")
    retired = data.get("retired")

    if is_loa == 1:
        status_display = f"{emoji['dnd']} On Leave"
    elif retired == 1:
        status_display = f"{emoji['invisible']} Retired"
    else:
        status_display = f"{emoji['online']} Active"

    embed = discord.Embed(
        color=0xFFFFFF,
        title=f"{name}'s Profile",
    )

    embed.set_thumbnail(
        url=staff.avatar.url if staff.avatar else staff.default_avatar.url
    )

    embed.set_image(
        url="https://media.discordapp.net/attachments/1404797630558765141/1437432525739003904/colorbarWhite.png?format=webp&quality=lossless"
    )

    embed.add_field(
        name="__Basic Information__",
        value=(
            f"{emoji['shield']} **Role:** {','.join(role_name or []) or 'N/A'}\n"
            f"{emoji['bookmark']} **Responsibilities:** {responsibility or 'N/A'}\n"
            f"{emoji['clock']} **Timezone:** {timezone or 'N/A'}\n"
            f"{emoji['calender']} **Join Date:** <t:{joined_on}:D>"
        ),
        inline=False,
    )

    embed.add_field(
        name="__Experience Information__",
        value=f"{emoji['clock']} **Evaluated Experience:** <t:{joined_on}:R>",
        inline=False,
    )

    embed.add_field(
        name="__Strikes Information__",
        value=f"{emoji['logs']} **Strike Count:** **{strikes_count}**",
        inline=False,
    )

    embed.add_field(
        name="__Status__",
        value=f"{status_display}\n",
        inline=False,
    )

    return embed

def build_staff_update_embed(
    staff: discord.Member | int,
    handled_staff: discord.Member | discord.User,
    reason: str,
    img: dict
) -> discord.Embed:

    if staff and isinstance(staff, discord.Member):
        embed = discord.Embed(
            color=0xFFFFFF,
            title="Staff Update Information",
            description=f"### {staff.mention} has been removed from the team",
        )

        
        embed.set_thumbnail(url=staff.display_avatar.url)

        embed.set_image(url=img["border"])

        embed.add_field(
            name="Handled by",
            value=handled_staff.mention,
            inline=False,
        )

        embed.add_field(
            name="Reason",
            value=f"- {reason}",
            inline=False,
        )

        return embed
    else:
        return discord.Embed()
    
def build_no_strikes_embed(staff: discord.Member) -> discord.Embed:
    return (
        discord.Embed(
            color=0xf50000,
            title=f"{emoji['cross']} No Strikes Found",
            description=f"No strikes found for {staff.mention}.",
        )
        .set_thumbnail(url=staff.display_avatar.url or img["member"])
        .set_footer(text="Immutable Records • Managed by Lily System")
    )

def build_strikes_list_embed(
        staff: discord.Member, 
        strikes: list[dict]
    ) -> discord.Embed:
    embed = discord.Embed(
        color=0xFFFFFF,
        title=f"{emoji['arrow']} {staff.display_name}'s Strike Information",
        description=f"{emoji['bookmark']} Listing all strikes issued to {staff.mention}",
    )

    embed.set_thumbnail(url=staff.display_avatar.url)
    embed.set_image(url=img["border"])

    for strike in strikes:
        embed.add_field(
            name=f"{emoji['pencil']} __Strike ID: {strike['strike_id']}__",
            value=(
                f"> {emoji['bookmark']} **Reason** : {strike['reason']}\n"
                f"> {emoji['shield']} **Manager** : <@{strike['manager']}>\n"
                f"> {emoji['calender']} **Date** : {strike['date']}"
            ),
            inline=False,
        )

    embed.set_footer(text="Immutable Records • Can only be removed by higher staff")

    return embed

def build_staff_update_result_embed(
    staff: discord.Member,
    ctx: commands.Context,
    old_role_id: int | None,
    new_role_id: int | None,
    reason: str,
    update_type: str
) -> discord.Embed:

    act = "promoted" if update_type == "promotion" else "demoted"

    embed = discord.Embed(
        color=0xFFFFFF,
        title=f"{update_type.title()} Information",
        description=(
            f"### {staff.mention} has been {act}!\n"
            f"### <@&{old_role_id}> -> <@&{new_role_id}>"
        )
    )

    embed.set_thumbnail(url=staff.display_avatar.url)
    embed.set_image(url=img["border"])

    embed.add_field(
        name=f"{act.title()} By",
        value=ctx.author.mention,
        inline=False,
    )

    embed.add_field(
        name="Reason",
        value=f"- {reason}",
        inline=False,
    )

    return embed

def build_staff_batch_update_embed(
    ctx: commands.Context,
    descriptions: list[str],
    update_type: str,
    reason: str,
) -> discord.Embed:

    act = "promoted" if update_type == "promotion" else "demoted"

    embed = discord.Embed(
        color=0xFFFFFF,
        title=f"{update_type.title()} Information",
        description="\n".join(descriptions) if descriptions else "No updates processed."
    )

    embed.set_image(url=img["border"])

    embed.add_field(
        name=f"{act.title()} By",
        value=ctx.author.mention,
        inline=False,
    )

    embed.add_field(
        name="Reason",
        value=f"- {reason}",
        inline=False,
    )

    return embed