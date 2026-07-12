from PIL import Image, ImageDraw, ImageFont
from typing import Final, Optional
import numpy as np
import unicodedata
from PIL.ImageFont import FreeTypeFont
from io import BytesIO
from pilmoji import Pilmoji
from src.core.visuals.components.wrap_text import wrap_text
from src.core.visuals.components.fade import build_fade_mask
from src.core.configs.path import FONTS as FONT_DIR

from unidecode import unidecode


FONT_REG: Final    = FONT_DIR / "Poppins-Regular.ttf"
FONT_ITALIC: Final = FONT_DIR / "NotoSans-LightItalic.ttf"
FONT_LIGHT: Final  = FONT_DIR / "Poppins-Light.ttf"
W, H = 1200, 630


def make_quote_card(
    image,
    quote: str,
    author: str,
    handle: str,
    subject_max_right_pct: float = 0.53,
    fade_start_pct: float = 0.25,
    fade_end_pct:   float = 0.46,
    text_col_start_pct: float = 0.46,
    invert: bool = True
) -> Image.Image:
    card = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    subject = Image.open(BytesIO(image)).convert("RGBA")
    bbox = subject.getbbox()
    if bbox:
        subject = subject.crop(bbox)
    max_w = int(W * subject_max_right_pct)
    scale_by_h = H / subject.height
    w_if_scale_h = int(subject.width * scale_by_h)
    if w_if_scale_h <= max_w:
        target_w = w_if_scale_h
        target_h = H
        subject  = subject.resize((target_w, target_h), Image.Resampling.LANCZOS)
        crop_y   = 0
    else:
        scale_by_w = max_w / subject.width
        target_w   = max_w
        scaled_h   = int(subject.height * scale_by_w)
        subject    = subject.resize((target_w, scaled_h), Image.Resampling.LANCZOS)
        crop_y     = max((scaled_h - H) // 2, 0)
        subject    = subject.crop((0, crop_y, target_w, crop_y + H))
        target_h   = H
        crop_y     = 0

    if invert:
        grey = subject.convert("LA").convert("RGBA")
    else:
        grey = subject.convert("RGBA")
    paste_x = 0
    paste_y = (H - target_h) // 2
    fade_start_x = int(W * fade_start_pct)
    fade_end_x   = int(W * fade_end_pct)
    full_mask    = build_fade_mask(W, H, fade_start_x, fade_end_x)
    mask_crop = full_mask.crop((paste_x, paste_y,
                                paste_x + target_w, paste_y + target_h))
    r, g, b, a = grey.split()
    combined_alpha = Image.fromarray(
        np.minimum(np.array(a), np.array(mask_crop)).astype(np.uint8)
    )
    grey.putalpha(combined_alpha)
    card.paste(grey, (paste_x, paste_y), grey)

    draw = ImageDraw.Draw(card)

    text_x     = int(W * text_col_start_pct)
    text_w     = W - text_x - 48
    center_x   = text_x + text_w // 2

    quote_font: Optional[FreeTypeFont] = None
    line_h: int = 0
    for size in [56, 50, 44, 38, 32, 28, 24, 20, 16, 14, 12, 8, 4]:
        quote_font = ImageFont.truetype(FONT_REG, size)
        lines      = wrap_text(draw, quote, quote_font, text_w)
        line_h     = size + 14
        if len(lines) * line_h < H * 0.58:
            break

    author_font = ImageFont.truetype(FONT_ITALIC, 36)
    handle_font = ImageFont.truetype(FONT_LIGHT,  28)
    wm_font     = ImageFont.truetype(FONT_LIGHT,  22)

    lines         = wrap_text(draw, quote, quote_font, text_w)
    quote_block_h = len(lines) * line_h
    gap           = 28
    total_h       = quote_block_h + gap + 50 + 40
    y             = (H - total_h) // 2

    with Pilmoji(card) as pilmoji:
        for line in lines:
            lw, _ = pilmoji.getsize(line, font=quote_font)
            pilmoji.text((center_x - lw // 2, y), line, font=quote_font, fill="white")
            y += line_h

        y += gap

        author = unicodedata.normalize("NFKC", author)
        author = unidecode(author) 
        author_normalized = "".join(c for c in author if c.isalnum() or c == " ")

        author_text = f"- {author_normalized}"
        aw, _ = pilmoji.getsize(author_text, font=author_font)
        pilmoji.text((center_x - aw // 2, y), author_text, font=author_font, fill="white")
        y += 50

        hw, hh_val = pilmoji.getsize(handle, font=handle_font)
        padding = 20
        hx = W - hw - padding
        hy = H - hh_val - padding
        pilmoji.text((hx, hy), handle, font=handle_font, fill=(200, 200, 200, 255))

    return card.convert("RGB")