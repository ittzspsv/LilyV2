import sqlite3

db = sqlite3.connect("storage/configs/ValueData.db")
cursor = db.execute("SELECT * FROM BF_ItemValues")
rows = cursor.fetchall()
print(rows)