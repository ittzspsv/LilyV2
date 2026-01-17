from PIL import Image, ImageDraw, ImageFont
import os
import discord
import re
import random
import string
import io


def draw_gradient_text(
    image, 
    position, 
    text, 
    font, 
    gradient_colors, 
    anchor="lt", 
    stretch_height=1.0, 
    scale=1.0
):
    temp_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    x0, y0, x1, y1 = temp_draw.textbbox((0, 0), text, font=font)
    text_w, text_h = x1 - x0, y1 - y0

    mask = Image.new("L", (text_w, text_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((-x0, -y0), text, font=font, fill=255)

    if scale != 1.0 or stretch_height != 1.0:
        new_w = max(1, int(text_w * scale))
        new_h = max(1, int(text_h * stretch_height * scale))
        mask = mask.resize((new_w, new_h), resample=Image.LANCZOS)
        text_w, text_h = new_w, new_h

    gradient = Image.new("RGBA", (text_w, text_h))
    grad_draw = ImageDraw.Draw(gradient)
    c0, c1 = gradient_colors[0], gradient_colors[1]

    for y in range(text_h):
        t = y / float(text_h - 1) if text_h > 1 else 0
        r = int(c0[0] * (1 - t) + c1[0] * t)
        g = int(c0[1] * (1 - t) + c1[1] * t)
        b = int(c0[2] * (1 - t) + c1[2] * t)
        grad_draw.line([(0, y), (text_w, y)], fill=(r, g, b))

    gradient.putalpha(mask)

    x, y = position
    if anchor in ("mm", "mt", "mb"):
        x -= text_w // 2
    elif anchor in ("rm", "rt", "rb"):
        x -= text_w
    if anchor in ("mm", "lm", "rm"):
        y -= text_h // 2
    elif anchor in ("mb", "lb", "rb"):
        y -= text_h

    image.paste(gradient, (int(x), int(y)), gradient)

async def CreateLevelCard(member: discord.Member, name="Lily", rank="35", xp="32", max_xp = "64", level='35'):
    bg_image_path = "src/ui/Greetings/Levels.png"
    TEXT_FONT_PATH = "src/ui/font/Berlin Sans FB Bold.ttf"
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

    avatar_asset = member.avatar.replace(format="png", size=256)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    AVATAR_SIZE = (int(260 * 0.55), int(260 * 0.55))
    avatar = avatar.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)

    mask = Image.new("L", AVATAR_SIZE, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE[0], AVATAR_SIZE[1]), fill=255)

    AVATAR_POS = (220, 125)
    bg.paste(avatar, AVATAR_POS, mask)

    final_buffer = io.BytesIO()
    bg.save(final_buffer, format="PNG")
    final_buffer.seek(0)

    return final_buffer

async def CreateProfileCard(member: discord.Member=None, today="66", weekly="16,000", total="116,600", coins="77"):
    bg_image_path = "src/ui/Greetings/Profile.png"
    TEXT_FONT_PATH = "src/ui/font/Game Bubble.ttf"
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

    avatar_asset = member.avatar.replace(format="png", size=256)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    AVATAR_SIZE = (int(260 * 0.8), int(260 * 0.8))
    avatar = avatar.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)

    mask = Image.new("L", AVATAR_SIZE, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE[0], AVATAR_SIZE[1]), fill=255)

    AVATAR_POS = (519, 81)
    bg.paste(avatar, AVATAR_POS, mask)

    final_buffer = io.BytesIO()
    bg.save(final_buffer, format="PNG")
    final_buffer.seek(0)

    return final_buffer

async def CreateLeaderBoardCard(rank_dict=[]):
    bg_image_path = "src/ui/Greetings/LeaderBoard.png"
    TEXT_FONT_PATH = "src/ui/font/Berlin Sans FB Bold.ttf"
    NUMBER_FONT_PATH = "src/ui/font/Game Bubble.ttf"
    CROWN_PATH = "src/ui/misc_icons/CrownSecondary.png"
    DEFAULT_AVATAR = "src/ui/bot_icons/Bot PFP.png"

    if not os.path.isfile(bg_image_path):
        raise FileNotFoundError(f"Background file not found: {bg_image_path}")

    bg = Image.open(bg_image_path).convert("RGBA").copy()
    draw = ImageDraw.Draw(bg)

    AVATAR_SIZE = (220, 220)
    CROWN_SIZE = (180, 120)
    GRID_COLS = 3
    START_X = 175
    START_Y = 260
    GAP_X = 440
    GAP_Y = 350

    mask = Image.new("L", AVATAR_SIZE, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE[0], AVATAR_SIZE[1]), fill=255)

    async def DrawAvatarCard():
        for index, data in enumerate(rank_dict[:10], start=1):
            name = data.get("name", "Lily").upper()
            member = data.get("member", None)


            if index == 10:
                AVATAR_POS = (START_X + GAP_X, START_Y + 3 * GAP_Y)
            else:
                col = (index - 1) % GRID_COLS
                row = (index - 1) // GRID_COLS
                AVATAR_POS = (START_X + col * GAP_X, START_Y + row * GAP_Y)

            if member and member.avatar:
                avatar_asset = member.avatar.replace(format="png", size=256)
                avatar_bytes = await avatar_asset.read()
                avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            else:
                avatar = Image.open(DEFAULT_AVATAR).convert("RGBA")

            avatar = avatar.resize(AVATAR_SIZE, Image.LANCZOS)
            bg.paste(avatar, AVATAR_POS, mask)

            if index == 1:
                crown = Image.open(CROWN_PATH).convert("RGBA").resize(CROWN_SIZE, Image.LANCZOS)
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