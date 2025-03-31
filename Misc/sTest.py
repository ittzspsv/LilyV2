import discord
from discord.ext import commands
import asyncio
import random
import Config.sBotDetails as sBotDetails

CHANNEL_ID = 1353459828680298708

user_max_health = 77777777777
victim_max_health = 20

user_health = user_max_health
victim_health = victim_max_health

user_name = ""
victim_name = ""

type = 0

beginning_dialogues = [
    "## A strange Light fills in the <#{channel_id}>",
    "## Twilight is shining through the barrier.",
    "## {user_name} is standing between you and absolute.",
    "## It seems your journey is about to end.",
    "## (You're filled with DETERMINATION.)"
]

beginning_dialogues2 = [
    "## It's a beautiful day outside",
    "## birds are singing",
    "## flowers are blooming.......",
    "## on days like this",
    "## kids like you aka {victim_name}",
]

act_dialogues = [
    ["### You quietly tell {user_name} you don’t want to fight.",  
     "### {user_name}'s hands tremble for a moment.",  
     "### He closes his eyes and takes a deep breath."],

    ["### You firmly tell {user_name} to stop.",  
     "### {user_name} grips his trident tightly.",  
     "### His expression softens for a moment... but he still raises his weapon."],

    ["### You try to talk to {user_name}, but he refuses to respond.",  
     "### He looks away, as if trying to ignore his emotions.",  
     "### But his attacks seem slightly weaker."],

    ["### {victim_name} remembers the happy moments you shared with {user_name}.",  
     "### {user_name} hesitates… his grip falters.",  
     "### But he quickly steels himself and attacks."],

    ["### You kneel down and refuse to fight.",  
     "### {user_name}'s breathing grows uneven.",  
     "### His next attack is noticeably weaker."],

    ["### You tell {user_name} that there must be another way.",  
     "### For a moment, {user_name}'s eyes seem full of sorrow.",  
     "### But he shakes his head and attacks anyway."],

    ["### You think about all the friends you made along the way.",  
     "### {user_name} stands silent, gripping his trident.",  
     "### His movements slow down, as if he's struggling with himself."],

    ["### You remind {user_name} of your past friendship.",  
     "### He tightens his grip on his weapon, but his stance wavers.",  
     "### A flicker of hesitation appears in his eyes."],

    ["### You call out {user_name}'s name softly.",  
     "### He pauses, struggling with his emotions.",  
     "### His next attack is sluggish and lacks determination."],

    ["### You tell {user_name} that fighting is meaningless.",  
     "### He grits his teeth, looking conflicted.",  
     "### His hands shake as he prepares his next attack."],

    ["### {user_name} is breathing heavily.",  
     "### You ask if he truly wants to continue this.",  
     "### He hesitates but does not lower his weapon."],

    ["### You step forward and extend a hand toward {user_name}.",  
     "### He flinches, unsure whether to strike or accept it.",  
     "### His attack barely grazes you."],

    ["### You speak about the memories you shared with {user_name}.",  
     "### His attacks become inconsistent.",  
     "### He’s struggling to stay focused."],

    ["### You tell {user_name} that deep down, he doesn’t want to fight.",  
     "### He stays silent, avoiding your gaze.",  
     "### His next attack lacks its usual force."],

    ["### You hold your ground and refuse to fight back.",  
     "### {user_name} grits his teeth, looking frustrated.",  
     "### His attacks become slower and less aggressive."],

    ["### You remind {user_name} of what he once fought for.",  
     "### He looks away, guilt flashing across his face.",  
     "### But he shakes his head and attacks again."],

    ["### You whisper, 'This isn’t who you are, {user_name}.'",  
     "### His hands tremble.",  
     "### His attack is much weaker than before."],

    ["### You tell {user_name} that hurting you won’t change anything.",  
     "### His expression wavers for a moment.",  
     "### But then he hardens his heart and swings his weapon."],

    ["### You talk about the future you both once dreamed of.",  
     "### {user_name} hesitates, his weapon lowering slightly.",  
     "### His next strike barely scratches you."],

    ["### You remind {user_name} of a time when he protected others.",  
     "### His eyes flicker with recognition.",  
     "### He exhales sharply and his next attack is weaker."],

    ["### You tell {user_name} that even now, you believe in him.",  
     "### He clenches his fists, clearly in conflict.",  
     "### He takes a deep breath and steadies himself."],

    ["### You recall a day when you and {user_name} laughed together.",  
     "### He visibly flinches at the memory.",  
     "### His movements become sluggish, as if he’s unsure of himself."],

    ["### You say, 'I know there’s still good in you, {user_name}.'",  
     "### He closes his eyes for a moment.",  
     "### His attack lacks the same determination."],

    ["### You tell {user_name} that he’s stronger than his anger.",  
     "### He exhales slowly, gripping his weapon tightly.",  
     "### But his next attack lacks force."],

    ["### You remind {user_name} of the person he used to be.",  
     "### His eyes darken with conflict.",  
     "### He attacks, but his strikes are uncertain."],

    ["### You stand still and simply watch {user_name}.",  
     "### He hesitates, his hands shaking.",  
     "### His attack never comes."],

    ["### You ask {user_name} if he truly wants this fight to continue.",  
     "### He doesn’t answer immediately.",  
     "### But his next attack is hesitant and weak."],

    ["### You take a step closer, unafraid.",  
     "### {user_name} clenches his jaw, his grip tightening.",  
     "### But his weapon wavers mid-swing."],

    ["### You lower your weapon and look at {user_name}.",  
     "### He exhales slowly, his expression troubled.",  
     "### His attacks lose their edge."],

    ["### You say, 'I’m not your enemy, {user_name}.'",  
     "### He stays silent, but his stance weakens.",  
     "### His next attack barely touches you."]
]



attack_dialogues = [
    "### What? You think I'm just gonna stand there and take it?",
    "### Tch... cute. You really thought that would work?",
    "### You just made the worst mistake of your life.",
    "### That was your plan? You must be joking.",
    "### I expected more. Guess I was wrong.",
    "### You sure you wanna do this?",
    "### Not bad... but not good enough.",
    "### I don’t need to try against someone like you.",
    "### That was your best? Now it’s my turn.",
    "### You’re hesitating. That’s your first mistake.",
    "### If you’re gonna swing, swing like you mean it.",
    "### Yawn... wake me up when you actually land a hit.",
    "### Keep struggling. It only makes it worse for you.",
    "### I’ve already won. You just don’t know it yet.",
    "### You talk big, but all I see is fear in your eyes.",
    "### You should’ve walked away when you had the chance.",
    "### That hesitation just cost you the fight.",
    "### You wanna impress me? Try staying on your feet.",
    "### This isn’t a game. I don’t play fair.",
    "### It’s over. You just haven’t realized it yet.",
    "### You’re not worth my time... but I’ll entertain you.",
    "### I don’t fight for fun. I fight to dominate.",
    "### You call that an attack? Try again.",
    "### Give up. You’re out of your league.",
    "### The difference between us? I finish what I start.",
    "### One hit. That’s all I need.",
    "### You better hope that wasn’t your best shot.",
    "### You’re predictable. And that’s why you’ll lose.",
    "### Go ahead, take your best shot. It won’t change anything."
]


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=',', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

async def send_message(content):
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(content)

async def send_embed(title, description):
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(title=title, description=description, color=0xFF0000)
        await channel.send(embed=embed)

def generate_health_bar(health, max_health, length=10):
    filled_blocks = int((health / max_health) * length)
    return "█" * filled_blocks + "─" * (length - filled_blocks)

@bot.command()
async def lilyban(ctx, member: discord.Member):
    global user_name, victim_name, user_health, victim_health

    user_name = ctx.author.name
    victim_name = member.name

    user_health = user_max_health
    victim_health = victim_max_health


    if type == 0:
        await ctx.send(f"## {member.mention}, if you have any unfinished business, please finish it")
        await asyncio.sleep(4)
        await ctx.send("### Because soon...")
        await asyncio.sleep(4)
        await ctx.send(f"### You'll be sent to another dimension <#{CHANNEL_ID}>.")
        await asyncio.sleep(4)
        await ctx.send(f"### Goodbye, {member.mention}...")

        for dialogue in beginning_dialogues:
            formatted_dialogue = dialogue.format(user_name=user_name, victim_name=victim_name, channel_id=CHANNEL_ID)
            await send_message(formatted_dialogue)
            await asyncio.sleep(3)
        await send_message("Type act to save yourself!!!")
    else:
        await ctx.send(f"## {member.mention}, Let just get it to the point")

        for dialogue in beginning_dialogues2:
            formatted_dialogue = dialogue.format(user_name=user_name, victim_name=victim_name, channel_id=CHANNEL_ID)
            await send_message(formatted_dialogue)
            await asyncio.sleep(2)

        await send_message("Type act to save yourself!!!")

@bot.event
async def on_message(message):
    start = 0
    global user_health, victim_health

    if message.author == bot.user:
        return

    if message.content.lower() == "act" and message.author.name == victim_name:
        act_set = random.choice(act_dialogues)

        if type == 0:
            for line in act_set:
                formatted_line = line.format(user_name=user_name, victim_name=victim_name)
                await send_message(formatted_line)
                await asyncio.sleep(3)
        else:
            pass

        randomint = random.randint(0, 1)
        if randomint == 0:
            if type == 1:
                if start == 0:
                    await send_message(f"{user_name} Dodged")
                    await send_message(attack_dialogues[0])
                    start = 1
                else:
                    await send_message(f"{user_name} Dodged")
                    randominteger = random.randint(0, len(attack_dialogues))
                    await send_message(attack_dialogues[randominteger])
            else:
                user_health = max(user_health + (user_max_health * 0.1), 0)
                await send_message(f"{user_name} Got Healed!")
        else:
            victim_health = max(victim_health - (victim_max_health * 0.1), 0)
            await send_message(f"{victim_name} Got damaged!")

        user_health_bar = generate_health_bar(user_health, user_max_health)
        victim_health_bar = generate_health_bar(victim_health, victim_max_health)

        dialogue_text = "\n".join([line.format(user_name=user_name, victim_name=victim_name) for line in act_set])
        health_status = f"**{user_name}**: `{user_health_bar}` `{int(user_health)}/{user_max_health}`\n" \
                        f"**{victim_name}**: `{victim_health_bar}` `{int(victim_health)}/{victim_max_health}`"

        await send_embed(f"{user_name}", f"{health_status}")

    await bot.process_commands(message)

bot.run(sBotDetails.bot_token)
