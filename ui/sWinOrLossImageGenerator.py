from PIL import Image, ImageDraw, ImageFont, ImageFilter

your_fruits = ['Dark Blade', 'Dough', 'Leopard', 'Shadow']
your_values = [110000000, 11000000, 11000000, 11000000]
their_fruits = ['Rumble', 'Portal', 'Light', 'Yeti']
their_values = [11000000, 11000000, 11000000, 11000000]

def GenerateWORLImage(your_fruits, your_values, their_fruits, their_values, trade_winorlose = "WIN", trade_conclusion="YOUR TRADE IS A W", trade_conclusion_color="gold", percentage_Calculation = 77):
    icon_size = 120
    value_font_offset = 6

    your_coords = [(64, 240), (208, 240), (64, 390), (208, 390)]
    their_coords = [(408, 240), (552, 240), (408, 390), (552, 390)]

    img = Image.new("RGBA", (704, 883), "black")
    draw = ImageDraw.Draw(img)

    def load_font(size):
        try:
            return ImageFont.truetype("ui/font/Game Bubble.ttf", size)
        except:
            return ImageFont.load_default()

    font_title_main = load_font(48)
    font_title_sub = load_font(42)
    font_small = load_font(20)
    font_percentage = load_font(32)
    font_result = load_font(40)
    font_diff = load_font(34)
    font_footer = load_font(22)

    def paste_fruits(fruits, coords, values):
        for fruit, coord, val in zip(fruits, coords, values):
            try:
                icon_path = f"ui/fruit_icons/{fruit}.png"
                icon = Image.open(icon_path).convert("RGBA").resize((icon_size, icon_size))

                shadow = icon.copy().resize((icon_size + 20, icon_size + 20)).filter(ImageFilter.GaussianBlur(10))
                shadow_pos = (coord[0] - 10, coord[1] - 10)
                img.paste(shadow, shadow_pos, shadow)

                img.paste(icon, coord, icon)

                text_pos = (coord[0] + icon_size // 2, coord[1] + icon_size + value_font_offset)
                draw.text(text_pos, f"${val:,}", font=font_small, fill="lime", anchor="mt")
            except FileNotFoundError:
                print(f"Missing icon: {fruit}")

    paste_fruits(your_fruits, your_coords, your_values)
    paste_fruits(their_fruits, their_coords, their_values)

    your_total = sum(your_values)
    their_total = sum(their_values)
    diff = your_total - their_total
    percent = percentage_Calculation
    win = diff > 0

    # Titles
    draw.text((img.width // 2, 40), "WIN OR LOSS", font=font_title_main, fill="lime", anchor="mm")
    draw.text((img.width // 2, 100), "CALCULATOR", font=font_title_sub, fill="orange", anchor="mm")

    # Grid Labels
    font_grid_label = load_font(28)

    your_label_x = (your_coords[0][0] + your_coords[1][0] + icon_size) // 2
    their_label_x = (their_coords[0][0] + their_coords[1][0] + icon_size) // 2
    label_y = 200

    draw.text((your_label_x, label_y), "YOUR ITEMS", font=font_grid_label, fill="#FFD700", anchor="mm")
    draw.text((their_label_x, label_y), "THEIR ITEMS", font=font_grid_label, fill="#00FFFF", anchor="mm")

    # Win bar
    center_x = img.width // 2
    bar_x, bar_y, bar_width, bar_height = 140, 660, 420, 12
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_width * (percent / 100)), bar_y + bar_height], fill="lime")

    draw.text((center_x, bar_y - 70), f"{percent}% {trade_winorlose}", font=font_percentage, fill="orange", anchor="mm")

    trade_msg = trade_conclusion
    draw.text((center_x, bar_y + 80), trade_msg, font=font_result, fill=f"{trade_conclusion_color}", anchor="mm")

    '''
    diff_msg = f"WINNING BY ${abs(diff):,}" if not win else f"LOSING BY ${abs(diff):,}"
    draw.text((center_x, bar_y + 110), diff_msg, font=font_diff, fill="cyan", anchor="mm")'''

    draw.text((center_x, 820), ".GG/BLOXTRADE", font=font_footer, fill="orange", anchor="mm")

    output_path = "trade_Result.png"
    img.save(output_path)
    img.show()
    return output_path

GenerateWORLImage(your_fruits, your_values, their_fruits, their_values)