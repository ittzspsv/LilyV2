import aiosqlite
import asyncio

from typing import Optional, Dict

vdb = None
cdb = None
combo_db = None

# Structure
guild_configs: Dict[int, Dict[str, Dict[str, int]]] = {}

async def initialize() -> None:
    global vdb, cdb, combo_db
    vdb = await aiosqlite.connect("storage/configs/ValueData.db")
    cdb = await aiosqlite.connect("storage/configs/Configs.db")
    combo_db = await aiosqlite.connect("storage/configs/ComboData.db")

async def initialize_cache() -> None:
    await initialize()
    global guild_configs

    cursor = await cdb.execute("""
        SELECT c.guild_id, cc.*
        FROM ConfigData AS c
        LEFT JOIN ConfigChannels AS cc
            ON c.channel_config_id = cc.channel_config_id
    """)

    rows = await cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    for row in rows:
        row_dict = dict(zip(columns, row))
        
        guild_id = row_dict.pop("guild_id")

        row_dict.pop("channel_config_id", None)

        channels = {
            column: value
            for column, value in row_dict.items()
            if value is not None
        }

        guild_configs[guild_id] = {
            "channels": channels
        }

asyncio.run(initialize_cache())