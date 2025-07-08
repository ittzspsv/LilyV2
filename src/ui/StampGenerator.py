from PIL import Image, ImageDraw, ImageFont
import numpy as np


def generate_gradient_text(text, font, size, gradient_start, gradient_end):
    text_mask = Image.new("L", size, 0)
    text_draw = ImageDraw.Draw(text_mask)

    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2

    text_draw.text((x, y), text, fill=255, font=font)

    gradient_array = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    for y in range(size[1]):
        ratio = y / size[1]
        r = int(gradient_start[0] * (1 - ratio) + gradient_end[0] * ratio)
        g = int(gradient_start[1] * (1 - ratio) + gradient_end[1] * ratio)
        b = int(gradient_start[2] * (1 - ratio) + gradient_end[2] * ratio)
        a = int(gradient_start[3] * (1 - ratio) + gradient_end[3] * ratio)
        gradient_array[y, :, :] = [r, g, b, a]

    gradient_img = Image.fromarray(gradient_array, mode='RGBA')
    text_colored = Image.new("RGBA", size, (255, 255, 255, 0))
    text_colored = Image.composite(gradient_img, text_colored, text_mask)

    return text_colored


def fit_font_size(text, font_path, max_width, max_height, start_size=200):
    for font_size in range(start_size, 10, -2):
        font = ImageFont.truetype(font_path, font_size)
        bbox = font.getbbox(text)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= max_width and h <= max_height:
            return font
    raise ValueError("Text too large to fit in stamp")


def center_overlay(base, overlay, x_shift=-7, y_shift=-16):
    base_w, base_h = base.size
    overlay_w, overlay_h = overlay.size

    x = (base_w - overlay_w) // 2 + x_shift
    y = (base_h - overlay_h) // 2 + y_shift

    result = base.copy()
    result.paste(overlay, (x, y), overlay)
    return result



def create_stamp(TEXT:str):
    BASE_IMAGE_PATH = "src/libraries/wantedposter/assets/image_components/stamp_base.png"
    FONT_PATH = "src/ui/font/nexa-rust.slab-black-shadow-01.otf"
    FONT_COLOR_START = (255, 0, 0, 255)
    FONT_COLOR_END   = (255, 0, 0, 255)      
    PADDING = 20
    ROTATION_ANGLE = 30
    base = Image.open(BASE_IMAGE_PATH).convert("RGBA")
    w, h = base.size

    max_text_width = w - 2 * PADDING
    max_text_height = h - 2 * PADDING

    font = fit_font_size(TEXT, FONT_PATH, max_text_width, max_text_height)

    text_img = generate_gradient_text(TEXT, font, (w, h), FONT_COLOR_START, FONT_COLOR_END)
    rotated_text = text_img.rotate(ROTATION_ANGLE, expand=True, resample=Image.BICUBIC)

    final_stamp = center_overlay(base, rotated_text)
    return final_stamp
