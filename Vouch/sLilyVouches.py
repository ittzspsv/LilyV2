import polars as pl
import os
import discord  
import Moderation.sLilyModeration as mLily


from datetime import datetime
from Config.sBotDetails import *
from discord.ext import commands

database = "vouches_database.csv"

def store_vouch(ctx: commands.Context, member: discord.Member, note: str = "", received: str = "", verified: bool = False):

    if not os.path.exists(database):
        df = pl.DataFrame({
            "Member ID": pl.Series([], dtype=pl.Utf8),
            "Receiver ID": pl.Series([], dtype=pl.Utf8),
            "Note": pl.Series([], dtype=pl.Utf8),
            "Received": pl.Series([], dtype=pl.Utf8),
            "Timestamp": pl.Series([], dtype=pl.Utf8),
            "Vouch Count": pl.Series([], dtype=pl.Int64),
            "Experience Days": pl.Series([], dtype=pl.Int64),
            "Verified": pl.Series([], dtype=pl.Boolean)
        })
        df.write_csv(database)
    
    df = pl.read_csv(database, dtypes={
        "Member ID": pl.Utf8,
        "Receiver ID": pl.Utf8,
        "Note": pl.Utf8,
        "Received": pl.Utf8,
        "Timestamp": pl.Utf8,
        "Vouch Count": pl.Int64,
        "Experience Days": pl.Int64,
        "Verified": pl.Boolean
    })
    
    existing_entries = df.filter(df["Member ID"] == str(member.id))
    if len(existing_entries) > 0:
        first_vouch_timestamp = existing_entries["Timestamp"].min()
        experience_days = (datetime.utcnow() - datetime.fromisoformat(first_vouch_timestamp)).days
        vouch_count = existing_entries["Vouch Count"].max() + 1
    else:
        experience_days = 0
        vouch_count = 1
    
    new_entry = pl.DataFrame([
        {
            "Member ID": str(member.id),
            "Receiver ID": str(ctx.author.id),
            "Note": note,
            "Received": received,
            "Timestamp": datetime.utcnow().isoformat(),
            "Vouch Count": vouch_count,
            "Experience Days": experience_days,
            "Verified": verified
        }
    ])
    
    df = pl.concat([df, new_entry], how="vertical")
    
    df.write_csv(database)
    
    embed = discord.Embed(
        title=f"✅ VOUCH FOR: {member.name}",
        description=f"{ctx.author.mention} **vouched** for {member.mention} 🤝",
        colour=0x00E4F5,
        timestamp=datetime.now()
    )

    embed.set_author(name=bot_name, icon_url=bot_icon_link_url)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else "https://example.com/default-avatar.png")

    embed.add_field(name="💰 Received", value=f"**{received}**", inline=False)
    embed.add_field(name="📝 Notes", value=f"_{note}_" if note else "_No additional notes provided._", inline=False)
    embed.add_field(name="🏆 Total Vouches", value=f"**{vouch_count}**", inline=False) 

    return embed

def verify_servicer(member_id: int):
    if not os.path.exists(database):
        print("No vouch records found.")
        return
    
    df = pl.read_csv(database, dtypes={
        "Member ID": pl.Utf8,
        "Receiver ID":pl.Utf8,
        "Note": pl.Utf8,
        "Received": pl.Utf8,
        "Timestamp": pl.Utf8,
        "Vouch Count": pl.Int64,
        "Experience Days": pl.Int64,
        "Verified": pl.Boolean
    })
    
    member_id_str = str(member_id)
    existing_entry = df.filter(df["Member ID"] == member_id_str)
    
    if len(existing_entry) == 0:
        print(f"Member {member_id} not found in vouch records.")
        return
    
    df = df.with_columns(
        pl.when(df["Member ID"] == member_id_str)
        .then(pl.lit(True))
        .otherwise(df["Verified"])
        .alias("Verified")
    )
    
    df.write_csv(database)
    return mLily.SimpleEmbed(f"Service Provider <@{member_id}> has been verified ✅ ")

def unverify_servicer(member_id: int):
    if not os.path.exists(database):
        print("No vouch records found.")
        return
    
    df = pl.read_csv(database, dtypes={
        "Member ID": pl.Utf8,
        "Receiver ID": pl.Utf8,
        "Note": pl.Utf8,
        "Received": pl.Utf8,
        "Timestamp": pl.Utf8,
        "Vouch Count": pl.Int64,
        "Experience Days": pl.Int64,
        "Verified": pl.Boolean
    })
    
    member_id_str = str(member_id)
    existing_entry = df.filter(df["Member ID"] == member_id_str)
    
    if len(existing_entry) == 0:
        print(f"Member {member_id} not found in vouch records.")
        return
    
    df = df.with_columns(
        pl.when(df["Member ID"] == member_id_str)
        .then(pl.lit(False))
        .otherwise(df["Verified"])
        .alias("Verified")
    )
    
    df.write_csv(database)
    return mLily.SimpleEmbed(f"Service Provider <@{member_id}> has been Un-Verified. ")

def display_vouch_embed(member: discord.Member, min=0, max=5):
    if not os.path.exists(database):
        return discord.Embed(
            title=f"{member.name}'s VOUCHES",
            description=f"No Vouches Available {member.mention}.",
            colour=0xFF0000,
            timestamp=datetime.now()
        )

    df = pl.read_csv(database, dtypes={
        "Member ID": pl.Utf8,
        "Receiver ID": pl.Utf8,
        "Note": pl.Utf8,
        "Received": pl.Utf8,
        "Timestamp": pl.Utf8,
        "Vouch Count": pl.Int64,
        "Experience Days": pl.Int64,
        "Verified": pl.Boolean
    })

    member_id_str = str(member.id)
    existing_entry = df.filter(df["Member ID"] == member_id_str)
    filtered = df.filter(pl.col("Member ID") == member_id_str)
    if len(existing_entry) == 0:
        return discord.Embed(
            title=f"{member.name}'s VOUCHES",
            description=f"No Vouches Available {member.mention}.",
            colour=0xFF0000,
            timestamp=datetime.now()
        )

    vouch_count = existing_entry["Vouch Count"].max()
    existing_entry = existing_entry.with_columns(
        pl.col("Timestamp").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.f", strict=False)
    )

    total_vouches = len(existing_entry)
    unique_receivers = existing_entry.select("Receiver ID").unique().height
    trust_percentage = round((unique_receivers / total_vouches) * 100, 2) if total_vouches > 0 else 100.0

    first_vouch_date = existing_entry["Timestamp"].min()
    experience_days = (datetime.now() - first_vouch_date).days
    verified = "✅" if existing_entry["Verified"].max() else "❌"

    recent_vouches = existing_entry.sort("Timestamp", descending=True)[min:max]

    recent_vouches_text = "\n".join([
        f"- {row['Note']} (Received: {row['Received']})" for row in recent_vouches.iter_rows(named=True)
    ]) if len(recent_vouches) > 0 else "No recent vouches."

    embed = discord.Embed(
        title=f"🔹 {member.name}'s Vouches",
        description=f"📜 Vouches for {member.mention}",
        colour=0x00e4f5,
        timestamp=datetime.now()
    )

    embed.set_author(name=bot_name, icon_url=bot_icon_link_url)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else "https://example.com/default_avatar.png")

    embed.add_field(name="🛠 **Vouches**", value=f"{vouch_count}", inline=True)
    embed.add_field(name="📅 **Experience**", value=f"{experience_days} days", inline=True)
    #embed.add_field(name="**Unique Users Vouched**", value=f"{trust_percentage}%", inline=True)
    embed.add_field(name="**Verified**", value=f"{verified}", inline=True)

    embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━", inline=False)

    for idx, row in enumerate(recent_vouches.iter_rows(named=True), start=1):
        if idx > 5:
            break
        dt = datetime.strptime(str(row['Timestamp']), "%Y-%m-%d %H:%M:%S.%f")
        t_formatted = dt.isoformat()
        embed.add_field(
            name=f"✨ Recent Vouch #{idx}",
            value=(
                f"> **👤 Receiver:** <@{row['Receiver ID']}>\n"
                f"> **📆 Received:** {row['Received']}\n"
                f"> **📝 Notes:** {row['Note']}\n\n"
                f"> ** ⏲️ Time:** `{t_formatted}`"
            ),
            inline=False
        )

    return embed

def delete_vouch(member_id: int, timestamp_str: str) -> bool:
    if not os.path.exists(database):
        return False

    df = pl.read_csv(database, dtypes={
        "Member ID": pl.Utf8,
        "Receiver ID": pl.Utf8,
        "Note": pl.Utf8,
        "Received": pl.Utf8,
        "Timestamp": pl.Utf8,
        "Vouch Count": pl.Int64,
        "Experience Days": pl.Int64,
        "Verified": pl.Boolean
    })

    original_len = len(df)

    df = df.filter(~(
        (df["Member ID"] == str(member_id)) & 
        (df["Timestamp"] == timestamp_str)
    ))

    if len(df) == original_len:
        return False

    df.write_csv(database)
    return True