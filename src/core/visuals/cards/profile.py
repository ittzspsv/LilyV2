from PIL import Image, ImageDraw, ImageFont
from typing import Final

import os
import discord
import io

bg_image_path: Final = "public/assets/custom/Profile.png"
TEXT_FONT_PATH: Final = "public/assets/fonts/Game Bubble.ttf"

async def profile_img(member: discord.Member, today="66", weekly="16,000", total="116,600", coins="77"):
    if not os.path.isfile(bg_image_path):
        raise FileNotFoundError(f"Background file not found: {bg_image_path}")

    bg = Image.open(bg_image_path).convert("RGBA").copy()
    draw = ImageDraw.Draw(bg)

    if today:
        rx, ry = (305, 140)
        try:
            rating_font = ImageFont.truetype(TEXT_FONT_PATH, 20)
        except:
            rating_font = ImageFont.load_default()

        draw.text(
            (rx, ry),
            f'{today}',
            font=rating_font,
            fill=(240, 200, 255, 255),
            anchor="lt"
        )
    if weekly:
        rx, ry = (305, 162)
        try:
            rating_font = ImageFont.truetype(TEXT_FONT_PATH, 20)
        except:
            rating_font = ImageFont.load_default()

        draw.text(
            (rx, ry),
            f'{weekly}',
            font=rating_font,
            fill=(240, 200, 255, 255),
            anchor="lt"
        )

    if total:
        rx, ry = (305, 185)
        try:
            rating_font = ImageFont.truetype(TEXT_FONT_PATH, 20)
        except:
            rating_font = ImageFont.load_default()

        draw.text(
            (rx, ry),
            f'{total}',
            font=rating_font,
            fill=(240, 200, 255, 255),
            anchor="lt"
        )
    if coins:
        rx, ry = (295, 271)
        try:
            rating_font = ImageFont.truetype(TEXT_FONT_PATH, 20)
        except:
            rating_font = ImageFont.load_default()

        draw.text(
            (rx, ry),
            f'${coins}',
            font=rating_font,
            fill=(240, 200, 255, 255),
            anchor="lt"
        )

    avatar_asset = member.display_avatar.replace(format="png", size=256)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    AVATAR_SIZE = (int(260 * 0.8), int(260 * 0.8))
    avatar = avatar.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)

    mask = Image.new("L", AVATAR_SIZE, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE[0], AVATAR_SIZE[1]), fill=255)

    AVATAR_POS = (519, 81)
    bg.paste(avatar, AVATAR_POS, mask)

    return bg