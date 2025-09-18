from PIL import Image, ImageDraw, ImageFont
import numpy as np
import math


def generate_gradient_text(text, font, size, gradient_start, gradient_end, y_stretch=1.0):
    text_mask = Image.new("L", size, 0)
    text_draw = ImageDraw.Draw(text_mask)

    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size[0] - text_width) // 2 - bbox[0]
    y = (size[1] - text_height) // 2 - bbox[1]
    text_draw.text((x, y), text, fill=255, font=font)

    gradient_array = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    for yy in range(size[1]):
        ratio = yy / size[1]
        r = int(gradient_start[0] * (1 - ratio) + gradient_end[0] * ratio)
        g = int(gradient_start[1] * (1 - ratio) + gradient_end[1] * ratio)
        b = int(gradient_start[2] * (1 - ratio) + gradient_end[2] * ratio)
        a = int(gradient_start[3] * (1 - ratio) + gradient_end[3] * ratio)
        gradient_array[yy, :, :] = [r, g, b, a]

    gradient_img = Image.fromarray(gradient_array, mode='RGBA')
    text_colored = Image.new("RGBA", size, (255, 255, 255, 0))
    text_colored = Image.composite(gradient_img, text_colored, text_mask)

    if y_stretch != 1.0:
        w, h = text_colored.size
        text_colored = text_colored.resize((w, int(h * y_stretch)), resample=Image.BICUBIC)

    return text_colored


def fit_font_size(text, font_path, max_width, max_height, rotation_angle=30, start_size=200):
    char_len = len(text.replace(" ", ""))

    if char_len > 6:
        adj_width = max_width * 0.85
        adj_height = max_height * 1.15
    elif char_len <= 4:
        adj_width = max_width * 0.85
        adj_height = max_height * 0.75
    else:
        adj_width = max_width
        adj_height = max_height

    angle_rad = math.radians(rotation_angle)
    sin_a, cos_a = abs(math.sin(angle_rad)), abs(math.cos(angle_rad))

    for size in range(start_size, 10, -2):
        font = ImageFont.truetype(font_path, size)
        bbox = font.getbbox(text)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        rotated_w = w * cos_a + h * sin_a
        rotated_h = w * sin_a + h * cos_a

        if rotated_w <= adj_width and rotated_h <= adj_height:
            return font

    raise ValueError("Text too large to fit in stamp")


def create_stamp(TEXT: str):
    BASE_IMAGE_PATH = "src/libraries/wantedposter/assets/image_components/stamp_base.png"
    FONT_PATH = "src/ui/font/nexa-rust.slab-black-shadow-01.otf"
    FONT_COLOR_START = (255, 0, 0, 255)
    FONT_COLOR_END = (255, 0, 0, 255)
    ROTATION_ANGLE = 30
    PADDING = 20

    base = Image.open(BASE_IMAGE_PATH).convert("RGBA")
    w, h = base.size

    max_text_width = w - 2 * PADDING
    max_text_height = h - 2 * PADDING

    font = fit_font_size(TEXT, FONT_PATH, max_text_width, max_text_height, rotation_angle=ROTATION_ANGLE)

    char_len = len(TEXT.replace(" ", ""))
    if char_len > 6:
        y_stretch = 1.25
    elif char_len <= 4:
        y_stretch = 0.85
    else:
        y_stretch = 1.0

    text_img = generate_gradient_text(TEXT, font, (w, h), FONT_COLOR_START, FONT_COLOR_END, y_stretch=y_stretch)

    rotated = text_img.rotate(ROTATION_ANGLE, expand=True, resample=Image.BICUBIC)

    result = base.copy()
    x = (w - rotated.width) // 2
    y = (h - rotated.height) // 2
    result.paste(rotated, (x, y), rotated)
    return result
