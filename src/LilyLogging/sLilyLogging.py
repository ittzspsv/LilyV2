from datetime import datetime

from discord.ext import commands
import polars as pl
import os

async def WriteLog(ctx: commands.Context, user_id, log_txt):
        log_file_path = f"storage/{ctx.guild.id}/botlogs/logs.csv"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_log = pl.DataFrame({
            "user_id": [str(user_id)],
            "timestamp": [timestamp],
            "log": [log_txt]
        })

        if os.path.exists(log_file_path):
            existing_logs = pl.read_csv(log_file_path)

            new_log = new_log.cast(existing_logs.schema)

            updated_logs = pl.concat([existing_logs, new_log], how="vertical")
        else:
            updated_logs = new_log

        updated_logs.write_csv(log_file_path)