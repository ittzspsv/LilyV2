from PIL import Image, ImageDraw, ImageFont
from ui.sWinOrLossImageGenerator import add_glow_border, draw_neon_text
import os


def draw_gradient_text(image, position, text, font, gradient_colors, anchor="lt", stretch_height=1.0):
    temp_img = Image.new("RGBA", (1000, 500), (0, 0, 0, 0))
    draw_temp = ImageDraw.Draw(temp_img)
    text_bbox = draw_temp.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = int((text_bbox[3] - text_bbox[1]) * stretch_height)

    padding = 15

    text_mask = Image.new("L", (text_width, text_height + padding * 2), 0)
    draw_mask = ImageDraw.Draw(text_mask)
    draw_mask.text((0, padding), text, font=font, fill=255)

    gradient = Image.new("RGBA", (text_width, text_height + padding * 2), color=0)
    for y in range(text_height + padding * 2):
        ratio = y / (text_height + padding * 2)
        r = int(gradient_colors[0][0] * (1 - ratio) + gradient_colors[1][0] * ratio)
        g = int(gradient_colors[0][1] * (1 - ratio) + gradient_colors[1][1] * ratio)
        b = int(gradient_colors[0][2] * (1 - ratio) + gradient_colors[1][2] * ratio)
        ImageDraw.Draw(gradient).line([(0, y), (text_width, y)], fill=(r, g, b), width=1)

    gradient.putalpha(text_mask)

    x, y = position
    if anchor in ("mm", "mt", "mb"):
        x -= text_width // 2
    elif anchor in ("rm", "rt", "rb"):
        x -= text_width
    if anchor in ("mm", "lm", "rm"):
        y -= (text_height + padding * 2) // 2
    elif anchor in ("mb", "lb", "rb"):
        y -= (text_height + padding * 2)

    image.paste(gradient, (int(x), int(y)), gradient)


def CreateBaseComboImage(icons, font_path="src/ui/font/Game Bubble.ttf", combo_text=None):
    if not 1 <= len(icons) <= 4:
        raise ValueError("You must provide between 1 and 4 icons.")

    try:
        bg = Image.open("src/ui/ComboBase.png").convert("RGBA")
    except FileNotFoundError:
        raise FileNotFoundError("Background image 'src/ui/ComboBase.png' not found.")

    draw = ImageDraw.Draw(bg)

    icon_size = (130, 130)
    icon_y = 210
    spacing_x = 160

    total_width = (len(icons) - 1) * spacing_x
    base_x = (bg.width - icon_size[0] - total_width) // 2

    for i, icon_path in enumerate(icons):
        if not icon_path or not isinstance(icon_path, str):
            raise ValueError(f"[Icon Error] Invalid path at index {i}: {icon_path!r}")

        if not os.path.isfile(icon_path):
            raise FileNotFoundError(f"[Icon Error] File not found at index {i}: '{icon_path}'")

        try:
            icon = Image.open(icon_path).convert("RGBA").resize(icon_size)
        except Exception as e:
            raise IOError(f"[Icon Error] Failed to open or process image '{icon_path}': {e}")

        icon_glow = add_glow_border(icon, glow_color=(0, 255, 255), blur_radius=8, glow_alpha=150)
        x = base_x + i * spacing_x
        glow_offset = (x - 10, icon_y - 10)
        bg.alpha_composite(icon_glow, glow_offset)
        bg.paste(icon, (x, icon_y), icon)

    if combo_text:
        lines = combo_text.strip().split("\n")
        line_spacing = 8

        box_top = 400
        box_bottom = 860
        box_height = box_bottom - box_top
        max_font_size = 36
        min_font_size = 14

        for font_size in range(max_font_size, min_font_size - 1, -1):
            try:
                font = ImageFont.truetype(font_path, font_size)
            except OSError:
                font = ImageFont.load_default()

            total_height = sum(font.getbbox(line)[3] - font.getbbox(line)[1] + line_spacing for line in lines) - line_spacing
            if total_height <= box_height:
                break

        start_y = box_top + 1
        left_margin = 180

        gradient_colors = [(135, 206, 250), (180, 150, 255)]

        for line in lines:
            draw_gradient_text(bg, (left_margin, start_y), line, font, gradient_colors, anchor="lt", stretch_height=1.0)
            start_y += font.getbbox(line)[3] - font.getbbox(line)[1] + line_spacing

    return bg

def CreateBaseBuildIcon(icons):
    if not 1 <= len(icons) <= 4:
        raise ValueError("You must provide between 1 and 4 icons.")
    icon_size = (280, 280)
    spacing_x = 40 
    padding_x = 80
    padding_y = 50

    total_width = len(icons) * icon_size[0] + (len(icons) - 1) * spacing_x
    width = total_width + 2 * padding_x
    height = icon_size[1] + 2 * padding_y

    bg = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    icon_y = padding_y

    for i, icon_path in enumerate(icons):
        if not icon_path or not isinstance(icon_path, str):
            raise ValueError(f"[Icon Error] Invalid path at index {i}: {icon_path!r}")
        if not os.path.isfile(icon_path):
            raise FileNotFoundError(f"[Icon Error] File not found at index {i}: '{icon_path}'")

        try:
            icon = Image.open(icon_path).convert("RGBA").resize(icon_size)
        except Exception as e:
            raise IOError(f"[Icon Error] Failed to open or process image '{icon_path}': {e}")

        icon_glow = add_glow_border(icon, glow_color=(0, 255, 255), blur_radius=8, glow_alpha=150)
        x = padding_x + i * (icon_size[0] + spacing_x)
        glow_offset = (x - 10, icon_y - 10)
        bg.alpha_composite(icon_glow, glow_offset)
        bg.paste(icon, (x, icon_y), icon)

    return bg