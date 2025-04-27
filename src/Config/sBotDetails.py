import json
import os
import discord
from discord.ext import commands


async def load_exceptional_ban_ids(ctx: commands.Context):
        Ban_Exceptional_File = f"storage/{ctx.guild.id}/configs/blacklisted_mods.json"
        if os.path.exists(Ban_Exceptional_File):
            with open(Ban_Exceptional_File, "r") as f:
                return json.load(f).get("ids", [])
        return []

async def save_exceptional_ban_ids(ctx, ids):
        Ban_Exceptional_File = f"storage/{ctx.guild.id}/configs/blacklisted_mods.json"
        with open(Ban_Exceptional_File, "w") as f:
            json.dump({"ids": ids}, f, indent=4)

async def remove_exceptional_ban_id(ctx, remove_id):
        Ban_Exceptional_File = f"storage/{ctx.guild.id}/configs/blacklisted_mods.json"
        try:
            with open(Ban_Exceptional_File, "r") as f:
                data = json.load(f)

            if "ids" in data and remove_id in data["ids"]:
                data["ids"].remove(remove_id)

                with open(Ban_Exceptional_File, "w") as f:
                    json.dump(data, f, indent=4)

                return True
            else:
                return False

        except (FileNotFoundError, json.JSONDecodeError):
            return False

async def load_roles(ctx: commands.Context):
        Role_Assignable_File = f"storage/{ctx.guild.id}/configs/assignable_roles.json"
        if os.path.exists(Role_Assignable_File):
            with open(Role_Assignable_File, "r") as f:
                return json.load(f).get("roles", {})
        return {}

async def save_roles(ctx: commands.Context, new_id, priority):
        Role_Assignable_File = f"storage/{ctx.guild.id}/configs/assignable_roles.json"
        roles = await load_roles(ctx)
        roles[str(new_id)] = priority
        with open(Role_Assignable_File, "w") as f:
            json.dump({"roles": roles}, f, indent=4)

async def save_channel(ctx: commands.Context, channel_name, channel_id):
    config_path = f"storage/{ctx.guild.id}/configs/configs.json"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = json.load(f)
    else:
        data = {}
    channel_config = data.get("ChannelConfig", {})
    channel_config[str(channel_name)] = int(channel_id)

    data["ChannelConfig"] = channel_config
    with open(config_path, "w") as f:
        json.dump(data, f, indent=4)

def load_channel_config(ctx: commands.Context, guild_id:int=0, type=0):
    if type == 0:
        config_path = f"storage/{ctx.guild.id}/configs/configs.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        if not os.path.exists(config_path):
            return {}

        with open(config_path, "r") as f:
            data = json.load(f)

        return data.get("ChannelConfig", {})
    else:
        config_path = f"storage/{guild_id}/configs/configs.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        if not os.path.exists(config_path):
            return {}

        with open(config_path, "r") as f:
            data = json.load(f)

        return data.get("ChannelConfig", {}) 


# VERY IMPORTANT TOKEN THAT SHOULD NOT BE SHARED HERE
bot_token = ""

# Command prefix for the bot
bot_command_prefix = "?"

# Bot display settings
bot_name = "BloxTrade"
bot_icon_link_url = "https://cdn.discordapp.com/icons/970643838047760384/a_a6cfa91910d8e2fff68defeda76dd902.png?size=256"
embed_color_code = 0xfa0064
# Server display settings
server_name = "Blox Trade"
server_invite_link = "https://discord.com/invite/bloxtrade"

# Display style for fruit image (1 = thumbnail, 0 = full image)
fruit_value_embed_type = 1

# Port system (0 = test environment, 1 = production environment)
port = 1 # Currently set to Production Server

# ENVIRONMENT SETTINGS
if port == 0:
    # DEVELOPMENT SERVER SETTINGS
    TRADE_EMOJI_ID = ["1348722170586599465"]
    PERM_EMOJI_ID = ["1349449830048731206"]

    middle_men_channel_id = 1349351985626878013
    stock_ping_role_id = "1348020649444114574"
    stock_team_roll_name = "Stock Ping"

    limit_Ban_details = {
        1356187197526638693: 3, #HEAD ADMIN in SHREE_SPSV SERVER
        1348020649444114574: 2,  #STOCK PING in SHREE_SPSV SERVER
        1325145748035207239 : 3 #CREATORS ROLE IN TEXIOVERSE,
    }

    trial_moderator_name = "Stock Ping"

    service_manager_roll_id = 1356187197526638693

else:
    # PRODUCTION SERVER SETTINGS (BLOXTRADE)
    TRADE_EMOJI_ID = ["1324867813067984986", "1039668628561342504"]
    PERM_EMOJI_ID = ["1236412085894905887", "1170178840283316244", "1324867811775877241"]

    middle_men_channel_id = 1341106937676304434
    stock_ping_role_id = "1345555258314588170"
    stock_team_roll_name = "Moderator"
    
    trial_moderator_name = "Trial Moderator"

    #Their user id followed by how much limited ban they can do in a day
    limit_Ban_details = {
        1333123391875584011 : 20, #HEAD MODERATOR
        1348412603701133506 : 10,  #SENIOR MODERATOR
        1324581146272595999 : 5,  #MODERATORS
        1365324107947970700 : 50 #MANAGER
    }

    service_manager_roll_id = 1333123391875584011 #CURRENTLY HEAD MODERATORS
    giveaway_hoster_role = 1345579694522630205    #USED TO CREATE EMBEDS

# Embed colors based on item type
embed_color_codes = {
    "common": 0xa1a4a5,
    "uncommon": 0x1c78ce,
    "rare": 0x1f1cce,
    "legendary": 0x9f1cce,
    "mythical": 0xce1c1c,
    "gamepass": 0xffd500,
    "limited": 0xffd500
}

# Admin/Moderator/Dev access user IDs
#Commands They can use : update fruit values, fruit value / stock logs, delete fruit value / stock logs
ids = [845511381637529641, 999309816914792630, 549777573551276051, 1120025980178796714] #CURRENT USER IDS - [SHREE, TEXIO, ZELY, VOUCH]


owner_ids = [549777573551276051, 1120025980178796714, 845511381637529641]  #CURRENT USER IDS - [ZELY, VOUCH]
trusted_moderator_ids = [1329951007311921212, 895649073082814475, 845511381637529641, 999309816914792630, 1220169032762920965, 869064913535004753, 827775992521031700] #CURRENT USER IDS [KAI, LELOUCH, SHREE, TEXIO, FAMOPLAYS, OBLIVION, SAMURAI]
staff_manager_ids = [895649073082814475] #CURRENT USER IDS - [LELOUCH]
