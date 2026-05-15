from PIL import Image, ImageDraw, ImageFont
from typing import Final
from core.utils.lily_utility import format_currency
import io
import re
import discord

BACKGROUND_IMG: Final = 'public/assets/custom/Welcome.png'
TEXT_FONT_PATH: Final = "public/fonts/Berlin Sans FB Bold.ttf"
BASE_USERNAME_POS: Final = (395, 135)
AVATAR_SIZE: Final = (int(260 * 0.55), int(260 * 0.55))

async def welcome_img(member: discord.Member):
    base = Image.open(BACKGROUND_IMG).convert("RGBA")

    avatar_asset = member.display_avatar.replace(format="png", size=256)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    avatar = avatar.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)

    mask = Image.new("L", AVATAR_SIZE, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE[0], AVATAR_SIZE[1]), fill=255)

    AVATAR_POS = (220, 125)
    base.paste(avatar, AVATAR_POS, mask)

    draw = ImageDraw.Draw(base)

    username_text = re.sub(r'[^A-Za-z ]', '', member.name.replace('_', ' ').upper())
    char_len = len(username_text)

    if char_len <= 6:
        username_font_size = 60
        pos_offset = (10, 0)
    elif char_len <= 10:
        username_font_size = 46
        pos_offset = (0, 0)
    elif char_len <= 14:
        username_font_size = 30
        pos_offset = (-10, 2)
    elif char_len <= 18:
        username_font_size = 26
        pos_offset = (-18, 4)
    else:
        username_font_size = 20
        pos_offset = (-25, 6)

    username_font = ImageFont.truetype(TEXT_FONT_PATH, username_font_size)

    MAX_USERNAME_WIDTH = 500
    while draw.textlength(username_text, font=username_font) > MAX_USERNAME_WIDTH and username_font_size > 10:
        username_font_size -= 1
        username_font = ImageFont.truetype(TEXT_FONT_PATH, username_font_size)


    USERNAME_POS = (
        BASE_USERNAME_POS[0] + pos_offset[0],
        BASE_USERNAME_POS[1] + pos_offset[1]
    )

    member_font = ImageFont.truetype(TEXT_FONT_PATH, 27)

    draw.text(
        USERNAME_POS,
        username_text,
        font=username_font,
        fill=(255, 255, 255),
        anchor="lt"
    )

    MEMBER_POS = (475, 225)
    draw.text(
        MEMBER_POS,
        f"MEMBER #{format_currency(str(member.guild.member_count))}",
        font=member_font,
        fill=(200, 200, 200),
        anchor="lt"
    )

    final_buffer = io.BytesIO()
    base.save(final_buffer, format="PNG")
    final_buffer.seek(0)

    return final_buffer