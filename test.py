import sqlite3

db = sqlite3.connect("storage/logs/Logs.db")

db.execute("""
           CREATE INDEX IF NOT EXISTS idx_modlogs_cooldown
ON modlogs (guild_id, moderator_id, mod_type, timestamp);
""")
db.commit()
