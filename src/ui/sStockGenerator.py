from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import math
import os
import numpy as np



CARD_WIDTH = 900
BG_COLOR = (0, 0, 0)
PRICE_COLOR = (0, 255, 0)
FONT_PATH = "src/ui/font/Game Bubble.ttf"
ITEM_IMAGE_FOLDER = "src/ui/fruit_icons"


fruits = {
    "Blade": 30000,
    "Rocket": 30000,
    "Dough": 30000,
    "Buddha": 30000,
    "Portal": 30000,
    "Kitsune": 30000,
    "Dough": 30000,
    "Dragon": 30000

}


def get_text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_neon_text(img, position, text, font, glow_color, text_color, anchor="mm"):
    draw = ImageDraw.Draw(img)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    for offset in range(1, 4):
        glow_draw.text(position, text, font=font, fill=glow_color, anchor=anchor, stroke_width=offset)

    blurred_glow = glow.filter(ImageFilter.GaussianBlur(radius=5))
    img.paste(blurred_glow, (0, 0), blurred_glow)

    draw.text(position, text, font=font, fill=text_color, anchor=anchor)

def draw_gradient_text(image, position, text, font, gradient_colors, anchor="lt", stretch_height=1.0):
    temp_img = Image.new("RGBA", (1000, 500), (0, 0, 0, 0))
    draw_temp = ImageDraw.Draw(temp_img)
    text_bbox = draw_temp.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = int((text_bbox[3] - text_bbox[1]) * stretch_height)

    text_mask = Image.new("L", (text_width, text_height), 0)
    draw_mask = ImageDraw.Draw(text_mask)
    draw_mask.text((0, 0), text, font=font, fill=255)

    gradient = Image.new("RGBA", (text_width, text_height), color=0)
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(text_height):
        ratio = y / text_height
        r = int(gradient_colors[0][0] * (1 - ratio) + gradient_colors[1][0] * ratio)
        g = int(gradient_colors[0][1] * (1 - ratio) + gradient_colors[1][1] * ratio)
        b = int(gradient_colors[0][2] * (1 - ratio) + gradient_colors[1][2] * ratio)
        grad_draw.line([(0, y), (text_width, y)], fill=(r, g, b), width=1)

    gradient.putalpha(text_mask)

    x, y = position
    if anchor in ("mm", "mt", "mb"):
        x -= text_width // 2
    elif anchor in ("rm", "rt", "rb"):
        x -= text_width
    if anchor in ("mm", "lm", "rm"):
        y -= text_height // 2
    elif anchor in ("mb", "lb", "rb"):
        y -= text_height

    image.paste(gradient, (int(x), int(y)), gradient)

def StockImageGenerator(data_dict, output="card.png"):
    count = len(data_dict)
    rows = math.ceil(count / 3)
    card_height = 300 + rows * 260

    img = Image.new("RGBA", (CARD_WIDTH, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        if count == 1:
            item_font_size = 56
            price_font_size = 50
        elif count == 2:
            item_font_size = 50
            price_font_size = 44
        else:
            item_font_size = 42
            price_font_size = 36

        item_font = ImageFont.truetype(FONT_PATH, item_font_size)
        price_font = ImageFont.truetype(FONT_PATH, price_font_size)
    except:
        item_font = ImageFont.load_default()
        price_font = ImageFont.load_default()

    max_cols = 3
    actual_cols = min(count, max_cols)

    if count == 1:
        icon_size = 300
        y_start = 120
    elif count == 2:
        icon_size = 260
        y_start = 150
    else:
        icon_size = 200
        y_start = 130

    gap_x = 40 

    if actual_cols == max_cols:
        total_items_width = actual_cols * icon_size + (actual_cols - 1) * gap_x
        x_start = max(10, (CARD_WIDTH - total_items_width) // 2)
    else:
        x_start = 20

    col_width = icon_size + gap_x
    row_height = icon_size + 120

    i = 0
    for name, price in data_dict.items():
        col = i % actual_cols
        row = i // actual_cols
        x = x_start + col * col_width
        y = y_start + row * row_height

        draw_neon_text(
            img,
            (x + icon_size // 2, y),
            name.upper(),
            item_font,
            glow_color=(0, 255, 255),
            text_color=(255, 255, 255),
            anchor="mt"
        )

        img_path = os.path.join(ITEM_IMAGE_FOLDER, f"{name.lower()}.png")
        if os.path.exists(img_path):
            icon = Image.open(img_path).convert("RGBA")
            icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            img.paste(icon, (x, y + 40), icon)

        price_str = f"${price:,}"
        price_w, _ = get_text_size(draw, price_str, price_font)
        draw.text(
            (x + (icon_size - price_w) / 2, y + 40 + icon_size + 10),
            price_str,
            font=price_font,
            fill=PRICE_COLOR
        )

        i += 1

    return img