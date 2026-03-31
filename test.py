import sqlite3
import json

conn = sqlite3.connect("storage/configs/ValueData.db")
conn.row_factory = sqlite3.Row

cursor = conn.cursor()
cursor.execute("SELECT * FROM BF_ItemValues")

rows = cursor.fetchall()

data = [dict(row) for row in rows]

with open("Values.json", "w") as f:
    json.dump(data, f, indent=4)

conn.close()