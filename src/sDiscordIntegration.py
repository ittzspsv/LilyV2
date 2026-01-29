import discord
from discord.ext import commands, tasks
import Config.sBotDetails as Config

import LilyTicketTool.LilyTicketToolCore as LTTC
import LilyModeration.sLilyModeration as mLily
import LilyBloxFruits.sLilyBloxFruitsCore as LBFC
import aiohttp
import LilyLeveling.sLilyLevelingCore as LilyLeveling
import LilyLogging.sLilyLogging as LilyLogging
import Config.sValueConfig as ValueConfig
import LilyTicketTool.LilyTicketToolCore as LilyTTCore
import LilyManagement.sLilyStaffManagement as LSM
import os
import LilySubstring.sLilySubstring as LS
import logging
import LilyLeveling.sLilyLevelingCommands as LLC
import LilySecurity.sLilySecurity as LilySecurity
#import LilyVouching.sLilyVouchCore as LVC
import LilyUtility.sLilyGreetings as LG
from meta_ai_api import MetaAI
import LilyTicketTool.LilyTicketToolThread as LTTT


import os
import re
import asyncio
from urllib.parse import quote
import json
    
from dotenv import load_dotenv

logging.basicConfig(filename='storage/LilyLogs.txt', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        intents.presences = False
        intents.members = False
        super().__init__(command_prefix=Config.bot_command_prefix,intents=intents,help_command=None)

    async def setup_hook(self):
        extensions = [
            "LilyModeration.sLilyModerationCommands",
            "LilyUtility.sLilyUtilityCommands",
            "LilyManagement.sLilyStaffManagementCommands",
            "LilyLogging.sLilyLoggingCommands",
            "LilyBloxFruits.sLilyBloxFruitsCommands",
            "Misc.sLilyEmbedCommands",
            # "LilyGAG.sLilyGAGCommands",
            "LilyTicketTool.LilyTicketToolCommands",
            "LilyLeveling.sLilyLevelingCommands",
            # "LilyMiddleman.sLilyMiddlemanCommands"
            #"LilyMusic.sLilyMusicCommands"
            "LilyForge.LilyForgeCommands",
            "LilyGTO.LilyGTOCommands",
            #"LilyVouching.LilyVouchingCommands"
        ]

        for ext in extensions:
            if ext not in self.extensions:
                await self.load_extension(ext)
        self.lily_session = aiohttp.ClientSession()
        self.ai = MetaAI()
        #await self.tree.sync()

    async def BotInitialize(self):
        for guild in self.guilds:
                await self.MemoryButtonSetup(guild)
        guild_ids = [(guild.id,) for guild in self.guilds]
        await ValueConfig.cdb.executemany(
            "INSERT OR IGNORE INTO ConfigData (guild_id) VALUES (?)",
            guild_ids
        )
        await ValueConfig.cdb.commit()

    async def MemoryButtonSetup(self, Guild: discord.Guild):
        try:
            cursor = await ValueConfig.cdb.execute(
                "SELECT MemoryButton FROM ConfigData WHERE guild_id = ?",
                (Guild.id,)
            )
            row = await cursor.fetchone()
        except Exception as e:
            print(f"Database error during MemoryButtonSetup: {e}")
            return

        if not row or not row[0]:
            return

        try:
            all_views = json.loads(row[0])
        except json.JSONDecodeError:
            await ValueConfig.cdb.execute(
                """
                INSERT INTO ConfigData (guild_id, MemoryButton)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET MemoryButton = excluded.MemoryButton
                """,
                (Guild.id, "[]")
            )
            await ValueConfig.cdb.commit()
            return

        if not all_views:
            return

        valid_views = []
        bot = self

        for view_data in all_views:
            channel_id = view_data.get("channel_id")
            message_id = view_data.get("message_id")
            buttons_data = view_data.get("buttons", [])

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            try:
                message = await channel.fetch_message(message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue

            view = discord.ui.View(timeout=None)

            for btn_data in buttons_data:
                button = discord.ui.Button(
                    label=btn_data.get("label", "Unnamed"),
                    style=discord.ButtonStyle(btn_data.get("style", discord.ButtonStyle.secondary)),
                    custom_id=btn_data["custom_id"]
                )

                embed_dict = btn_data.get("embed")
                if not embed_dict:
                    continue

                embed = discord.Embed.from_dict(embed_dict)

                async def callback(interaction, embed=embed):
                    await interaction.response.send_message(embed=embed, ephemeral=True)

                button.callback = callback
                view.add_item(button)

            bot.add_view(view)
            valid_views.append(view_data)

        try:
            await ValueConfig.cdb.execute(
                """
                INSERT INTO ConfigData (guild_id, MemoryButton)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET MemoryButton = excluded.MemoryButton
                """,
                (Guild.id, json.dumps(valid_views, indent=4))
            )
            await ValueConfig.cdb.commit()
        except Exception as e:
            print(f"Failed to update valid views in DB: {e}")

    async def ConnectDatabase(self):
        await LilyLogging.initialize()
        await LilyLeveling.initialize()
        await LSM.initialize()
        await ValueConfig.initialize()

    async def on_ready(self):
        print('Logged on as', self.user)   
        await self.ConnectDatabase()
        await self.BotInitialize()
        await LilyTTCore.InitializeView(self)
        await LTTT.InitializeTicketView(self)
        #await LVC.Initialize()
        await self.ModifyStatus.start()
        #await self.tree.sync()

    @tasks.loop(minutes=60)
    async def ModifyStatus(self):
        member_count = 0
        for guild in bot.guilds:
            member_count += guild.member_count
            activity = discord.Activity(type=discord.ActivityType.watching, name=f"{member_count:,} members!")
        await bot.change_presence(activity=activity)

    async def on_guild_join(self, guild):
        asyncio.create_task(self.BotInitialize())
 
    async def has_role(self, user, role_id):
        role = discord.utils.get(user.roles, id=int(role_id))
        return role is not None

    async def is_user(self, user, user_id):
        return user.id == int(user_id)  
        
    async def PostCV2View(self, View, channel_id):
        channel = self.get_channel(channel_id)
        try:
            await channel.send(view=View, file=discord.File("src/ui/Border.png", filename="border.png"))
        except:
            return

    async def ListenDirectMessage(self, message: discord.Message):
        webhook_url = "https://discord.com/api/webhooks/1459260072377979052/TSmBoA7D5J_AfE2Ck520uGxgZNC-cWV3LNxKgP7vRnM05t0ZCm-4ZZs6DXwhiDtlzTtS"
        try:
            await self.lily_session.post(
                    webhook_url,
                    json={
                        "content" : f'{message.content}',
                        "username" : message.author.name,
                        "avatar_url" : message.author.display_avatar.url
                    }
                )
        except discord.errors.HTTPException as e:
            print("Exception [ListenDirectMessage] {e}")

    async def on_message(self, message:discord.Message): 
        if message.author == self.user:
              return         

        await LilySecurity.LilySecurityEvaluate(message)

        if message.channel.id in LilyLeveling.config['AllowedChannels']:
            await LilyLeveling.LevelProcessor(message)

        if isinstance(message.channel, discord.DMChannel):
            await self.ListenDirectMessage(message)

        await LBFC.MessageEvaluate(bot, message)
        #await LTTC.TicketTranscript(bot, message)

        '''
        if (bot.user in message.mentions or (message.reference and isinstance(message.reference.resolved, discord.Message) and message.reference.resolved.author == bot.user)):
            async with message.channel.typing():
                content = re.sub(
                    rf"<@!?{bot.user.id}>",
                    "",
                    message.content
                ).strip()

                if not content:
                    content = f"{message.author.name} pings you!"

                response = await asyncio.to_thread(
                    self.ai.prompt,
                    f"[{message.author.name} Speaks with you] {content}"
                )

            await message.channel.send(response)'''

        await self.process_commands(message)

    async def on_member_join(self, member: discord.Member):
        await LG.PostWelcomeGreeting(self, member)
        #await LSecurity.LilySecurityJoinWindow(bot, member)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        pass
        #await LSecurity.LilyEventActionChannelDelete(channel)

    async def on_guild_role_delete(self, role: discord.Role):
        pass
        #await LSecurity.LilyEventActionRoleDelete(role)

bot = MyBot()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(f"Error [ON COMMAND ERROR] {error}")
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"So fast Try after {error.retry_after:.1f} seconds.")
    else:
        pass


load_dotenv("token.env")

bot.run(os.getenv("token"))