import aiosqlite
import asyncio

vdb = None
cdb = None
async def initialize():
    global vdb, cdb
    vdb = await aiosqlite.connect("storage/configs/ValueData.db")
    cdb = await aiosqlite.connect("storage/configs/Configs.db")