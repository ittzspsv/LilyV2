from PIL import Image, ImageDraw, ImageFont
import io
import re
import discord

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


async def GenerateWelcome(member: discord.Member):
    background_img = 'src/ui/Greetings/Welcome.png'
    TEXT_FONT_PATH = "src/ui/font/Berlin Sans FB Bold.ttf"

    base = Image.open(background_img).convert("RGBA")

    avatar_asset = member.avatar.replace(format="png", size=256)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    AVATAR_SIZE = (int(260 * 0.55), int(260 * 0.55))
    avatar = avatar.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)

    mask = Image.new("L", AVATAR_SIZE, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE[0], AVATAR_SIZE[1]), fill=255)

    AVATAR_POS = (220, 125)
    base.paste(avatar, AVATAR_POS, mask)

    draw = ImageDraw.Draw(base)

    username_text = re.sub(r'[^A-Za-z ]', '', member.name.replace('_', ' ').upper())
    username_font_size = 52
    MAX_USERNAME_WIDTH = 500
    username_font = ImageFont.truetype(TEXT_FONT_PATH, username_font_size)
    while draw.textlength(username_text, font=username_font) > MAX_USERNAME_WIDTH and username_font_size > 10:
        username_font_size -= 1
        username_font = ImageFont.truetype(TEXT_FONT_PATH, username_font_size)

    member_font = ImageFont.truetype(TEXT_FONT_PATH, 27)

    username_gradient = [(200, 160, 255), (255, 50, 50)]
    member_gradient   = [(200, 160, 255), (255, 50, 50)]

    USERNAME_POS = (395, 135)
    draw_gradient_text(base, USERNAME_POS, username_text, username_font, username_gradient, anchor="lt")

    MEMBER_POS = (494, 222)
    draw_gradient_text(base, MEMBER_POS, f"MEMBER #{member.guild.member_count}", member_font, member_gradient, anchor="lt")

    final_buffer = io.BytesIO()
    base.save(final_buffer, format="PNG")
    final_buffer.seek(0)

    return final_buffer