import json
import os
from discord.ext import commands
import aiohttp


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
    
def load_channel_config_guild_id(guild_id: int, type=0):
    if guild_id is None:
        return {}

    if type == 0:
        config_path = f"storage/{guild_id}/configs/configs.json"
    else:
        config_path = f"storage/{guild_id}/configs/configs.json"

    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    if not os.path.exists(config_path):
        return {}

    with open(config_path, "r") as f:
        data = json.load(f)
    return data.get("ChannelConfig", {})


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
meta_enable = 0
engagement = 0

# ENVIRONMENT SETTINGS
if port == 0:
    # DEVELOPMENT SERVER SETTINGS
    TRADE_EMOJI_ID = ["1348722170586599465"]
    PERM_EMOJI_ID = ["1349449830048731206"]

    combo_channel_id = 1376633733997924422
    stock_ping_role_id = "1348020649444114574"
    stock_team_roll_name = "Stock Ping"

    limit_Ban_details = {
        1356187197526638693: 9999, #HEAD ADMIN in SHREE_SPSV SERVER
        1348020649444114574: 2,  #STOCK PING in SHREE_SPSV SERVER
        1325145748035207239 : 3 #CREATORS ROLE IN TEXIOVERSE,
    }

    trial_moderator_name = "Stock Ping"

    service_manager_roll_id = 1356187197526638693

    appeal_server_link = "https://discord.gg/RvkyTxnH6r"

    role_creation_limit = 1

    StaffRoles = [1381715715794534590]
    TrustedStaffRoles = [1381715790889357393]
    StaffManagerRoles = [1381715601772511493]
    DeveloperRoles = [1381715636010618940]
    OwnerRoles = [1381728367207907418]
    BlacklistedRoles = [1381715681904558132]

    #CHANNELS -- GAG
    seed_gear_stock_channel_id = 1387001376269144116
    eggstock_channel_id = 1387001376269144116
    cosmeticsstock_channel_id = 1387001376269144116
    eventshop_channel_id = 1387001376269144116
    weatherupdate_channel_id = 1387001376269144116

    #GUILD REFERENCE
    GUILD_ID = 1240215331071594536

else:
    # PRODUCTION SERVER SETTINGS (BLOXTRADE)
    TRADE_EMOJI_ID = ["1324867813067984986", "1039668628561342504"]
    PERM_EMOJI_ID = ["1236412085894905887", "1170178840283316244", "1324867811775877241"]
    combo_channel_id = 0
    stock_ping_role_id = "1345555258314588170"
    stock_team_roll_name = "Moderator"
    
    trial_moderator_name = "Trial Moderator"

    #Their user id followed by how much limited ban they can do in a day
    limit_Ban_details = {
        1333123391875584011 : 20, #HEAD MODERATOR
        1348412603701133506 : 10,  #SENIOR MODERATOR
        1324581146272595999 : 5,  #MODERATORS
        1365324107947970700 : 50, #MANAGER
        1351867043393044551 : 50, #DEVELOPER
        
        #GAG SERVER
        1389986649273929778 : 5, #Moderator
        1389986637831737365 : 10, #Senior Moderator
        1389986627207823360 : 20, #Head Moderator
        1390347777959264328 : 30, #Head Administrator
        1389986618320093236 : 50, #Staff Manager
        1389986591208116335 : 50, #Developer
    }

    service_manager_roll_id = 1333123391875584011 #CURRENTLY HEAD MODERATORS
    giveaway_hoster_role = 1345579694522630205    #USED TO CREATE EMBEDS

    appeal_server_link = "https://discord.gg/CycZg9UmyT"

    role_creation_limit = 1

    StaffRoles = [1360395431737036900, 1389986714159808552] # Staff Role
    TrustedStaffRoles = [1333444259033911306, 1390347661936165057, 1390347777959264328] # Trusted Role
    StaffManagerRoles = [1365324107947970700, 1389986618320093236] # Staff Manager Roles
    DeveloperRoles = [1351867043393044551, 1389986591208116335] # Developer Role
    OwnerRoles = [1324577057228980285, 1389986702075891884] # (+) Role
    BlacklistedRoles = [1357492900195205130, 1389986579610730617] # Kai Role

    #CHANNELS -- GAG
    seed_gear_stock_channel_id = 1389972635403948153
    eggstock_channel_id = 1389977044733136966
    cosmeticsstock_channel_id = 1389977261486112869
    eventshop_channel_id = 1390370838154580200
    weatherupdate_channel_id = 1389977107244777634

    #GUILD REFERENCE
    GUILD_ID = 1389970924664786964

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


owner_ids = [549777573551276051, 1120025980178796714]  #CURRENT USER IDS - [ZELY, VOUCH]
trusted_moderator_ids = [1329951007311921212, 1369716151210475621, 845511381637529641, 999309816914792630, 1220169032762920965, 869064913535004753] #CURRENT USER IDS [KAI, LELOUCH, SHREE, TEXIO, FAMOPLAYS, OBLIVION]
staff_manager_ids = [895649073082814475, 1369716151210475621] #CURRENT USER IDS - [LELOUCH] 
staff_manager_role_id = 1365324107947970700

#ROLES

async def update_config_data():
    global ids, owner_ids, trusted_moderator_ids, staff_manager_ids, limit_Ban_details, StaffRoles, TrustedStaffRoles, StaffManagerRoles, DeveloperRoles, OwnerRoles, BlacklistedRoles,seed_gear_stock_channel_id, eggstock_channel_id,cosmeticsstock_channel_id,weatherupdate_channel_id,GUILD_ID, eventshop_channel_id
    url = 'https://ittzspsv.github.io/LilyV2-Configs/LilyConfig.json'

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            try:
                text = await response.text()
                data = json.loads(text)

                ids = data['ids']
                trusted_moderator_ids = data['trusted_moderator_ids']
                staff_manager_ids = data['staff_manager_ids']
                limit_Ban_details = {int(k): v for k, v in data['limit_ban_details'].items()}

                StaffRoles = data['Roles']['StaffRoles']
                TrustedStaffRoles = data['Roles']['TrustedStaffRoles']
                StaffManagerRoles = data['Roles']['StaffManagerRoles']
                DeveloperRoles = data['Roles']['DeveloperRoles']
                OwnerRoles = data['Roles']['OwnerRoles']
                BlacklistedRoles = data['Roles']['BlacklistedRoles']

                #CHANNELS -- GAG
                seed_gear_stock_channel_id = int(data['GAGChannels']['seed_gear_stock_channel_id'])
                eggstock_channel_id = int(data['GAGChannels']['eggstock_channel_id'])
                cosmeticsstock_channel_id = int(data['GAGChannels']['cosmeticsstock_channel_id'])
                weatherupdate_channel_id = int(data['GAGChannels']['weatherupdate_channel_id'])
                eventshop_channel_id = int(data['GAGChannels']['eventshop_channel_id'])

                #GUILD REFERENCE
                GUILD_ID = int(data['Guilds']['GAGGuildID'])


                return "Success"
            except Exception as e:
                return f'Failure: {e}'
 
