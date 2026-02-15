'''
Cache stores all the information  of the items on the memory for fast lookup.  
You may disable this cache if you want to fetch items manually from database, but that would reduce the speed.
'''

import aiosqlite
import asyncio
import ast
from typing import Dict, Set, List, Union


'''GLOBAL ATTRIBUTES'''
item_dict: Dict = {}
item_list_minimal: List[Dict[str, Union[str, int]]] = []
fruit_names: Set = set()
fruit_names_sorted: List = []
alias_map: Dict = {}
fruit_set: Set = set()
category_map = {
        'common': 1,
        'uncommon': 2,
        'rare': 3,
        'legendary': 4,
        'mythical': 5,
        'gamepass': 6
    }
name_to_category = {}

async def initialize():
    global item_dict, fruit_names, alias_map
    global fruit_names_sorted, fruit_set, name_to_category, item_list_minimal

    conn = await aiosqlite.connect("storage/configs/ValueData.db")
    cursor = await conn.cursor()

    await cursor.execute("SELECT * FROM BF_ItemValues")
    rows = await cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]

    item_dict = {}

    fruit_names.clear()
    alias_map.clear()
    item_list_minimal.clear()
    name_to_category.clear()

    for row in rows:
        row_data = dict(zip(columns, row))

        aliases = row_data.get("aliases")
        if aliases:
            try:
                aliases = ast.literal_eval(aliases)
                if not isinstance(aliases, list):
                    aliases = []
            except (ValueError, SyntaxError):
                aliases = []
        else:
            aliases = []

        row_data["aliases"] = aliases

        name = row_data.get("name")
        if not name:
            continue

        name_lower = name.lower()
        category_lower = (row_data.get("category") or "").lower()

        phys_val = row_data.get("physical_value") or 0
        perm_val = row_data.get("permanent_value") or 0

        item_dict[name] = row_data
        fruit_names.add(name_lower)
        name_to_category[name_lower] = category_lower

        for alias in aliases:
            if alias:
                alias_map[alias.lower()] = name_lower

        item_list_minimal.append({
            "name": name,
            "name_lower": name_lower,    
            "category": category_lower,     
            "physical_value": phys_val,
            "permanent_value": perm_val
        })

    await cursor.close()
    await conn.close()

    fruit_names_sorted = sorted(fruit_names, key=len, reverse=True)
    fruit_set = set(fruit_names_sorted)
