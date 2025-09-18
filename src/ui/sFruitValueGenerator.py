from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

FONT_PATH = "src/ui/font/Game Bubble.ttf"
ITEM_IMAGE_FOLDER = "src/ui/fruit_icons"
BACKGROUND = "src/ui/FruitValues.png"

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def format_currency(n):
    return f"${int(n):,}" if n else "$0"

def fit_font_size(draw, text, font_path, max_width, starting_size=46, min_size=20):
    font_size = starting_size
    font = load_font(font_path, font_size)
    text_width, _ = get_text_size(draw, text, font)

    while text_width > max_width and font_size > min_size:
        font_size -= 1
        font = load_font(font_path, font_size)
        text_width, _ = get_text_size(draw, text, font)

    return font

def get_text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_neon_text(img, position, text, font, glow_color, text_color, anchor="mm"):
    draw = ImageDraw.Draw(img)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    for offset in range(1, 4):
        glow_draw.text(position, text, font=font,
                       fill=glow_color[:3] + (100,),
                       anchor=anchor, stroke_width=offset)

    blurred_glow = glow.filter(ImageFilter.GaussianBlur(radius=4))
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


async def GenerateValueImage(data, output="card.png"):
    fruit_name = data.get("fruit_name", "UNKNOWN")
    physical_value = data.get("physical_value", 0)
    permanent_value = data.get("permanent_value", 0)
    value_amount = data.get("value", 0)
    demand = data.get("demand", "")
    demand_type = data.get("demand_type", "")

    bg = Image.open(BACKGROUND).convert("RGBA").resize((704, 883))
    canvas = Image.new("RGBA", bg.size)
    canvas.paste(bg, (0, 0))
    draw = ImageDraw.Draw(canvas)

    big_font = load_font(FONT_PATH, 46)
    label_font = load_font(FONT_PATH, 32)


    icon_file = get_icon_path(ITEM_IMAGE_FOLDER, fruit_name)
    if icon_file:
        icon_size = 220
        icon = Image.open(icon_file).convert("RGBA")
        icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

        avg_color_img = icon.resize((1, 1))
        avg_color = avg_color_img.getpixel((0, 0))[:3]

        glow_size = (int(icon_size * 2.5), int(icon_size * 2.5))
        glow_img = Image.new("RGBA", glow_size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        ellipse_bbox = (glow_size[0] // 4, glow_size[1] // 4,
                        3 * glow_size[0] // 4, 3 * glow_size[1] // 4)
        glow_draw.ellipse(ellipse_bbox, fill=avg_color + (120,))
        glow = glow_img.filter(ImageFilter.GaussianBlur(20))

        angle = 6
        glow = glow.rotate(angle, expand=True, resample=Image.BICUBIC)
        icon = icon.rotate(angle, expand=True, resample=Image.BICUBIC)

        glow_x = 60 + icon_size // 2 - glow.width // 2
        glow_y = 260 + icon_size // 2 - glow.height // 2
        canvas.paste(glow, (glow_x, glow_y), glow)

        icon_x = 60 + icon_size // 2 - icon.width // 2
        icon_y = 260 + icon_size // 2 - icon.height // 2
        canvas.alpha_composite(icon, (icon_x, icon_y))
    else:
        print(f"[WARN] Missing icon for {fruit_name}")

    img = canvas.convert("RGB")
    img_resized = img.resize((int(img.width * 0.7), int(img.height * 0.7)))
    return img_resized
