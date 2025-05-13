import discord
import re
from datetime import datetime


def EmbedParser(config_str: str, ctx:discord.Member):
    embeds_to_display = []
    buttons = []

    def parse_embed_block(embed_block: str) -> discord.Embed:
        title_match = re.search(r'EMBED\s+"?(.*?)"?\s*\n', embed_block)
        color_match = re.search(r'EMBED_COLOR\s+"?(.*?)"?\s*\n', embed_block)
        image_match = re.search(r'EMBED_IMAGE\s+"?(.*?)"?\s*\n', embed_block)
        thumb_match = re.search(r'EMBED_THUMBNAIL\s+"?(.*?)"?\s*\n', embed_block)

        desc = re.sub(
            r'(EMBED\s+".*?"\s*\n|EMBED_COLOR\s+".*?"\s*\n|EMBED_IMAGE\s+".*?"\s*\n|EMBED_THUMBNAIL\s+".*?"\s*\n)',
            '', embed_block)
        desc = re.sub(r'EMBED END', '', desc, flags=re.IGNORECASE).strip()

        embed = discord.Embed(description=desc)

        if title_match:
            title = title_match.group(1).strip()
            if title:
                embed.title = title

        if color_match:
            hex_color = color_match.group(1).strip().lstrip("#")
            if hex_color:
                try:
                    embed.color = discord.Color(int(hex_color, 16))
                except ValueError:
                    pass

        if image_match:
            image_url = image_match.group(1).strip()
            if image_url:
                embed.set_image(url=image_url)

        if thumb_match:
            thumb_url = thumb_match.group(1).strip()
            if thumb_url:
                embed.set_thumbnail(url=thumb_url)

        embed.set_author(
            name=ctx.display_name,
            icon_url=ctx.display_avatar.url
        )

        return embed

    button_pattern = re.compile(
        r'BUTTON NAMED\s+"?(.*?)"?(?:\s+ROW\s*:\s*(\d+))?(?:\s+TYPE\s*:\s*(\w+))?\s*\n(EMBED\s+".+?\n.*?\nEMBED END)',
        re.DOTALL | re.IGNORECASE
    )
    button_blocks = button_pattern.findall(config_str)

    used_embed_blocks = []
    seen_ids = set()

    style_map = {
        'PRIMARY': discord.ButtonStyle.primary,
        'SECONDARY': discord.ButtonStyle.secondary,
        'SUCCESS': discord.ButtonStyle.success,
        'DANGER': discord.ButtonStyle.danger
    }

    for button_label, row_str, type_str, embed_block in button_blocks:
        embed = parse_embed_block(embed_block)

        base_id = re.sub(r'[^a-zA-Z0-9_]', '_', embed.title or button_label.strip())
        custom_id = base_id
        counter = 1
        while custom_id in seen_ids:
            custom_id = f"{base_id}_{counter}"
            counter += 1
        seen_ids.add(custom_id)

        row = int(row_str) if row_str and row_str.isdigit() else None
        style = style_map.get(type_str.upper(), discord.ButtonStyle.secondary) if type_str else discord.ButtonStyle.secondary

        button = discord.ui.Button(
            label=button_label.strip(),
            style=style,
            custom_id=f"show_embed_{custom_id}",
            row=row
        )
        buttons.append((button, embed))
        used_embed_blocks.append(embed_block)

    cleaned_config = config_str
    for block in used_embed_blocks:
        cleaned_config = cleaned_config.replace(block, "")

    base_embed_pattern = re.compile(r'EMBED\s+"?.*?"?\s*\n.*?\nEMBED END', re.DOTALL | re.IGNORECASE)
    for match in base_embed_pattern.finditer(cleaned_config):
        embed_block = match.group()
        embed = parse_embed_block(embed_block)
        embeds_to_display.append(embed)

    return embeds_to_display, buttons

def ParseAdvancedEmbed(data: dict):
    content = data.get("content") or None
    embeds = []
    if content:
        content = re.sub(r'@everyone|@here', '', content)

    for embed_data in data.get("embeds", []):
        try:
            color = discord.Color(embed_data.get("color", 0))
        except (ValueError, TypeError):
            color = discord.Color.default()

        embed = discord.Embed(
            title=embed_data.get("title"),
            description=embed_data.get("description"),
            url=embed_data.get("url"),
            color=color
        )

        if "timestamp" in embed_data:
            try:
                embed.timestamp = datetime.fromtimestamp(int(embed_data["timestamp"]) / 1000)
            except (ValueError, TypeError):
                pass

        if author := embed_data.get("author"):
            embed.set_author(name=author.get("name"), url=author.get("url"), icon_url=author.get("icon_url"))
        if thumbnail := embed_data.get("thumbnail"):
            embed.set_thumbnail(url=thumbnail.get("url"))
        if image := embed_data.get("image"):
            embed.set_image(url=image.get("url"))
        if footer := embed_data.get("footer"):
            embed.set_footer(text=footer.get("text"), icon_url=footer.get("icon_url"))

        for field in embed_data.get("fields", []):
            embed.add_field(
                name=field.get("name"),
                value=field.get("value"),
                inline=field.get("inline", False)
            )

        embeds.append(embed)

    return content, embeds

