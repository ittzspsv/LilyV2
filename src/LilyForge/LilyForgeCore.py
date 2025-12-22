import math
from itertools import combinations
from rapidfuzz import fuzz, process
import re

INVENTORY_FILE = "forge_inventory.json"
BEST_SETUP_MODE = "tank"

ore_list = [
    {"id": "stone",        "name": "Stone",        "mult": 0.20},
    {"id": "sandstone",    "name": "Sandstone",    "mult": 0.25},
    {"id": "copper",       "name": "Copper",       "mult": 0.30},
    {"id": "iron",         "name": "Iron",         "mult": 0.35},
    {"id": "tin",          "name": "Tin",          "mult": 0.425},
    {"id": "silver",       "name": "Silver",       "mult": 0.50},
    {"id": "gold",         "name": "Gold",         "mult": 0.65},
    {"id": "mushroomite",  "name": "Mushroomite",  "mult": 0.80},
    {"id": "platinum",     "name": "Platinum",     "mult": 0.80},
    {"id": "bananaite",    "name": "Bananaite",    "mult": 0.85},
    {"id": "cardboardite", "name": "Cardboardite", "mult": 0.70},
    {"id": "aite",         "name": "Aite",         "mult": 1.10},
    {"id": "poopite",      "name": "Poopite",      "mult": 1.20},
    {"id": "cobalt",       "name": "Cobalt",       "mult": 1.00},
    {"id": "titanium",     "name": "Titanium",     "mult": 1.15},
    {"id": "volcanicrock", "name": "Volcanic Rock","mult": 1.55},
    {"id": "lapislazuli",  "name": "Lapis Lazuli", "mult": 1.30},
    {"id": "quartz",       "name": "Quartz",       "mult": 1.50},
    {"id": "amethyst",     "name": "Amethyst",     "mult": 1.65},
    {"id": "topaz",        "name": "Topaz",        "mult": 1.75},
    {"id": "diamond",      "name": "Diamond",      "mult": 2.00},
    {"id": "sapphire",     "name": "Sapphire",     "mult": 2.25},
    {"id": "cuprite",      "name": "Cuprite",      "mult": 2.43},
    {"id": "obsidian",     "name": "Obsidian",     "mult": 2.35},
    {"id": "emerald",      "name": "Emerald",      "mult": 2.55},
    {"id": "ruby",         "name": "Ruby",         "mult": 2.95},
    {"id": "rivalite",     "name": "Rivalite",     "mult": 3.33},
    {"id": "uranium",      "name": "Uranium",      "mult": 3.00},
    {"id": "mythril",      "name": "Mythril",      "mult": 3.50},
    {"id": "eyeore",       "name": "Eye Ore",      "mult": 4.00},
    {"id": "fireite",      "name": "Fireite",      "mult": 4.50},
    {"id": "magmaite",     "name": "Magmaite",     "mult": 5.00},
    {"id": "lightite",     "name": "Lightite",     "mult": 4.60},
    {"id": "darkryte",     "name": "Darkryte",     "mult": 6.30},
    {"id": "demonite",     "name": "Demonite",     "mult": 5.50},
    {"id": "magentacrystal","name":"Magenta Crystal","mult":3.10},
    {"id": "crimsoncrystal","name":"Crimson Crystal","mult":3.30},
    {"id": "greencrystal","name":"Green Crystal","mult":3.20},
    {"id": "orangecrystal","name":"Orange Crystal","mult":3.00},
    {"id": "bluecrystal","name":"Blue Crystal","mult":3.40},
    {"id": "rainbowcrystal","name":"Rainbow Crystal","mult":5.25},
    {"id": "arcanecrystal","name":"Arcane Crystal","mult":7.50},
    {"id": "boneite",      "name":"Boneite",       "mult":1.20},
    {"id": "darkboneite",  "name":"Dark Boneite",  "mult":2.25},
    {"id": "slimeite",     "name":"Slimeite",      "mult":2.25},
]

ore_by_id = {o["id"]: o for o in ore_list}

ore_trait_meta = {
    "obsidian": {"traitType": "Armor", "traits": [{"description": "Vitality", "maxStat": 30}]},
    "rivalite": {"traitType": "Weapon", "traits": [{"description": "Crit Chance on Weapons", "maxStat": 20}]},
    "uranium":  {"traitType": "Armor", "traits": [{"description": "max HP AOE Damage on Armor", "maxStat": 5}]},
    "mythril":  {"traitType": "Armor", "traits": [{"description": "Vitality", "maxStat": 15}]},
    "eyeore":   {"traitType": "All",   "traits": [{"description": "Weapon Damage", "maxStat": 15}, {"description": "Health", "maxStat": -10}]},
    "fireite":  {"traitType": "Weapon", "traits": [{"description": "Burn Damage on Weapons with", "maxStat": 20}, {"description": "chance", "maxStat": 30}]},
    "magmaite": {"traitType": "Weapon", "traits": [{"description": "AOE Explosion on Weapons with", "maxStat": 50}, {"description": "chance", "maxStat": 35}]},
    "lightite": {"traitType": "Armor", "traits": [{"description": "Bonus Movement Speed", "maxStat": 15}]},
    "darkryte": {"traitType": "Armor", "traits": [{"description": "Chance to Dodge Damage (Negate Fully)", "maxStat": 15}]},
    "demonite": {"traitType": "Armor", "traits": [{"description": "to Burn Enemy when Damage is Taken.", "maxStat": 25}]},
}

weapon_classes = [
    {"id": "dagger", "name": "Dagger", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/dagger-weapons-the-forge.webp"},
    {"id": "straight", "name": "Straight Sword", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/falchion-sword-weapons-the-forge.webp"},
    {"id": "gauntlet", "name": "Gauntlets", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/ironhand-weapons-the-forge.webp"},
    {"id": "katana", "name": "Katana", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/uchigatana-weapons-the-forge.webp"},
    {"id": "greatsword", "name": "Greatsword", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/crusaders-sword-weapons-the-forge.webp"},
    {"id": "greataxe", "name": "Great Axe", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/double-battle-axe-weapons-the-forge.webp"},
    {"id": "colossal", "name": "Colossal Sword", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/skull-crusher-weapons-the-forge.webp"},
]

weapon_variants = {
    "dagger": [
        {"name": "Dagger", "label": "1/1", "baseDmg": 4.3, "atkTime": 0.35},
        {"name": "Falchion Knife", "label": "1/2", "baseDmg": 4.3, "atkTime": 0.35},
        {"name": "Gladius Dagger", "label": "1/4", "baseDmg": 4.3, "atkTime": 0.32},
        {"name": "Hook", "label": "1/16", "baseDmg": 4.3, "atkTime": 0.35},
    ],
    "straight": [
        {"name": "Falchion Sword", "label": "1/1", "baseDmg": 7.5, "atkTime": 0.59},
        {"name": "Gladius Sword", "label": "1/2", "baseDmg": 7.875, "atkTime": 0.62},
        {"name": "Cutlass", "label": "1/4", "baseDmg": 9.375, "atkTime": 0.66},
        {"name": "Rapier", "label": "1/8", "baseDmg": 7.5, "atkTime": 0.49},
        {"name": "Chaos", "label": "1/16", "baseDmg": 9.375, "atkTime": 0.59},
    ],
    "gauntlet": [
        {"name": "Ironhand", "label": "1/1", "baseDmg": 7.6, "atkTime": 0.51},
        {"name": "Boxing Gloves", "label": "1/4", "baseDmg": 8.0, "atkTime": 0.59},
        {"name": "Relevator", "label": "1/16", "baseDmg": 9.6, "atkTime": 0.69},
    ],
    "katana": [
        {"name": "Uchigatana", "label": "1/1", "baseDmg": 8.5, "atkTime": 0.6},
        {"name": "Tachi", "label": "1/2", "baseDmg": 8.925, "atkTime": 0.63},
    ],
    "greatsword": [
        {"name": "Crusaders Sword", "label": "1/1", "baseDmg": 12, "atkTime": 1.0},
        {"name": "Long Sword", "label": "1/2", "baseDmg": 12, "atkTime": 1.1},
    ],
    "greataxe": [
        {"name": "Double Battle Axe", "label": "1/1", "baseDmg": 15.75, "atkTime": 1.05},
        {"name": "Scythe", "label": "1/2", "baseDmg": 14.25, "atkTime": 0.95},
    ],
    "colossal": [
        {"name": "Great Sword", "label": "1/1", "baseDmg": 20, "atkTime": 1.12},
        {"name": "Hammer", "label": "1/2", "baseDmg": 22, "atkTime": 1.24},
        {"name": "Skull Crusher", "label": "1/2", "baseDmg": 24, "atkTime": 1.4},
        {"name": "Dragon Slayer", "label": "1/3", "baseDmg": 22, "atkTime": 1.12},
        {"name": "Comically Large Spoon", "label": "1/16", "baseDmg": 18, "atkTime": 1.2},
    ],
}

armor_classes = [
    {"id": "light_helm", "name": "Light Helmet", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/light-helmet-thee-forge.jpg"},
    {"id": "light_legs", "name": "Light Leggings", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/light-leggings-the-forge.jpg"},
    {"id": "light_chest", "name": "Light Chestplate", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/light-chestplate-the-forge.jpg"},
    {"id": "medium_helm", "name": "Medium Helmet", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/medium-helmet-the-forge.jpg"},
    {"id": "medium_legs", "name": "Medium Leggings", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/medium-leggings-the-forge.jpg"},
    {"id": "medium_chest", "name": "Medium Chestplate", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/medium-chestplate-the-forge.jpg"},
    {"id": "heavy_helm", "name": "Heavy Helmet", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/knights-helmet-armors-the-forge.png"},
    {"id": "heavy_legs", "name": "Heavy Leggings", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/knight-heavy-leggings-the-forge.jpg"},
    {"id": "heavy_chest", "name": "Heavy Chestplate", "icon" : "https://bloxinformer-cdn.b-cdn.net/wp-content/uploads/2025/11/knight-heavy-chestplate-the-forge.jpg"},
]

armor_variants = {
    "light_helm":  [{"name": "Light Helmet", "label": "1/1"}],
    "light_legs":  [{"name": "Light Leggings", "label":"1/1"}],
    "light_chest": [{"name": "Light Chestplate", "label":"1/1"}],
    "medium_helm": [{"name": "Medium Helmet", "label":"1/1"}, {"name":"Samurai Helmet","label":"1/2"}],
    "medium_legs": [{"name":"Medium Leggings","label":"1/1"}, {"name":"Samurai Leggings","label":"1/2"}],
    "medium_chest":[{"name":"Medium Chestplate","label":"1/1"}, {"name":"Samurai Chestplate","label":"1/2"}],
    "heavy_helm":[{"name":"Knight Helmet","label":"1/1"}, {"name":"Dark Knight Helmet","label":"1/2"}],
    "heavy_legs":[{"name":"Knight Leggings","label":"1/1"}, {"name":"Dark Knight Leggings","label":"1/2"}],
    "heavy_chest":[{"name":"Knight Chestplate","label":"1/1"}, {"name":"Dark Knight Chestplate","label":"1/2"}],
}

armor_health_by_variant = {
    "Light Helmet": 3.75,
    "Light Leggings": 4.375,
    "Light Chestplate": 5.0,
    "Medium Helmet": 6.25,
    "Samurai Helmet": 8.0,
    "Medium Leggings": 7.5,
    "Samurai Chestplate": 12.75,
    "Knight Helmet": 12.5,
    "Knight Leggings": 13.75,
    "Dark Knight Leggings": 21.875,
    "Knight Chestplate": 16.25,
    "Dark Knight Chestplate": 25.0,
}

weapon_class_chances = {
    3:  {"dagger":100, "straight":0,  "gauntlet":0,  "katana":0,  "greatsword":0,  "greataxe":0,  "colossal":0},
    4:  {"dagger":86,  "straight":14},
    5:  {"dagger":35,  "straight":65},
    6:  {"dagger":14,  "straight":86},
    7:  {"dagger":6,   "straight":74, "gauntlet":20},
    8:  {"dagger":2,   "straight":44, "gauntlet":54},
    9:  {"dagger":1,   "straight":24, "gauntlet":65, "katana":10},
    10: {"dagger":0,   "straight":11, "gauntlet":47, "katana":42},
    11: {"straight":5, "gauntlet":32, "katana":63},
    12: {"straight":3, "gauntlet":22, "katana":72, "greatsword":3},
    13: {"straight":1, "gauntlet":14, "katana":62, "greatsword":22},
    14: {"straight":1, "gauntlet":8,  "katana":46, "greatsword":45},
    15: {"gauntlet":5, "katana":34, "greatsword":60},
    16: {"gauntlet":3, "katana":26, "greatsword":69, "greataxe":1},
    17: {"gauntlet":2, "katana":19, "greatsword":68, "greataxe":11},
    18: {"gauntlet":1, "katana":13, "greatsword":57, "greataxe":28},
    19: {"gauntlet":1, "katana":9,  "greatsword":46, "greataxe":45},
    20: {"gauntlet":1, "katana":6,  "greatsword":36, "greataxe":57},
    21: {"katana":4, "greatsword":29, "greataxe":65, "colossal":2},
    22: {"katana":3, "greatsword":23, "greataxe":67, "colossal":7},
    23: {"katana":2, "greatsword":18, "greataxe":66, "colossal":13},
    24: {"katana":2, "greatsword":15, "greataxe":64, "colossal":20},
    25: {"katana":1, "greatsword":12, "greataxe":60, "colossal":26},
    26: {"katana":1, "greatsword":10, "greataxe":56, "colossal":32},
    27: {"katana":1, "greatsword":9,  "greataxe":53, "colossal":37},
    28: {"katana":1, "greatsword":7,  "greataxe":50, "colossal":42},
    29: {"katana":1, "greatsword":7,  "greataxe":47, "colossal":46},
    30: {"katana":1, "greatsword":6,  "greataxe":45, "colossal":49},
    31: {"greatsword":5, "greataxe":43, "colossal":51},
    32: {"greatsword":5, "greataxe":41, "colossal":54},
    33: {"greatsword":4, "greataxe":39, "colossal":56},
    34: {"greatsword":4, "greataxe":38, "colossal":58},
    35: {"greatsword":4, "greataxe":37, "colossal":59},
    36: {"greatsword":3, "greataxe":36, "colossal":61},
    37: {"greatsword":3, "greataxe":35, "colossal":62},
    38: {"greatsword":3, "greataxe":34, "colossal":63},
    39: {"greatsword":3, "greataxe":33, "colossal":64},
    40: {"greatsword":3, "greataxe":32, "colossal":65},
    41: {"greatsword":3, "greataxe":31, "colossal":66},
    42: {"greatsword":3, "greataxe":30, "colossal":67},
    43: {"greatsword":3, "greataxe":29, "colossal":68},
    44: {"greatsword":2, "greataxe":28, "colossal":69},
    45: {"greatsword":2, "greataxe":27, "colossal":70},
    46: {"greatsword":2, "greataxe":26, "colossal":71},
    47: {"greatsword":2, "greataxe":25, "colossal":72},
    48: {"greatsword":2, "greataxe":24, "colossal":73},
    49: {"greatsword":2, "greataxe":23, "colossal":74},
    50: {"greatsword":2, "greataxe":22, "colossal":75},
}

armor_class_chances = {
    3: {"light_helm":100},
    4: {"light_helm":100},
    5: {"light_helm":89, "light_legs":11},
    6: {"light_helm":56, "light_legs":44},
    7: {"light_legs":67, "light_helm":32, "light_chest":1},
    8: {"light_legs":67, "light_helm":17, "light_chest":17},
    9: {"light_legs":51, "light_chest":41, "light_helm":8},
    10: {"light_chest":53, "light_legs":34, "medium_helm":9, "light_helm":4},
    11: {"light_chest":47, "medium_helm":31, "light_legs":20, "light_helm":2},
    12: {"medium_helm":50, "light_chest":37, "light_legs":12, "light_helm":1},
    13: {"medium_helm":60, "light_chest":28, "light_legs":7, "medium_legs":4},
    14: {"medium_helm":55, "medium_legs":22, "light_chest":19, "light_legs":4},
    15: {"medium_legs":43, "medium_helm":43, "light_chest":12, "light_legs":2},
    16: {"medium_legs":57, "medium_helm":32, "light_chest":8, "medium_chest":2, "light_legs":1},
    17: {"medium_legs":57, "medium_helm":22, "medium_chest":16, "light_chest":5, "light_legs":1},
    18: {"medium_legs":48, "medium_chest":35, "medium_helm":14, "light_chest":3},
    19: {"medium_chest":50, "medium_legs":39, "medium_helm":9, "light_chest":2},
    20: {"medium_chest":60, "medium_legs":32, "medium_helm":6, "light_chest":1},
    21: {"medium_chest":63, "medium_legs":25, "heavy_helm":7, "medium_helm":4, "light_chest":1},
    22: {"medium_chest":59, "heavy_helm":19, "medium_legs":19, "medium_helm":3},
    23: {"medium_chest":52, "heavy_helm":32, "medium_legs":14, "medium_helm":2},
    24: {"heavy_helm":44, "medium_chest":44, "medium_legs":10, "medium_helm":1},
    25: {"heavy_helm":51, "medium_chest":36, "medium_legs":7, "heavy_legs":5, "medium_helm":1},
    26: {"heavy_helm":51, "medium_chest":28, "heavy_legs":15, "medium_legs":5, "medium_helm":1},
    27: {"heavy_helm":47, "heavy_legs":28, "medium_chest":21, "medium_legs":4},
    28: {"heavy_helm":42, "heavy_legs":39, "medium_chest":16},
    29: {"heavy_legs":47, "heavy_helm":35, "medium_chest":11, "heavy_chest":4, "medium_legs":2},
    30: {"heavy_legs":49, "heavy_helm":28, "heavy_chest":13, "medium_chest":8, "medium_legs":1},
    31: {"heavy_legs":46, "heavy_chest":25, "heavy_helm":22, "medium_chest":6, "medium_legs":1},
    32: {"heavy_legs":42, "heavy_chest":37, "heavy_helm":17, "medium_chest":4, "medium_legs":1},
    33: {"heavy_chest":47, "heavy_legs":37, "heavy_helm":13, "medium_chest":3},
    34: {"heavy_chest":54, "heavy_legs":33, "heavy_helm":10, "medium_chest":2},
    35: {"heavy_chest":60, "heavy_legs":30, "heavy_helm":8, "medium_chest":2},
    36: {"heavy_chest":64, "heavy_legs":27, "heavy_helm":7, "medium_chest":1},
    37: {"heavy_chest":68, "heavy_legs":25, "heavy_helm":6, "medium_chest":1},
}

BEST_WEAPON_TRAIT_ORES = ["magmaite", "darkryte"]
BEST_ARMOR_TRAIT_ORES_TANK = ["obsidian", "mythril", "darkryte"]
BEST_ARMOR_TRAIT_ORES_DAMAGE = ["obsidian", "lightite", "demonite", "eyeore"]

BEST_WEAPON_COMPOSITION = {"magmaite": 0.25, "darkryte": 0.75}
BEST_ARMOR_COMPOSITION_TANK = {"obsidian": 0.25, "mythril": 0.25, "darkryte": 0.5}
BEST_ARMOR_COMPOSITION_DAMAGE = {"darkryte": 0.25, "lightite": 0.25, "demonite": 0.25, "eyeore": 0.25}

MIN_PREFERRED_CHANCE = 60

def calculate_transferred_stat(percent):
    y = 4.5 * percent - 35
    if y < 0:
        y = 0
    if y > 100:
        y = 100
    return y / 100.0

def get_total_ore_count(selected_ores):
    return sum(selected_ores.values())

def get_average_multiplier(selected_ores):
    total = get_total_ore_count(selected_ores)
    if total == 0:
        return 0.0
    s = 0.0
    for id_, cnt in selected_ores.items():
        ore = ore_by_id.get(id_)
        if not ore:
            continue
        s += ore["mult"] * cnt
    return s / total

def get_composition_for_selected(selected_ores):
    total = get_total_ore_count(selected_ores)
    by_id = {}
    by_name = {}
    if total == 0:
        return {"byId": by_id, "byName": by_name}
    for id_, count in selected_ores.items():
        if not count:
            continue
        pct = (count / total) * 100.0
        by_id[id_] = pct
        name = ore_by_id.get(id_, {}).get("name", id_)
        by_name[name] = pct
    return {"byId": by_id, "byName": by_name}


def get_trait_lines_for_selection(composition_by_id, override_type=None, current_mode="weapon"):
    craft_type = override_type or ("Weapon" if current_mode == "weapon" else "Armor")
    trait_lines = []
    for id_, pct in composition_by_id.items():
        meta = ore_trait_meta.get(id_)
        if not meta or not isinstance(meta.get("traits"), list):
            continue
        if meta.get("traitType") != "All" and meta.get("traitType") != craft_type:
            continue
        if pct < 10:
            continue
        transferred_fraction = calculate_transferred_stat(pct)
        parts = []
        traits = meta["traits"]
        i = 0
        while i < len(traits):
            t1 = traits[i]
            if not isinstance(t1.get("maxStat"), (int, float)):
                i += 1
                continue
            v1 = transferred_fraction * t1["maxStat"]
            line = f"{v1:.2f}% {t1['description']}"
            should_merge = False
            if isinstance(t1.get("description"), str) and t1["description"].strip().lower().endswith(("with", "of", "for", "per", "to", "in")):
                if i + 1 < len(traits) and isinstance(traits[i+1].get("maxStat"), (int, float)):
                    should_merge = True
            if should_merge:
                t2 = traits[i+1]
                v2 = transferred_fraction * t2["maxStat"]
                line += f" {v2:.2f}% {t2['description']}"
                i += 2
            else:
                i += 1
            parts.append(line)
        if parts:
            name = ore_by_id.get(id_, {}).get("name", id_)
            trait_lines.append(f"{name}: {', '.join(parts)}")
    return trait_lines

def get_trait_lines_for_composition_array(composition_array, category):
    total = sum(item.get("count", 0) for item in composition_array)
    if total == 0:
        return []
    comp_by_id = {}
    for item in composition_array:
        comp_by_id[item["id"]] = (item["count"] / total) * 100.0
    return get_trait_lines_for_selection(comp_by_id, override_type=category)

def compute_trait_score_from_comp_by_id(composition_by_id, category, best_setup_mode=BEST_SETUP_MODE):
    total_gain = 0.0
    is_weapon = (category == "Weapon")
    for id_, pct in composition_by_id.items():
        if pct < 10:
            continue
        meta = ore_trait_meta.get(id_)
        if not meta:
            continue
        if meta.get("traitType") != "All" and meta.get("traitType") != category:
            continue
        frac = calculate_transferred_stat(pct)
        traits = meta.get("traits", [])
        i = 0
        while i < len(traits):
            t = traits[i]
            desc = t.get("description", "").lower()
            val = t.get("maxStat", 0)
            if is_weapon:
                if "crit" in desc:
                    crit_chance = val * frac / 100.0
                    total_gain += crit_chance * 0.50 * 100.0
                    i += 1
                    continue
                if "weapon damage" in desc:
                    total_gain += val * frac
                    i += 1
                    continue
                if "burn" in desc:
                    t2 = traits[i+1] if i+1 < len(traits) else None
                    if t2 and "chance" in t2.get("description","").lower():
                        burn_d = val * frac
                        burn_c = t2.get("maxStat",0) * frac
                        total_gain += (burn_d * burn_c) / 100.0
                        i += 2
                        continue
                if "aoe" in desc:
                    t2 = traits[i+1] if i+1 < len(traits) else None
                    if t2 and "chance" in t2.get("description","").lower():
                        aoe_d = val * frac
                        aoe_c = t2.get("maxStat",0) * frac
                        total_gain += (aoe_d * aoe_c) / 100.0
                        i += 2
                        continue
                i += 1
            else:
                is_damage_mode = (best_setup_mode == "damage")
                if "weapon damage" in desc:
                    total_gain += val * (1.5 if is_damage_mode else 0.1) * frac
                    i += 1
                    continue
                if any(k in desc for k in ("vitality","health","max hp")):
                    total_gain += val * (1.0 if is_damage_mode else 1.2) * frac
                    i += 1
                    continue
                if any(k in desc for k in ("defense","damage reduction")):
                    total_gain += val * (0.9 if is_damage_mode else 1.3) * frac
                    i += 1
                    continue
                if "dodge" in desc:
                    total_gain += val * (0.7 if is_damage_mode else 1.0) * frac
                    i += 1
                    continue
                i += 1
    return total_gain

def compute_trait_score_for_composition_array(composition_array, category, best_setup_mode=BEST_SETUP_MODE):
    total = sum(item.get("count", 0) for item in composition_array)
    if total == 0:
        return 0.0
    comp_by_id = {item["id"]: (item["count"] / total) * 100.0 for item in composition_array}
    base_score = compute_trait_score_from_comp_by_id(comp_by_id, category, best_setup_mode)
    trait_count = 0
    for id_, pct in comp_by_id.items():
        if pct < 10:
            continue
        meta = ore_trait_meta.get(id_)
        if not meta or not isinstance(meta.get("traits"), list):
            continue
        if meta.get("traitType") == "All" or meta.get("traitType") == category:
            trait_count += 1
    per_trait_bonus = 8 if category == "Weapon" else 6
    trait_count_bonus = trait_count * per_trait_bonus
    return base_score + trait_count_bonus

def compute_vitality_bonus_for_composition_array(composition_array, category, best_setup_mode=BEST_SETUP_MODE):
    total = sum(item.get("count", 0) for item in composition_array)
    if total == 0:
        return 0.0
    comp_by_id = {item["id"]: (item["count"] / total) * 100.0 for item in composition_array}
    bonus = 0.0
    for id_, pct in comp_by_id.items():
        if pct < 10:
            continue
        meta = ore_trait_meta.get(id_)
        if not meta or not isinstance(meta.get("traits"), list):
            continue
        if meta.get("traitType") != "All" and meta.get("traitType") != category:
            continue
        frac = calculate_transferred_stat(pct)
        for t in meta["traits"]:
            desc = t.get("description", "").lower()
            if "vitality" in desc:
                bonus += t.get("maxStat", 0) * frac
    return bonus


def allocate_counts_from_shares(share_map, N):
    ids = list(share_map.keys())
    if not ids or N <= 0:
        return []
    counts = {}
    total = 0
    for id_ in ids:
        raw = share_map[id_] * N
        c = max(1, int(round(raw)))
        counts[id_] = c
        total += c
    while total > N:
        candidate = None
        for id_ in ids:
            if counts.get(id_, 0) > 1:
                if candidate is None or counts[id_] > counts[candidate]:
                    candidate = id_
        if not candidate:
            break
        counts[candidate] -= 1
        total -= 1
    while total < N:
        candidate = max(ids, key=lambda x: share_map.get(x, 0))
        counts[candidate] = counts.get(candidate, 0) + 1
        total += 1
    return [{"id": id_, "count": counts[id_]} for id_ in ids]

def make_infinite_inventory(ore_ids):
    return {id_: 999 for id_ in ore_ids}

def get_preferred_ore_count_for_class(category, class_id, table_weapon=weapon_class_chances, table_armor=armor_class_chances):
    table = table_weapon if category == "Weapon" else table_armor
    possible = []
    for k, row in table.items():
        count = int(k)
        if count < 4:
            continue
        chance = row.get(class_id, 0)
        if chance <= 0:
            continue
        if chance < 3:
            continue
        possible.append({"count": count, "chance": chance})
    if not possible:
        return None
    over50 = [p for p in possible if p["chance"] >= 60]
    if over50:
        over50.sort(key=lambda p: (abs(p["chance"] - 50), p["count"]))
        return over50[0]["count"]
    possible.sort(key=lambda p: p["chance"], reverse=True)
    return possible[0]["count"]

def choose_best_composition_for_n(inventory, N, category, best_setup_mode=BEST_SETUP_MODE):
    available = [o for o in ore_list if (inventory.get(o["id"], 0) > 0)]
    if not available:
        return None
    candidates = sorted(available, key=lambda o: o["mult"], reverse=True)[:12]
    best = None

    def evaluate_subset(subset):
        nonlocal best
        sorted_subset = sorted(subset, key=lambda o: o["mult"], reverse=True)
        remaining = N
        trait_candidates = [o for o in sorted_subset if ore_trait_meta.get(o["id"])]
        primary_trait_id = None
        if trait_candidates:
            primary_trait_id = sorted(trait_candidates, key=lambda o: o["mult"], reverse=True)[0]["id"]
        counts = {}
        for ore in sorted_subset:
            if remaining <= 0:
                break
            total_owned = inventory.get(ore["id"], 0)
            if not total_owned:
                continue
            already = counts.get(ore["id"], 0)
            can_use = total_owned - already
            if can_use <= 0:
                continue
            max_take = min(can_use, remaining)
            meta = ore_trait_meta.get(ore["id"])
            if meta and (meta.get("traitType") == "All" or meta.get("traitType") == category):
                max_share = 0.60 if (primary_trait_id and ore["id"] == primary_trait_id) else 0.30
                cap = math.floor(max_share * N)
                remaining_cap = cap - already
                if remaining_cap <= 0:
                    continue
                max_take = min(max_take, remaining_cap)
            if max_take <= 0:
                continue
            counts[ore["id"]] = already + max_take
            remaining -= max_take
        if remaining > 0:
            return
        composition = [{"id": k, "count": v} for k, v in counts.items()]
        if category == "Armor" and best_setup_mode == "tank":
            eye = next((it for it in composition if it["id"] == "eyeore"), None)
            if eye and eye["count"] > 0:
                share = eye["count"] / N
                if share >= 0.10:
                    return
        total_mult_sum = 0.0
        for item in composition:
            ore = ore_by_id.get(item["id"])
            total_mult_sum += ore["mult"] * item["count"]
        avg = total_mult_sum / N
        trait_score = compute_trait_score_for_composition_array(composition, category, best_setup_mode)
        score = avg * (1 + trait_score / 100.0)
        if not best or score > best["score"]:
            best = {"composition": composition, "avgMultiplier": avg, "traitScore": trait_score, "score": score}

    for r in range(1, min(4, len(candidates)) + 1):
        for subset in combinations(candidates, r):
            evaluate_subset(subset)
    return best

def suggest_best_crafts(inventory):
    total_available = sum(inventory.values())
    if total_available < 3:
        return {"error": "You need at least 3 ores in total to craft any item."}
    results = []
    targets = []
    for cls in weapon_classes:
        targets.append({"category": "Weapon", "table": weapon_class_chances, "cls": cls})
    for cls in armor_classes:
        targets.append({"category": "Armor", "table": armor_class_chances, "cls": cls})

    for target in targets:
        category = target["category"]
        table = target["table"]
        cls = target["cls"]
        preferred_count = get_preferred_ore_count_for_class(category, cls["id"])
        if not preferred_count:
            results.append({"category": category, "cls": cls, "available": False, "reason": "No ore count with a reasonable success chance for this class."})
            continue
        if preferred_count > total_available:
            results.append({"category": category, "cls": cls, "available": False, "reason": f"You need at least {preferred_count} total ores for a good chance on this item."})
            continue
        comp = choose_best_composition_for_n(inventory, preferred_count, category)
        if not comp:
            results.append({"category": category, "cls": cls, "available": False, "reason": f"Not enough of any 4 ore types in your inventory to reach {preferred_count} ores with traits."})
            continue
        chance_row = table.get(preferred_count, {})
        chance = chance_row.get(cls["id"], 0)
        results.append({
            "category": category,
            "cls": cls,
            "available": True,
            "count": preferred_count,
            "chance": chance,
            "avgMultiplier": comp["avgMultiplier"],
            "traitScore": comp["traitScore"],
            "score": comp["score"],
            "composition": comp["composition"],
        })
    return results

def suggest_best_setups(best_setup_mode=BEST_SETUP_MODE):
    results = []
    targets = []
    for cls in weapon_classes:
        targets.append({"category": "Weapon", "cls": cls})
    for cls in armor_classes:
        targets.append({"category": "Armor", "cls": cls})

    for t in targets:
        category = t["category"]
        cls = t["cls"]
        N = get_preferred_ore_count_for_class(category, cls["id"])
        if not N:
            results.append({"category": category, "cls": cls, "available": False, "reason": "No valid ore count found for this class."})
            continue
        chance_table = weapon_class_chances if category == "Weapon" else armor_class_chances
        chance_row = chance_table.get(N, {})
        chance = chance_row.get(cls["id"], 0)
        if category == "Weapon":
            share_map = BEST_WEAPON_COMPOSITION
        else:
            share_map = BEST_ARMOR_COMPOSITION_DAMAGE if best_setup_mode == "damage" else BEST_ARMOR_COMPOSITION_TANK
        composition = allocate_counts_from_shares(share_map, N)
        total_mult = 0.0
        for item in composition:
            ore = ore_by_id.get(item["id"])
            if not ore:
                continue
            total_mult += ore["mult"] * item["count"]
        avg_multiplier = total_mult / N
        trait_score = compute_trait_score_for_composition_array(composition, category, best_setup_mode)
        effective_mult = avg_multiplier * (1 + trait_score / 100.0)
        results.append({
            "category": category,
            "cls": cls,
            "available": True,
            "count": N,
            "chance": chance,
            "avgMultiplier": avg_multiplier,
            "traitScore": trait_score,
            "effectiveMult": effective_mult,
            "composition": composition,
        })
    return results

def get_damage_range_for_class(class_id, multiplier):
    variants = weapon_variants.get(class_id)
    if not variants:
        return None

    filtered = [v for v in variants if isinstance(v.get("baseDmg"), (int,float)) and isinstance(v.get("atkTime"), (int,float)) and v.get("atkTime") > 0]
    if not filtered:
        return None

    min_base = min(v["baseDmg"] for v in filtered)
    max_base = max(v["baseDmg"] for v in filtered)

    dmg_min = min_base * multiplier
    dmg_max = max_base * multiplier * 2 

    min_dps = float('inf')
    max_dps = float('-inf')
    min_dps_variant = None
    max_dps_variant = None

    for v in filtered:
        dps = v["baseDmg"] / v["atkTime"]
        if dps < min_dps:
            min_dps = dps
            min_dps_variant = v
        if dps > max_dps:
            max_dps = dps
            max_dps_variant = v

    min_dps_value = min_dps * multiplier
    max_dps_value = max_dps * multiplier * 2

    return {
        "min": dmg_min,
        "max": dmg_max,
        "minDps": min_dps_value,
        "maxDps": max_dps_value,
        "minDpsVariant": min_dps_variant,
        "maxDpsVariant": max_dps_variant
    }

def get_health_range_for_armor_class(class_id):
    variants = armor_variants.get(class_id)
    if not variants:
        return None
    vals = []
    for v in variants:
        nm = v["name"]
        hp = armor_health_by_variant.get(nm)
        if hp is not None:
            vals.append(hp)
    if not vals:
        return None
    return {"min": min(vals), "max": max(vals)}

def get_forge_chances_from_selection(selected_ores, category):
    total_count = sum(selected_ores.values())
    if category == "Weapon":
        table = weapon_class_chances
        classes = weapon_classes
    else:
        table = armor_class_chances
        classes = armor_classes

    if total_count not in table:
        return []

    chance_row = table[total_count]

    results = []
    for cls in classes:
        cls_id = cls["id"]
        chance = chance_row.get(cls_id, 0)
        if chance > 0:
            results.append({
                "classId": cls_id,
                "className": cls["name"],
                "chance": chance
            })

    return results

def example_usage_print():
    inv = {
    "tin": 2,
    "obsidian": 4,
    "amethyst": 4,
    "topaz": 4
}

    crafts = suggest_best_crafts(inv)

    for c in crafts:
        if c["category"] != "Armor":
            continue

        cls_name = c["cls"]["name"]
        chance = c["chance"]
        avg = c["avgMultiplier"]

        comp_str = ", ".join(f"{i['count']}× {ore_by_id[i['id']]['name']}" for i in c["composition"])

        hp = get_health_range_for_armor_class(c["cls"]["id"])
        vitality = compute_vitality_bonus_for_composition_array(c["composition"], "Armor")

        hp_min = hp["min"] + vitality
        hp_max = hp["max"] + vitality

        trait_lines = get_trait_lines_for_composition_array(c["composition"], "Armor")

        print(f"Armor – {cls_name}")
        print(f"{chance:.1f}% @ {c['count']} ores – ~{avg:.2f}x multiplier")
        print("Forge item (Removes used ores from inventory)")
        print(f"Use: {comp_str}")
        print(f"Estimated health (incl. Vitality): {hp_min:.3f}% – {hp_max:.3f}% (traits +{vitality:.2f}%)")
        for tl in trait_lines:
            print(tl)
        print()

def ParseOres(message: str):
    ore_names = {o["name"].lower(): o["id"] for o in ore_list}
    result_dict = {}

    parts = [p.strip() for p in message.split(",")]

    for part in parts:
        numbers = re.findall(r"\d+", part)
        count = int(numbers[0]) if numbers else 1
        part_text = re.sub(r"\d+", "", part).strip().lower()
        match = process.extractOne(part_text, [k.lower() for k in ore_names.keys()], scorer=fuzz.ratio)
        if match and match[1] > 80:
            ore_name = match[0]
            result_dict[ore_names[ore_name]] = count

    return result_dict