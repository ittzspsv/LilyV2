import os
from typing import Optional ,List
import aiohttp
import discord
import src.core.configs.sBotDetails as Config
from discord.ext import commands, tasks

from src.core.database.integrations.bot_globals import BotGlobalsDatabaseAccess
from src.core.features.agents.controller.lily_agent_controller import LilyAgentController
from src.core.logging.lily_logging import LilyLoggingController
from src.core.utils.embeds.sLilyEmbed import simple_embed
from src.core.configs.path import CONFIG_DB
from src.api.app import LilyAPI
import uvicorn


class Lily(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() 
        intents.presences = False
        intents.members = False
        intents.message_content = True

        self.lily_session = None
        self.db: Optional[BotGlobalsDatabaseAccess] = None
        self.logging_controller: Optional[LilyLoggingController] = None
        self.agent_controller: LilyAgentController = LilyAgentController()

        super().__init__(command_prefix=self.prefix,intents=intents,help_command=None, owner_ids={1488556914605428988})

    async def start_api(self):
        config = uvicorn.Config(self.api.app, host="0.0.0.0", port=8000, loop="asyncio")
        server = uvicorn.Server(config)
        await server.serve()

    async def setup_hook(self):
        """ Bot Globals Database """
        self.db = await BotGlobalsDatabaseAccess.connect(str(CONFIG_DB))
        self.logging_controller = LilyLoggingController(self.db)

        self.api = LilyAPI(self.db)
        self.loop.create_task(self.start_api())


        extensions = [
            "src.commands.moderation",
            "src.commands.utility",
            "src.commands.blox_fruits",
            "src.commands.management",
            "src.commands.ticket_tool",
            "jishaku"
        ]

        for ext in extensions:
            try:
                if ext not in self.extensions:
                    await self.load_extension(ext)
                    print(f"Loaded {ext}")
            except Exception as e:
                print(f"Load failed {ext}: {e}")

        #self.tree._global_commands.clear()
        #await self.tree.sync()
        await self.tree.sync()
        
    def prefix(self, bot: commands.Bot, message: discord.Message):
        if not message.guild:
            return Config.bot_command_prefix

        if self.db is None:
            return Config.bot_command_prefix

        member_prefix = self.db.get_prefix_member(
            message.author.id,
            message.guild.id
        )

        if member_prefix is not None:
            return member_prefix

        return self.db.get_prefix(message.guild.id)

    async def on_ready(self):
        print('Logged on as', self.user)
        
        await self.modify_status.start()

    async def on_guild_join(self, guild: discord.Guild):
        if self.db is not None:
            await self.db.guild_initialize(guild.id)

    @tasks.loop(minutes=60)
    async def modify_status(self):
        member_count = 0
        for guild in self.guilds:
            member_count += guild.member_count or 0
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"{member_count:,} members!")
        await self.change_presence(activity=activity)

    """ Miscellaneous DM message tracker """
    async def track_direct_messages(self, message: discord.Message):
        if not isinstance(message.channel, discord.DMChannel):
            return
        
        webhook = discord.Webhook.from_url(
            url="https://discord.com/api/webhooks/1516469275936686172/EvIk15kwZH3SQ8ihaDTQsmz6D_kSO_C2Xq2eAjtb3Xd3k3DUrh1NapPi8V7kYFRdvF3h",
            client=self
        )
        await webhook.send(
            content=message.content,
            username=message.author.name,
            avatar_url=message.author.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.none()
        )

    async def on_message(self, message:discord.Message): 
        if message.author == self.user:
              return
        await self.agent_controller.on_message(self, message=message)
        await self.track_direct_messages(message)
        await self.process_commands(message)

    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        if entry.action != discord.AuditLogAction.member_role_update:
            return

        action_user = entry.user_id

        if action_user in (437808476106784770, 235148962103951360, 155149108183695360):
            return

        target = entry._target_id
        before = entry.changes.before
        after = entry.changes.after
        reason = entry.reason

        before_roles = set(r.id for r in (before.roles or []))
        after_roles  = set(r.id for r in (after.roles  or []))

        added_ids   = after_roles - before_roles
        removed_ids = before_roles - after_roles

        guild = entry.guild
        added   = [guild.get_role(rid) for rid in added_ids]
        removed = [guild.get_role(rid) for rid in removed_ids]

        webhook = discord.Webhook.from_url(
            url="https://discord.com/api/webhooks/1518275871323197450/qWGNYE3eqUw5Zu8wjBDiskxC5tGJW4RbfHAnKUwsrBcqt_ncbx7GLMWEI4w8ofVtHnPl",
            client=self
        )

        for role in added:
            await webhook.send(
                username="Lily Auditing",
                avatar_url="https://media.discordapp.net/attachments/1510416807847133274/1518277154889269248/Kaede.png?ex=6a395549&is=6a3803c9&hm=05717257deda03eb05031cc015919b7d622e36098b5e575cc372653060374117&=&format=webp&quality=lossless",
                content = f"{action_user} added role {role.id} to {target}",
                embed = discord.Embed(description=f"<@{action_user}> added role <@&{role.id}> to <@{target}> with reason {reason}"),
                allowed_mentions=discord.AllowedMentions.none()
            )

        for role in removed:
            await webhook.send(
                username="Lily Auditing",
                avatar_url="https://media.discordapp.net/attachments/1510416807847133274/1518277154889269248/Kaede.png?ex=6a395549&is=6a3803c9&hm=05717257deda03eb05031cc015919b7d622e36098b5e575cc372653060374117&=&format=webp&quality=lossless",
                content = f"{action_user} removed role {role.id} from {target}",
                embed = discord.Embed(description=f"<@{action_user}> removed role <@&{role.id}> from <@{target}> with reason {reason}"),
                allowed_mentions=discord.AllowedMentions.none()
            )

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.reply(embed=simple_embed(str(error), 'cross'))

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(embed=simple_embed(f"So fast! Try again after {error.retry_after:.1f} seconds.", 'cross'))
        else:
            pass