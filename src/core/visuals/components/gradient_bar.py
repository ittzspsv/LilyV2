from PIL import ImageDraw, Image, ImageFilter

def draw_gradient_bar(img, x, y, width, height, percent, color_start, color_end,
                      corner_radius=4, glow_intensity=0.3):
    bar_base = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar_base)

    for i in range(width):
        t = i / (width - 1)
        r = int(color_start[0] * (1 - t) + color_end[0] * t)
        g = int(color_start[1] * (1 - t) + color_end[1] * t)
        b = int(color_start[2] * (1 - t) + color_end[2] * t)
        draw.line([(i, 0), (i, height)], fill=(r, g, b))

    progress_mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(progress_mask)
    progress_width = max(1, int(width * (percent / 100)))
    mask_draw.rounded_rectangle((0, 0, progress_width, height), radius=corner_radius, fill=255)

    track = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    track_draw = ImageDraw.Draw(track)
    track_color = tuple(int(c * glow_intensity) for c in color_end) + (180,)
    track_draw.rounded_rectangle((0, 0, width, height), radius=corner_radius, fill=track_color)

    glow = track.filter(ImageFilter.GaussianBlur(radius=6))
    img.alpha_composite(glow, dest=(x, y))
    img.alpha_composite(track, dest=(x, y))
    img.paste(bar_base, (x, y), progress_mask)

def add_glow_border(icon, glow_color=(255, 255, 255), blur_radius=6, glow_alpha=150):
    glow_size = (icon.size[0] + 20, icon.size[1] + 20)
    glow = Image.new("RGBA", glow_size, (0, 0, 0, 0))

    offset = (10, 10)
    temp_icon = Image.new("RGBA", glow_size, (0, 0, 0, 0))
    temp_icon.paste(icon, offset, icon)

    mask = temp_icon.split()[-1]
    solid_color = Image.new("RGBA", glow_size, glow_color + (0,))
    solid_color.putalpha(mask)

    blurred = solid_color.filter(ImageFilter.GaussianBlur(blur_radius))

    alpha = blurred.split()[-1].point(lambda x: x * (glow_alpha / 255))
    blurred.putalpha(alpha)

    return blurred