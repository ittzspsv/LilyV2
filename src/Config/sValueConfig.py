import asyncio
import aiosqlite

vdb = None
async def initialize():
    global vdb
    vdb = await aiosqlite.connect("src/Config/JSONData/ValueData.db")