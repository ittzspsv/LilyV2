import aiosqlite
import json
import asyncio

async def main():
    async with aiosqlite.connect("src/Config/JSONData/ValueData.db") as vdb:
        await vdb.execute("""
            CREATE TABLE IF NOT EXISTS GAG_PetMutationData (
                name TEXT PRIMARY KEY,
                value REAL
            )
        """)

        with open("src/LilyGAG/data/GAGPetMutationData.json") as d:
            data = json.load(d)

        records = [(k, float(v)) for k, v in data.items()]

        await vdb.executemany("INSERT OR REPLACE INTO GAG_PetMutationData (name, value) VALUES (?, ?)", records)

        await vdb.commit()
