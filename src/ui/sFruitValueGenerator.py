from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

FONT_PATH = "src/ui/font/Berlin Sans FB Bold.ttf"
NUMBER_FONT_PATH = "src/ui/font/Game Bubble.ttf"
ITEM_IMAGE_FOLDER = "src/ui/fruit_icons"
BACKGROUND = "src/ui/FruitValues.png"

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def format_currency(val):
    value = int(val)
    if value >= 1_000_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000_000:.1f}DX"
    elif value >= 1_000_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000_000:.1f}NX"
    elif value >= 1_000_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000_000:.1f}OX"
    elif value >= 1_000_000_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000_000_000:.1f}SPX"
    elif value >= 1_000_000_000_000_000_000_000: 
        return f"{value / 1_000_000_000_000_000_000_000:.1f}SX"
    elif value >= 1_000_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000_000:.1f}QI"
    elif value >= 1_000_000_000_000_000:  
        return f"{value / 1_000_000_000_000_000:.1f}QT"
    elif value >= 1_000_000_000_000: 
        return f"{value / 1_000_000_000_000:.1f}T"
    elif value >= 1_000_000_000:  
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:  
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:  
        return f"{value / 1_000:.1f}k"
    else:
        return str(int(value))

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

def draw_gradient_text(image, position, text, font, gradient_colors, anchor="lt", stretch_height=1.2, scale=1.0):
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
    number_font = load_font(NUMBER_FONT_PATH, 32)

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


    max_name_width = 300 
    big_font = fit_font_size(draw, fruit_name.upper(), FONT_PATH, max_name_width, starting_size=46, min_size=28)


    gradient_colors = [(100, 200, 255), (180, 150, 255)]

    draw_gradient_text(
        canvas,
        (180, 520),
        fruit_name.upper(),
        big_font,
        gradient_colors=gradient_colors,
        anchor="mm",
        stretch_height=1.0
    )

    draw_neon_text(
        canvas,
        (180, 520),
        fruit_name.upper(),
        big_font,
        glow_color=(150, 180, 255, 100),
        text_color=(255, 255, 255),
        anchor="mm"
    )

    start_x = 360
    start_y = 280
    row_gap = 95
    overall_y = -45

    def row(label, val, y, glow_color=(0, 255, 120), text_color=(255, 255, 255), number=0):
        draw_gradient_text(
            canvas, (start_x, y + overall_y), label.upper(),
            label_font, [(255, 150, 255), (180, 80, 255)], anchor="lm"
        )
        draw_neon_text(
            canvas, (start_x, y + overall_y + 38), val,
            number_font if number == 1 else label_font,
            glow_color=glow_color, text_color=text_color, anchor="lm"
        )

    row("Physical Value", format_currency(physical_value),
        start_y, glow_color=(0, 255, 120), text_color=(200, 255, 200), number=1)

    row("Permanent Value", format_currency(permanent_value),
        start_y + row_gap, glow_color=(0, 255, 120), text_color=(200, 255, 200), number=1)

    if value_amount:
        row("Value", format_currency(value_amount),
            start_y + row_gap * 2, glow_color=(255, 100, 180), text_color=(255, 180, 220), number=1)
        offset = 3
    else:
        offset = 2

    row("Demand", str(demand),
        start_y + row_gap * offset, glow_color=(255, 200, 50), text_color=(255, 220, 150), number=1)

    if demand_type:
        row("Demand Type", demand_type.upper(),
            start_y + row_gap * (offset + 1), glow_color=(255, 200, 50), text_color=(255, 220, 150))


    img = canvas.convert("RGB")
    #img_resized = img.resize((int(img.width * 0.7), int(img.height * 0.7)), Image.Resampling.LANCZOS)
    return img
