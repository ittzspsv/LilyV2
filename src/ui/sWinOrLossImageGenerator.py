from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os



def format_value(val):
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
        return str(value)

def draw_neon_text(img, position, text, font, glow_color, text_color, anchor="mm"):
    draw = ImageDraw.Draw(img)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    for offset in range(1, 4):
        glow_draw.text(position, text, font=font, fill=glow_color, anchor=anchor, stroke_width=offset)

    blurred_glow = glow.filter(ImageFilter.GaussianBlur(radius=5))
    img.paste(blurred_glow, (0, 0), blurred_glow)

    draw.text(position, text, font=font, fill=text_color, anchor=anchor)

def draw_gradient_text(
    image, 
    position, 
    text, 
    font, 
    gradient_colors, 
    anchor="lt", 
    stretch_height=1.0, 
    scale=1.0
):
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

def draw_gradient_bar(img, x, y, width, height, percent,color_start, color_end,corner_radius=4,glow_intensity=0.3):
    from PIL import ImageDraw, ImageFilter


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

def GenerateWORLImage(your_fruits, your_values, their_fruits, their_values,your_fruit_types,their_fruit_types,trade_winorlose="WIN", trade_conclusion="YOUR TRADE IS A L", percentage_Calculation=77, winorloseorfair = 0, background_type=0):
    icon_size = 120
    value_font_offset = 6
    if background_type == 0:
        background_path = "src/ui/WORLBase.png"
    else:
        background_path = "src/ui/FruitSuggestorBase.png"
    output_path = "trade_Result.png"

    your_coords = [(64, 240), (208, 240), (64, 390), (208, 390)]
    their_coords = [(408, 240), (552, 240), (408, 390), (552, 390)]

    try:
        bg = Image.open(background_path).convert("RGBA")
        img = bg.resize((704, 883))
    except FileNotFoundError:
        print(f"Background not found: {background_path}, using black background.")
        img = Image.new("RGBA", (704, 883), "black")

    draw = ImageDraw.Draw(img)

    def load_font(size):
        try:
            return ImageFont.truetype("src/ui/font/Berlin Sans FB Bold.ttf", size)
        except:
            return ImageFont.load_default()

    font_small = load_font(20)
    font_percentage = load_font(32)
    font_result = load_font(45)
    font_total = load_font(22)

    def paste_fruits(fruits, coords, values, fruit_types):
        total_slots = 4
        for i in range(total_slots):
            coord = coords[i]

            if i < len(fruits):
                fruit = fruits[i]
                val = values[i]
                fruit_type = fruit_types[i]
                try:
                    icon_path = f"src/ui/fruit_icons/{fruit}.png"
                    icon = Image.open(icon_path).convert("RGBA").resize((icon_size, icon_size))

                    avg_color_img = icon.resize((1, 1))
                    avg_color = avg_color_img.getpixel((0, 0))[:3]

                    glow_scale = 2.5
                    glow_size = int(icon_size * glow_scale)
                    glow_img = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
                    glow_draw = ImageDraw.Draw(glow_img)

                    ellipse_bbox = (glow_size // 4, glow_size // 4, 3 * glow_size // 4, 3 * glow_size // 4)
                    glow_draw.ellipse(ellipse_bbox, fill=avg_color + (120,))

                    glow = glow_img.filter(ImageFilter.GaussianBlur(20))

                    glow_pos = (coord[0] - (glow.width - icon_size)//2, coord[1] - (glow.height - icon_size)//2)
                    img.paste(glow, glow_pos, glow)


                    img.paste(icon, coord, icon)

                    value_text_y_offset = icon_size + 5
                    text_pos = (coord[0] + icon_size // 2, coord[1] + value_text_y_offset + value_font_offset)

                    draw_gradient_text(
                        img,
                        text_pos,
                        f"${format_value(val)}",
                        font=font_small,
                        gradient_colors=[(186, 85, 211), (0, 191, 255)],
                        anchor="mt",
                        stretch_height=1.1
                    )

                    if "permanent" in fruit_type.lower():
                        permanent_icon_path = "src/ui/PermanentIcon.png"
                        perm_icon_size = 44
                        permanent_icon = Image.open(permanent_icon_path).convert("RGBA").resize((perm_icon_size, perm_icon_size))

                        x_offset = icon_size - perm_icon_size - 6    
                        y_offset = icon_size - 36                 

                        permanent_pos = (
                            coord[0] + x_offset,
                            coord[1] + y_offset
                        )

                        img.paste(permanent_icon, permanent_pos, permanent_icon)

                except FileNotFoundError:
                    print(f"Missing icon: {fruit}")
            else:
                glow_size = int(icon_size * 2.5)
                placeholder = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(placeholder)
                draw.ellipse((glow_size//4, glow_size//4, 3*glow_size//4, 3*glow_size//4), fill=(255, 255, 255, 30))

                blurred = placeholder.filter(ImageFilter.GaussianBlur(40))
                blurred_pos = (coord[0] - (blurred.width - icon_size)//2, coord[1] - (blurred.height - icon_size)//2)
                img.paste(blurred, blurred_pos, blurred)


    paste_fruits(your_fruits, your_coords, your_values, your_fruit_types)
    paste_fruits(their_fruits, their_coords, their_values, their_fruit_types)

    your_total = sum(your_values)
    their_total = sum(their_values)
    percent = percentage_Calculation


    your_label_x = (your_coords[0][0] + your_coords[1][0] + icon_size) // 2
    their_label_x = (their_coords[0][0] + their_coords[1][0] + icon_size) // 2
    center_x = img.width // 2

    draw_gradient_text(
    img, (your_label_x, 575),
    f"TOTAL: ${format_value(your_total)}",
    font=font_total,
    gradient_colors=[(128, 255, 255), (255, 128, 255)],
    anchor="mm",
    scale=1.25,            
    stretch_height=1    
)

    draw_gradient_text(
        img, (their_label_x, 575),
        f"TOTAL: ${format_value(their_total)}",
        font=font_total,
        gradient_colors=[(255, 180, 255), (180, 255, 255)],
        anchor="mm",
        scale=1.25,
        stretch_height=1
    )

    bar_y = 640
    bar_width = 480 
    bar_height = 6    
    bar_x = center_x - bar_width // 2 

    label_offset_y = -35
    conclusion_offset_y = 40

    if winorloseorfair == 0: 
        color_start = (180, 140, 0)
        color_end = (255, 230, 100)
    elif winorloseorfair == 1:  
        color_start = (120, 0, 0)
        color_end = (255, 100, 100)
    else:  
        color_start = (180, 100, 0)
        color_end = (255, 210, 120)

    draw_gradient_bar(
        img, bar_x, bar_y, bar_width, bar_height, percent,
        color_start=color_start, color_end=color_end,
        corner_radius=3
    )

    draw_gradient_text(
        img, (center_x, bar_y + label_offset_y),
        f"{percent}% {trade_winorlose}",
        font=font_percentage,
        gradient_colors=[color_start, color_end],
        anchor="mm",
        scale=1.0
    )

    draw_gradient_text(
        img, (center_x, bar_y + conclusion_offset_y),
        trade_conclusion,
        font=font_result,
        gradient_colors=[color_start, color_end],
        anchor="mm",
        scale=0.75
    )
    return img

def GAGGenerateWORLImage(your_fruits, your_values, their_fruits, their_values,trade_winorlose="WIN", trade_conclusion="YOUR TRADE IS A L", percentage_Calculation=77, winorloseorfair = 0, background_type=0):
    icon_size = 120
    value_font_offset = 6
    if background_type == 0:
        background_path = "src/ui/GAGWORLBase.png"
    else:
        background_path = "src/ui/FruitSuggestorBase.png"
    output_path = "trade_Result.png"

    your_coords = [(64, 240), (208, 240), (64, 390), (208, 390)]
    their_coords = [(408, 240), (552, 240), (408, 390), (552, 390)]

    try:
        bg = Image.open(background_path).convert("RGBA")
        img = bg.resize((704, 883))
    except FileNotFoundError:
        print(f"Background not found: {background_path}, using black background.")
        img = Image.new("RGBA", (704, 883), "black")

    draw = ImageDraw.Draw(img)

    def load_font(size):
        try:
            return ImageFont.truetype("src/ui/font/Game Bubble.ttf", size)
        except:
            return ImageFont.load_default()

    font_small = load_font(20)
    font_percentage = load_font(32)
    font_result = load_font(45)
    font_total = load_font(22)

    def paste_fruits(fruits, coords, values):
        total_slots = 4
        for i in range(total_slots):
            coord = coords[i]

            if i < len(fruits):
                fruit = fruits[i]
                val = values[i]
                try:
                    icon_path = f"src/ui/GAG/{fruit}.png"
                    if not os.path.exists(icon_path): 
                        icon_path = f"src/ui/GAG/{fruit}.webp"

                    icon = Image.open(icon_path).convert("RGBA")
                    icon.thumbnail((icon_size, icon_size), Image.LANCZOS)

                    glow = add_glow_border(icon, glow_color=(186, 85, 211), blur_radius=8, glow_alpha=180)
                    glow_pos = (coord[0] - 10, coord[1] - 10)
                    img.paste(glow, glow_pos, glow)

                    img.paste(icon, coord, icon)

                    value_text_y_offset = icon_size + 5
                    text_pos = (coord[0] + icon_size // 2, coord[1] + value_text_y_offset + value_font_offset)

                    draw_gradient_text(
                        img,
                        text_pos,
                        f"¢{format_value(val)}",
                        font=font_small,
                        gradient_colors=[(186, 85, 211), (0, 191, 255)],
                        anchor="mt",
                        stretch_height=1.1
                    )

                except FileNotFoundError:
                    print(f"Missing icon: {fruit}")
            else:
                glow_size = icon_size
                placeholder = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(placeholder)
                draw.ellipse((0, 0, glow_size, glow_size), fill=(255, 255, 255, 20))
                blurred = placeholder.filter(ImageFilter.GaussianBlur(radius=6))

                img.paste(blurred, coord, blurred)


    paste_fruits(your_fruits, your_coords, your_values)
    paste_fruits(their_fruits, their_coords, their_values)

    your_total = sum(your_values)
    their_total = sum(their_values)
    percent = percentage_Calculation


    your_label_x = (your_coords[0][0] + your_coords[1][0] + icon_size) // 2
    their_label_x = (their_coords[0][0] + their_coords[1][0] + icon_size) // 2
    center_x = img.width // 2

    draw_gradient_text(img, (your_label_x, 575), f"TOTAL: ¢{format_value(your_total)}",
                    font=font_total, gradient_colors=[(128, 255, 255), (255, 128, 255)], anchor="mm")

    draw_gradient_text(img, (their_label_x, 575), f"TOTAL: ¢{format_value(their_total)}",
                    font=font_total, gradient_colors=[(255, 180, 255), (180, 255, 255)], anchor="mm")

    if winorloseorfair == 0:
        bar_x, bar_y, bar_width, bar_height = 140, 660, 420, 12
        draw_gradient_bar(img, bar_x, bar_y, bar_width, bar_height, percent,
                        color_start=(180, 140, 0), color_end=(255, 230, 100))

        draw_gradient_text(img, (center_x, bar_y - 30), f"{percent}% {trade_winorlose}",
                        font=font_percentage, gradient_colors=[(180, 140, 0), (255, 230, 100)], anchor="mm")
        
        draw_gradient_text(
            img,
            (center_x - 20, bar_y + 80),
            trade_conclusion,
            font=font_result,
            gradient_colors=[(180, 140, 0), (255, 230, 100)],
            anchor="mm"
        )

    elif winorloseorfair == 1:
        bar_x, bar_y, bar_width, bar_height = 140, 660, 420, 12
        draw_gradient_bar(img, bar_x, bar_y, bar_width, bar_height, percent,
                        color_start=(120, 0, 0), color_end=(255, 100, 100))
        draw_gradient_text(img, (center_x, bar_y - 30), f"{percent}% {trade_winorlose}",
                        font=font_percentage, gradient_colors=[(120, 0, 0), (255, 100, 100)], anchor="mm")
        
        draw_gradient_text(
            img,
            (center_x - 20, bar_y + 80),
            trade_conclusion,
            font=font_result,
            gradient_colors=[(120, 0, 0), (255, 100, 100)],
            anchor="mm"
        )

    else:
        bar_x, bar_y, bar_width, bar_height = 140, 660, 420, 12
        draw_gradient_bar(img, bar_x, bar_y, bar_width, bar_height, percent,
                        color_start=(180, 100, 0), color_end=(255, 210, 120))

        draw_gradient_text(img, (center_x, bar_y - 20), f"{percent}% {trade_winorlose}",
                        font=font_percentage, gradient_colors=[(180, 100, 0), (255, 210, 120)], anchor="mm")

        draw_gradient_text(
            img,
            (center_x - 20, bar_y + 80),
            trade_conclusion,
            font=font_result,
            gradient_colors=[(180, 100, 0), (255, 210, 120)],
            anchor="mm"
        )

    img = img.resize((int(img.width * 0.7), int(img.height * 0.7)))
    return img
