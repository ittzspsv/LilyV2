from PIL import ImageDraw, Image


def draw_gradient_text(image, position, text, font, gradient_colors, anchor="lt", stretch_height=1.0, scale=1.0):
    temp_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    x0, y0, x1, y1 = temp_draw.textbbox((0, 0), text, font=font)
    text_w, text_h = x1 - x0, y1 - y0

    mask = Image.new("L", (int(text_w), int(text_h)), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((-x0, -y0), text, font=font, fill=255)

    if scale != 1.0 or stretch_height != 1.0:
        new_w = max(1, int(text_w * scale))
        new_h = max(1, int(text_h * stretch_height * scale))
        mask = mask.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
        text_w, text_h = new_w, new_h

    gradient = Image.new("RGBA", (int(text_w), int(text_h)))
    grad_draw = ImageDraw.Draw(gradient)
    c0, c1 = gradient_colors[0], gradient_colors[1]

    for y in range(int(text_h)):
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