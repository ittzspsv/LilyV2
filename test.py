import sqlite3

db = sqlite3.connect("storage/configs/Configs.db")
bdb = sqlite3.connect("storage/configs/BackupConfigs.db")

db_cursor = db.cursor()
bdb_cursor = bdb.cursor()

# ---------- fetch old data ----------
bdb_cursor.execute("""
    SELECT
        guild_id,
        bf_win_loss_channel_id,
        bf_fruit_value_channel_id,
        bf_combo_channel_id,
        logs_channel,
        welcome_channel
    FROM ConfigData
""")

rows = bdb_cursor.fetchall()

# ---------- migrate ----------
for row in rows:
    (
        guild_id,
        win_loss,
        fruit_value,
        combo,
        logs,
        welcome,
    ) = row

    # 1️⃣ insert into ConfigChannels
    db_cursor.execute("""
        INSERT INTO ConfigChannels (
            bf_win_loss_channel_id,
            bf_fruit_value_channel_id,
            bf_combo_channel_id,
            logs_channel,
            welcome_channel
        )
        VALUES (?, ?, ?, ?, ?)
    """, (win_loss, fruit_value, combo, logs, welcome))

    # get generated channel_config_id
    channel_config_id = db_cursor.lastrowid

    # 2️⃣ insert into ConfigData
    db_cursor.execute("""
        INSERT OR REPLACE INTO ConfigData (
            guild_id,
            channel_config_id
        )
        VALUES (?, ?)
    """, (guild_id, channel_config_id))

# ---------- commit ----------
db.commit()

db_cursor.close()
bdb_cursor.close()

db.close()
bdb.close()

print("Migration complete.")
