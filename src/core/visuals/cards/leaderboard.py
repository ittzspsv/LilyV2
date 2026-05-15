from PIL import Image, ImageDraw, ImageFont
from typing import Final

import os
import io
import discord

bg_image_path: Final = "public/assets/custom/LeaderBoard.png"
TEXT_FONT_PATH: Final = "public/fonts/Berlin Sans FB Bold.ttf"
NUMBER_FONT_PATH: Final = "public/fonts/Game Bubble.ttf"
CROWN_PATH: Final = "public/assets/thirdparty/CrownSecondary.png"


AVATAR_SIZE: Final = (220, 220)
CROWN_SIZE: Final  = (180, 120)
GRID_COLS: Final  = 3
START_X: Final  = 175
START_Y: Final  = 260
GAP_X: Final  = 440
GAP_Y: Final  = 350

async def leaderboard_img(rank_dict=[]):
    if not os.path.isfile(bg_image_path):
        raise FileNotFoundError(f"Background file not found: {bg_image_path}")

    bg = Image.open(bg_image_path).convert("RGBA").copy()
    draw = ImageDraw.Draw(bg)

    mask = Image.new("L", AVATAR_SIZE, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE[0], AVATAR_SIZE[1]), fill=255)

    async def DrawAvatarCard():
        for index, data in enumerate(rank_dict[:10], start=1):
            name: str = data.get("name", "Lily").upper()
            member: discord.Member = data.get("member", None)


            if index == 10:
                AVATAR_POS = (START_X + GAP_X, START_Y + 3 * GAP_Y)
            else:
                col = (index - 1) % GRID_COLS
                row = (index - 1) // GRID_COLS
                AVATAR_POS = (START_X + col * GAP_X, START_Y + row * GAP_Y)

            avatar_asset = member.display_avatar.replace(format="png", size=256)
            avatar_bytes = await avatar_asset.read()
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

            avatar = avatar.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)
            bg.paste(avatar, AVATAR_POS, mask)

            if index == 1:
                crown = Image.open(CROWN_PATH).convert("RGBA").resize(CROWN_SIZE, Image.Resampling.LANCZOS)
                CROWN_POS = (AVATAR_POS[0] + 20, AVATAR_POS[1] - 100)
                bg.paste(crown, CROWN_POS, crown)

            try:
                num_font = ImageFont.truetype(NUMBER_FONT_PATH, 185)
            except:
                num_font = ImageFont.load_default()
            NUM_POS = (AVATAR_POS[0] - 140 if index != 10 else AVATAR_POS[0] - 235, AVATAR_POS[1])
            draw.text(NUM_POS, str(index), font=num_font, fill=(255, 255, 255, 255))

            max_width = AVATAR_SIZE[0]
            font_size = 60
            while font_size > 10:
                try:
                    font = ImageFont.truetype(TEXT_FONT_PATH, font_size)
                except:
                    font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), name, font=font)
                text_w = bbox[2] - bbox[0]
                if text_w <= max_width:
                    break
                font_size -= 2
            NAME_POS = (AVATAR_POS[0] + (AVATAR_SIZE[0] // 2) - (text_w // 2),
                        AVATAR_POS[1] + AVATAR_SIZE[1] + 20)
            draw.text(NAME_POS, name, font=font, fill=(240, 200, 255, 255))

    await DrawAvatarCard()

    final_buffer = io.BytesIO()
    bg.save(final_buffer, format="PNG")
    final_buffer.seek(0)
    return final_buffer