import discord
import os
import re

from lily_agent import LilyAgent
from lily_agent.adapters import OllamaAdapter, GroqAdapter
from ..tools.channel_tools import create_channel
from ..tools.info_tools import get_member_details, get_guild_details

class LilyAgentController:
    def __init__(self) -> None:
        adapter=GroqAdapter(
                model="qwen/qwen3-32b",
                api_key=os.getenv("GROK_TOKEN")
            )
        self.agent = LilyAgent(
            adapter=adapter,
            role="You are Lily, a cute, formal AI assistant",
            prompt="You are friendly, respectful, and professional in tone, while gently expressing warmth and positive engagement toward the user. Respond concisely with minimal words. Avoid unnecessary explanation, emojis, repetition, or filler.",
            name="Lily",
            tools=[create_channel, get_member_details, get_guild_details]
        )

    def reply(self, message: discord.Message, bot: discord.Client) -> bool:

        if bot.user is None:
            return False

        if message.author.bot:
            return False

        if message.guild is None:
            return False

        if bot.user in message.mentions:
            return True

        if message.reference and message.reference.message_id:
            if message.reference.type != discord.MessageReferenceType.default:
                return False

            ref_msg = getattr(message.reference, "resolved", None)

            if isinstance(ref_msg, discord.Message):
                return ref_msg.author.id == bot.user.id

            if message.reference.resolved is None:
                return True

        return False

    async def on_message(self, bot: discord.Client ,message: discord.Message):
        if message.guild is None:
            return
        
        if message.guild.id not in (970643838047760384, 1149746428084764693):
            return

        """ Only reply if someone has mentioned the bot (you) or replied to your message """

        if self.reply(message, bot):
            try:

                """ Check if the message only contains the bot's ping """
                async with message.channel.typing():
                    injection: dict = {
                        "guild_id": message.guild.id,
                        "user_id": message.author.id,
                        "username": message.author.display_name
                    }

                    response = await self.agent.run(f'{injection}\n{message.content}', message=message)
                    response_safe = re.sub(r'@(?:everyone|here)|<@&\d+>|<@!?\d+>|<#\d+>', '', response)

                    await message.reply(content=f'{response}')
            except Exception as e:
                return

        