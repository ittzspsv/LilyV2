from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os


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


def CreateBaseBuildIcon(icons,combo_text="Ice V\nIce C\nIce Z\nGodhuman X\nGodhuman C\nGodhuman Z",rating_text="10/10",rating_pos=(940, 990),font_path="src/ui/font/Berlin Sans FB Bold.ttf"):
    if not 1 <= len(icons) <= 4:
        raise ValueError("You must provide between 1 and 4 icons.")
    
    bg_image_path = "src/ui/Combo.png"
    if not os.path.isfile(bg_image_path):
        raise FileNotFoundError(f"Background file not found: {bg_image_path}")

    bg = Image.open(bg_image_path).convert("RGBA").copy()
    draw = ImageDraw.Draw(bg)
    bg_w, bg_h = bg.size

    icon_size = (280, 280)
    spacing_x = 40
    padding_x = 80

    icon_shift_y = -430  

    total_width = len(icons) * icon_size[0] + (len(icons) - 1) * spacing_x
    total_icon_height = icon_size[1]
    padding_y = (bg_h - total_icon_height) // 2
    icon_y = padding_y + icon_shift_y

    start_x = (bg_w - total_width) // 2

    for i, icon_path in enumerate(icons):
        if not os.path.isfile(icon_path):
            raise FileNotFoundError(f"[Icon Error] Missing icon: '{icon_path}'")

        icon = Image.open(icon_path).convert("RGBA").resize(icon_size)

        x = start_x + i * (icon_size[0] + spacing_x)

        glow_opacity = 120
        glow_size = (int(icon_size[0] * 2.5), int(icon_size[1] * 2.5))
        glow_img = Image.new("RGBA", glow_size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)

        avg_color_img = icon.resize((1, 1))
        avg_color = avg_color_img.getpixel((0, 0))[:3]

        ellipse_bbox = (glow_size[0] // 4, glow_size[1] // 4,
                        3 * glow_size[0] // 4, 3 * glow_size[1] // 4)
        glow_draw.ellipse(ellipse_bbox, fill=avg_color + (glow_opacity,))

        glow = glow_img.filter(ImageFilter.GaussianBlur(40))

        glow_x = x + icon_size[0] // 2 - glow.width // 2
        glow_y = icon_y + icon_size[1] // 2 - glow.height // 2
        icon_x = x + icon_size[0] // 2 - icon.width // 2
        icon_y_final = icon_y + icon_size[1] // 2 - icon.height // 2

        bg.paste(glow, (glow_x, glow_y), glow)
        bg.alpha_composite(icon, (icon_x, icon_y_final))

    if combo_text:
        lines = combo_text.strip().split("\n")

        box_x = 65
        box_y = 870
        box_w = 760 - 65
        box_h = 1350 - 500

        max_font = 100
        min_font = 25
        line_spacing = 15

        for font_size in range(max_font, min_font - 1, -1):
            font = ImageFont.truetype(font_path, font_size)

            longest = max(lines, key=len)
            w = font.getbbox(longest)[2] - font.getbbox(longest)[0]
            if w > box_w - 50: 
                continue
            total_height = sum(
                (font.getbbox(line)[3] - font.getbbox(line)[1] + line_spacing)
                for line in lines
            ) - line_spacing

            if total_height <= box_h:
                break

        y = box_y + 20
        for line in lines:
            draw.text(
                (box_x + 40, y),
                line,
                font=font,
                fill=(230, 230, 255, 255),
            )
            y += (font.getbbox(line)[3] - font.getbbox(line)[1]) + line_spacing


    if rating_text:
        rx, ry = rating_pos
        try:
            rating_font = ImageFont.truetype(font_path, 95)
        except:
            rating_font = ImageFont.load_default()

        draw.text(
            (rx, ry),
            rating_text,
            font=rating_font,
            fill=(240, 200, 255, 255),
            anchor="lt"
        )

    return bg