from PIL import Image, ImageDraw, ImageFont, ImageFilter

'''
seed_data = [
    {
        "name": "Carrot",
        "quantity": "x3",
        "rarity": "Common",
        "base_price": "¢10",
        "image_path": "src/ui/GAG/Carrot.png"
    },
    {
        "name": "Tomato",
        "quantity": "x5",
        "rarity": "Uncommon",
        "base_price": "¢20",
        "image_path": "src/ui/GAG/Tomato.png"
    },
    {
        "name": "Ember Lily",
        "quantity": "x2",
        "rarity": "Rare",
        "base_price": "¢35",
        "image_path": "src/ui/GAG/Ember_Lily.png"
    },
    {
        "name": "Burning Bud",
        "quantity": "x1",
        "rarity": "Epic",
        "base_price": "¢50",
        "image_path": "src/ui/GAG/Burning_Bud.png"
    },
    {
        "name": "Giant Pinecone",
        "quantity": "x4",
        "rarity": "Common",
        "base_price": "¢15",
        "image_path": "src/ui/GAG/Giant_Pinecone.png"
    }
]
'''




font_bold = ImageFont.truetype("src/ui/font/DejaVuSans-Bold.ttf", 16)
font_semibold = ImageFont.truetype("src/ui/font/DejaVuSans-Bold.ttf", 14)
font_regular = ImageFont.truetype("src/ui/font/DejaVuSans.ttf", 13)

async def GenerateStockImage(stock_name: str, seed_data: list):
    padding = 16
    card_width = 260
    section_height = 85
    header_height = 40
    entry_gap = 10
    total_height = header_height + (section_height * len(seed_data)) + (entry_gap * (len(seed_data) - 1))

    bg_color = (29, 29, 34)
    text_color = (255, 255, 255)
    accent_green = (166, 255, 101)
    muted_text = (190, 190, 190)

    def create_bevel_card(size, radius, color, shadow_offset=4):
        w, h = size
        base = Image.new("RGBA", (w + shadow_offset, h + shadow_offset), (0, 0, 0, 0))
        shadow = Image.new("RGBA", (w, h), color)

        mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, w, h], radius, fill=255)

        blurred_shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        base.paste(blurred_shadow, (shadow_offset, shadow_offset), mask)
        base.paste(Image.new("RGBA", (w, h), color), (0, 0), mask)

        return base

    card_img = create_bevel_card((card_width, total_height), radius=24, color=bg_color)
    draw = ImageDraw.Draw(card_img)

    draw.text((padding, 10), stock_name, font=font_bold, fill=accent_green)

    line_y = header_height - 6
    draw.line([(padding, line_y), (card_width - padding, line_y)], fill=(60, 60, 65), width=1)

    y = header_height
    for item in seed_data:
        seed_img = None
        try:
            seed_img = Image.open(item["image_path"]).convert("RGBA").resize((90, 90))
        except Exception:
            pass

        name_text = f"{item['name']} {item['quantity']}"
        price_text = f"•  Price : {item['base_price']}"
        rarity_text = f"•  Rarity : {item['rarity']}"

        draw.text((padding, y), name_text, font=font_semibold, fill=text_color)
        draw.text((padding, y + 22), price_text, font=font_regular, fill=muted_text)
        draw.text((padding, y + 40), rarity_text, font=font_regular, fill=muted_text)

        if seed_img:
            card_img.paste(seed_img, (card_width - padding - seed_img.width, y), seed_img)

        y += section_height + entry_gap

    return card_img

async def GenerateStockGridImage(left_title: str, left_data: list, right_title: str, right_data: list):
    padding = 16
    section_height = 85
    header_height = 40
    entry_gap = 10
    card_column_width = 260
    column_gap = 32

    max_entries = max(len(left_data), len(right_data))
    total_height = header_height + (section_height * max_entries) + (entry_gap * (max_entries - 1))
    total_width = (card_column_width * 2) + column_gap

    bg_color = (29, 29, 34)
    text_color = (255, 255, 255)
    accent_green = (166, 255, 101)
    muted_text = (190, 190, 190)

    def create_bevel_card(size, radius, color, shadow_offset=4):
        w, h = size
        base = Image.new("RGBA", (w + shadow_offset, h + shadow_offset), (0, 0, 0, 0))
        shadow = Image.new("RGBA", (w, h), color)

        mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, w, h], radius, fill=255)

        blurred_shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        base.paste(blurred_shadow, (shadow_offset, shadow_offset), mask)
        base.paste(Image.new("RGBA", (w, h), color), (0, 0), mask)

        return base

    full_card = create_bevel_card((total_width, total_height), radius=24, color=bg_color)
    draw = ImageDraw.Draw(full_card)

    def draw_column(title, seed_data, x_offset):
        draw.text((x_offset + padding, 10), title, font=font_bold, fill=accent_green)

        line_y = header_height - 6
        draw.line(
            [(x_offset + padding, line_y), (x_offset + card_column_width - padding, line_y)],
            fill=(60, 60, 65),
            width=1
        )

        y = header_height + 10
        for item in seed_data:
            seed_img = None
            try:
                seed_img = Image.open(item["image_path"]).convert("RGBA").resize((90, 90))
            except Exception:
                pass  # Skip image loading if not found

            name_text = f"{item['name']} x{item['quantity']}"
            price_text = f"•  Price : {item['base_price']}"
            rarity_text = f"•  Rarity : {item['rarity']}"

            draw.text((x_offset + padding, y), name_text, font=font_semibold, fill=text_color)
            draw.text((x_offset + padding, y + 22), price_text, font=font_regular, fill=muted_text)
            draw.text((x_offset + padding, y + 40), rarity_text, font=font_regular, fill=muted_text)

            if seed_img:
                full_card.paste(seed_img, (x_offset + card_column_width - padding - seed_img.width, y), seed_img)

            y += section_height + entry_gap

    draw_column(left_title, left_data, x_offset=0)
    draw_column(right_title, right_data, x_offset=card_column_width + column_gap)

    return full_card