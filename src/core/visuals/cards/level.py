from PIL import Image, ImageDraw, ImageFont
from typing import Final
from ..components.gradient_text import draw_gradient_text

import discord
import os
import re
import io

bg_image_path: Final = "public/assets/custom/Levels.png"
TEXT_FONT_PATH: Final = "public/fonts/Berlin Sans FB Bold.ttf"

async def CreateLevelCard(member: discord.Member, name="Lily", rank="35", xp="32", max_xp = "64", level='35'):
    if not os.path.isfile(bg_image_path):
        raise FileNotFoundError(f"Background file not found: {bg_image_path}")

    bg = Image.open(bg_image_path).convert("RGBA").copy()
    draw = ImageDraw.Draw(bg)
    bg_w, bg_h = bg.size

    if name:
        username_text = re.sub(r'[^A-Za-z ]', '', name.replace('_', ' ').upper())

        username_text = username_text[:12]

        length = len(username_text)


        SHORT = {"font": 52, "x": 475, "max_width": 420}
        LONG  = {"font": 40, "x": 525, "max_width": 520}

        Lmin, Lmax = 5, 12
        t = min(max((length - Lmin) / (Lmax - Lmin), 0), 1)

        interp_font = int(SHORT["font"] + t * (LONG["font"] - SHORT["font"]))
        interp_x    = int(SHORT["x"]    + t * (LONG["x"]    - SHORT["x"]))
        interp_w    = int(SHORT["max_width"] + t * (LONG["max_width"] - SHORT["max_width"]))

        font_size = interp_font
        min_size = 18

        while True:
            font = ImageFont.truetype(TEXT_FONT_PATH, font_size)
            bbox = font.getbbox(username_text)
            text_w = bbox[2] - bbox[0]

            if text_w <= interp_w or font_size <= min_size:
                break
            font_size -= 2

        USERNAME_POS = (interp_x - text_w // 2, 135)

        username_gradient = [(255, 80, 160), (140, 0, 255)]

        draw_gradient_text(
            bg,
            USERNAME_POS,
            username_text,
            font,
            username_gradient,
            anchor="lt"
        )

    if rank:
        rx, ry = (390, 227)
        try:
            rating_font = ImageFont.truetype(TEXT_FONT_PATH, 25)
        except:
            rating_font = ImageFont.load_default()
        
        draw.text(
            (rx, ry),
            f'RANK  {rank}  | XP  {xp or 0} / {max_xp or 0}',
            font=rating_font,
            fill=(240, 200, 255, 255),
            anchor="lt"
        )

    if level:
        rx, ry = (455, 30)
        try:
            rating_font = ImageFont.truetype(TEXT_FONT_PATH, 77)
        except:
            rating_font = ImageFont.load_default()

        draw.text(
            (rx, ry),
            f'{level}',
            font=rating_font,
            fill=(240, 200, 255, 255),
            anchor="lt"
        )

    avatar_asset = member.display_avatar.replace(format="png", size=256)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    AVATAR_SIZE = (int(260 * 0.55), int(260 * 0.55))
    avatar = avatar.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)

    mask = Image.new("L", AVATAR_SIZE, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE[0], AVATAR_SIZE[1]), fill=255)

    AVATAR_POS = (220, 125)
    bg.paste(avatar, AVATAR_POS, mask)

    return bg
