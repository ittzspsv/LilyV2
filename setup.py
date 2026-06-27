""" Create a fresh sqlite database using the schema """

import sqlite3

conn = sqlite3.connect("storage/configs/NewConfigs.db",)

with open("Configs_schema.sql", "r", encoding="utf-8") as f:
    schema = f.read()
conn.executescript(schema)
conn.close()
    