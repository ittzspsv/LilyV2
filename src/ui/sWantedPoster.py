import os
from PIL import Image, ImageDraw, ImageFont
from libraries.wantedposter.wantedposter import WantedPoster
import libraries.wantedposter.wantedposter as wantedposter
from textwrap import wrap
import aiohttp
import io


async def PosterGeneration(avatar_url: str, first_name: str, last_name: str, bounty_amount: int, level: int, description: str, role_name: str, stamp_bool: bool, stamp_name: str):
    role_name = role_name.upper()
    description = description.upper()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to fetch avatar: HTTP {resp.status}")
                data = await resp.read()
                buffer = io.BytesIO(data)
                buffer.seek(0)
    except Exception:
        fallback_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'LilyUI.png')
        wanted_poster = WantedPoster(fallback_path, first_name, last_name, bounty_amount)
        return wanted_poster.generate(should_make_portrait_transparent=True, stamp_bool=stamp_bool, stamp_name=stamp_name)

    wanted_poster = WantedPoster(buffer, first_name, last_name, bounty_amount)
    base = wanted_poster.generate(should_make_portrait_transparent=True, stamp_bool=stamp_bool, stamp_name=stamp_name)

    font_path = "src/libraries/wantedposter/assets/fonts/PlayfairDisplay-Bold.ttf"
    font_color = "#4b381e"
    
    draw = ImageDraw.Draw(base)

    level_text = f"LEVEL : {level}"
    level_box = (70, 1022, 170, 1043)
    level_font = ImageFont.truetype(font_path, 20)

    bbox = draw.textbbox((0, 0), level_text, font=level_font)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    lx = level_box[0] + (level_box[2] - level_box[0] - lw) // 2
    ly = level_box[1] + (level_box[3] - level_box[1] - lh) // 2
    draw.text((lx, ly), level_text, font=level_font, fill=font_color)

    desc_box = (70, 1044, 440, 1102)
    max_width = desc_box[2] - desc_box[0]
    max_height = desc_box[3] - desc_box[1]

    desc_box = (70, 1044, 440, 1102)
    max_height = desc_box[3] - desc_box[1]

    words = description.split()[:30]
    lines = wrap(" ".join(words), width=9999)
    lines = [" ".join(words[i:i+5]) for i in range(0, len(words), 5)]

    desc_font = ImageFont.truetype(font_path, 14)
    line_height = desc_font.getbbox("Ay")[3] + 2 
    total_text_height = len(lines) * line_height

    dy = desc_box[1] + (max_height - total_text_height) // 2 - 4

    for line in lines:
        draw.text((desc_box[0], dy), line, font=desc_font, fill=font_color)
        dy += line_height


    role_box = (529, 1024, 752, 1073)
    role_font = ImageFont.truetype(font_path, 28)

    bbox = draw.textbbox((0, 0), role_name, font=role_font)
    rw, rh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    rx = role_box[0] + (role_box[2] - role_box[0] - rw) // 2
    ry = role_box[1] + (role_box[3] - role_box[1] - rh) // 2
    draw.text((rx, ry), role_name, font=role_font, fill=font_color)

    return base