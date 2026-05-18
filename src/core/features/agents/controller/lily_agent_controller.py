import discord
import os
import re

from lily_agent import LilyAgent
from lily_agent.adapters import OllamaAdapter, GroqAdapter
from ..tools.channel_tools import create_channel
from ..tools.info_tools import get_member_details, get_guild_details
from ..tools.role_tools import create_role
from ..tools.global_tools import *

from ..data.overload_data import OverloadData

class LilyAgentController:
    def __init__(self) -> None:
        '''
        adapter=GroqAdapter(
                model="qwen/qwen3-32b",
                api_key=os.getenv("GROK_TOKEN")
            )
        '''
        
        adapter = OllamaAdapter(model="qwen3.5:4b")

        self.agent = LilyAgent(
            adapter=adapter,
            role="You are Lily, a cute, formal AI assistant",
            prompt="You are friendly, respectful, and professional in tone, while gently expressing warmth and positive engagement toward the user. Respond concisely with minimal words. Avoid unnecessary explanation, emojis, repetition, or filler.",
            name="Lily"
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
        
        if message.guild.id not in (970643838047760384, 1149746428084764693, 1489333992338624746):
            return
        
        if message.author.id not in (1488556914605428988, 999309816914792630):
            return

        """ Only reply if someone has mentioned the bot (you) or replied to your message """

        if self.reply(message, bot):
            try:
                """ Extract message flags """
                flags = re.findall(r'(?<!\S)-([A-Za-z])(?!\S)', message.content.upper())
                message_trimmed = re.sub(r'(?<!\S)-([A-Za-z])(?!\S)', '',message.content.upper())

                """ Clear previous tools """
                self.agent.clear_tools()

                """ Dynamically build tools if there are sufficient flags.  Else don't include tools """
                for flag in set(flags):
                    if 'C' == flag:
                        self.agent.register_tool(create_channel)
                    if 'I' == flag:
                        self.agent.register_tool([get_member_details, get_guild_details])

                    if 'R' in flag:
                        self.agent.register_tool(create_role)

                    if 'G' in flag:
                        self.agent.register_tool([get_prefix, set_prefix])

                print(self.agent.tools)

                """ Check if the message only contains the bot's ping """
                async with message.channel.typing():
                    injection: dict = {
                        "guild_id": message.guild.id,
                        "user_id": message.author.id,
                        "username": message.author.display_name
                    }
                    try:
                        response = await self.agent.run(f'{injection}\n{message_trimmed}', data=OverloadData(message, bot))
                        response_safe = re.sub(r'@(?:everyone|here)|<@&\d+>|<@!?\d+>|<#\d+>', '', response)
                    except Exception as e:
                        print(e)

                    await message.reply(content=f'{response_safe}')
            except Exception as e:
                return

        