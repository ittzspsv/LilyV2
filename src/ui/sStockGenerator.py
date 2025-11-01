from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

CARD_WIDTH = 900
BG_COLOR = (0, 0, 0)
PRICE_COLOR = (0, 255, 0)
FONT_PATH = "src/ui/font/Berlin Sans FB Bold.ttf"
NUMBER_FONT_PATH = "src/ui/font/Game Bubble.ttf"
ITEM_IMAGE_FOLDER = "src/ui/fruit_icons"

fruits = {
    "Blade": 30000,
    "Rocket": 30000,
}

def get_icon_path(folder, fruit_name):
    for ext in [".png", ".webp", ".jpg", ".jpeg"]:
        candidate = os.path.join(folder, f"{fruit_name}{ext}")
        if os.path.exists(candidate):
            return candidate

    fruit_lower = fruit_name.lower()
    for f in os.listdir(folder):
        name, ext = os.path.splitext(f)
        if name.lower() == fruit_lower and ext.lower() in [".png", ".webp", ".jpg", ".jpeg"]:
            return os.path.join(folder, f)

    return None

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

def StockImageGenerator(data_dict, stock_type="normal"):
    background_path = (
        "src/ui/StockImages/NormalStock.png"
        if "normal" in stock_type
        else "src/ui/StockImages/MirageStock.png"
    )
    bg = Image.open(background_path).convert("RGBA")
    bg_w, bg_h = bg.size

    img = Image.new("RGBA", (bg_w, bg_h), (0, 0, 0, 0))
    img.paste(bg, (0, 0), bg)
    draw = ImageDraw.Draw(img)

    items = list(data_dict.items())
    count = len(items)

    try:
        item_font = ImageFont.truetype(FONT_PATH, 40)
        price_font = ImageFont.truetype(NUMBER_FONT_PATH, 32)
    except:
        item_font = ImageFont.load_default()
        price_font = ImageFont.load_default()

    max_cols = 3
    icon_size = 300 if count <= max_cols else 250
    gap_y = 120

    if count > 2 * max_cols:
        items = items[-2 * max_cols:]
        count = len(items)

    if count <= max_cols:
        rows = [count]
    elif count <= 2 * max_cols:
        first_row = min(max_cols, count)
        second_row = count - first_row
        rows = [first_row, second_row]
    else:
        rows = [max_cols, max_cols]

    total_height = len(rows) * icon_size + (len(rows) - 1) * gap_y + 80
    y_start = (bg_h - total_height) // 2

    item_index = 0
    for r, cols_in_row in enumerate(rows):
        row_y = y_start + r * (icon_size + gap_y)
        total_icon_width = cols_in_row * icon_size
        remaining_space = bg_w - total_icon_width
        gap_x = remaining_space // (cols_in_row + 1)
        x_start = gap_x

        for c in range(cols_in_row):
            if item_index >= count:
                break

            name, price = items[item_index]
            x = x_start + c * (icon_size + gap_x)

            icon_path = get_icon_path(ITEM_IMAGE_FOLDER, name)
            if icon_path:
                icon = Image.open(icon_path).convert("RGBA")
                icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

                avg_color = icon.resize((1, 1)).getpixel((0, 0))[:3]
                glow_size = (int(icon_size * 2), int(icon_size * 2))
                glow_img = Image.new("RGBA", glow_size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow_img)

                ellipse_bbox = (
                    glow_size[0] // 4,
                    glow_size[1] // 4,
                    3 * glow_size[0] // 4,
                    3 * glow_size[1] // 4,
                )
                glow_draw.ellipse(ellipse_bbox, fill=avg_color + (150,))
                glow = glow_img.filter(ImageFilter.GaussianBlur(35))

                glow_x = x - (glow_size[0] - icon_size) // 2
                glow_y = row_y + 30 - (glow_size[1] - icon_size) // 2
                img.paste(glow, (glow_x, glow_y), glow)

                img.paste(icon, (x, row_y + 30), icon)

            draw_neon_text(
            img,
            (x + icon_size // 2, row_y),
            name.upper(),
            item_font,
            glow_color=(200, 100, 255, 140),
            text_color=(245, 230, 255),     
            anchor="mt"
        )

            price_str = f"${price:,}"
            price_w, _ = get_text_size(draw, price_str, price_font)
            price_x = x + (icon_size - price_w) / 2
            price_y = row_y + 30 + icon_size + 15

            draw_neon_text(
                img,
                (price_x + price_w / 2, price_y), 
                price_str,
                price_font,
                glow_color=(190, 90, 255, 140),  
                text_color=(245, 230, 255),  
                anchor="mt"
            )

            item_index += 1

    return img
