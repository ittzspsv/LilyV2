import asyncio
import aiosqlite

vdb = None
cdb = None
async def initialize():
    global vdb, cdb
    vdb = await aiosqlite.connect("storage/configs/ValueData.db")
    cdb = await aiosqlite.connect("storage/configs/Configs.db")

async def GetRoles(role_names: tuple = ()):
    global cdb
    if not role_names:
        return []

    placeholders = ",".join("?" for _ in role_names)
    query = f"SELECT role_id FROM roles WHERE role_name IN ({placeholders})"
    
    cursor = await cdb.execute(query, role_names)
    rows = await cursor.fetchall()
    return [row[0] for row in rows]