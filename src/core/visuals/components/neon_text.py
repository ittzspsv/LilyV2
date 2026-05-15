from PIL import ImageDraw, Image, ImageFilter

def draw_neon_text(img, position, text, font, glow_color, text_color, anchor="mm"):
    draw = ImageDraw.Draw(img)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    for offset in range(1, 4):
        glow_draw.text(position, text, font=font, fill=glow_color, anchor=anchor, stroke_width=offset)

    blurred_glow = glow.filter(ImageFilter.GaussianBlur(radius=5))
    img.paste(blurred_glow, (0, 0), blurred_glow)
    draw.text(position, text, font=font, fill=text_color, anchor=anchor)