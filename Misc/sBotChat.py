import discord
import asyncio
import Config.sBotDetails as BD
CHANNEL_ID = 1345823160951640097

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def send_message(channel_id, message):
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send(message)
    else:
        print("Invalid channel ID")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    asyncio.create_task(input_loop())

async def input_loop():
    while True:
        user_message = input("Enter message to send: ")
        await send_message(CHANNEL_ID, user_message)

client.run(BD.bot_token)


