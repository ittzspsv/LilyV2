# Command prefix for the bot
bot_command_prefix = "."

# Bot display settings
bot_name = "BloxTrade"
bot_icon_link_url = "https://cdn.discordapp.com/icons/970643838047760384/a_a6cfa91910d8e2fff68defeda76dd902.png?size=256"
embed_color_code = 0xfa0064
# Server display settings
server_name = "Blox Trade"
server_invite_link = "https://discord.com/invite/bloxtrade"

# Port system (0 = test environment, 1 = production environment)
port = 1 # Currently set to Production Server

# ENVIRONMENT SETTINGS
if port == 0:
    # DEVELOPMENT SERVER SETTINGS

    #Core Channel Config
    stock_fetch_guild_id = 1099482621161001113
    stock_fetch_channel_id = 1431687087928905821
    stock_fetch_channel_id_pvb = 1431687232074551307
    weather_fetch_channel_id_pvb = 1431687357555277995

else:
    appeal_server_link = "https://discord.gg/StcA9GaEUU"

    role_creation_limit = 1

    #GUILD REFERENCE
    GUILD_ID = 970643838047760384

    #Core Channel Config
    stock_fetch_guild_id = 1099482621161001113
    stock_fetch_channel_id = 1431687087928905821
    stock_fetch_channel_id_pvb = 1431687232074551307
    weather_fetch_channel_id_pvb = 1431687357555277995

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

emoji = {
    'clock' : '<:Clock:1438058728137162806>',
    'shield' : '<:shield:1438048782850723882>',
    'calender' : '<:calender:1438048778526396529>',
    'bookmark' : '<:bookmark:1438048772939583571>',
    'logs' : '<:logs:1438047737001017447>',
    'warn' : '<:warn:1438045607116668948>',
    'staff' : '<:staff:1438045603882991698>',
    'pencil' : '<:pencil:1438045599361532005>',
    'mute' : '<:mute:1438045595695710230>',
    'member' : '<:member:1438045591098753104>',
    'gift' : '<:gift:1438045585570791555>',
    'ban_hammer' : '<:ban_hammer:1438045582139719770>',
    'arrow' : '<:arrow:1438045578721493062>',
    'online' : '<:online:1438081060431855708>',
    'invisible' : '<:invisible:1438081057273417810>',
    'dnd' : '<:dnd:1438081053095890996>',
    'cross' : '<:cross:1438078467257143379>',
    'checked' : '<:checked:1438078165372243978>',
    'bot' : '<:bot:1438504383397494896>',
    'ticket' : '<:ticket:1438584946997592114>',
    'music_play' : '<:MusicPlay:1443189668307931268>',
    'music_shuffle' : '<:MusicShuffle:1443189671105400896>',
    'music_repeat' : '<:MusicRepeat:1443189674897182841>',
    'music_author' : '<:MusicAuthor:1443189678269268019>',
    'music_folder' : '<:MusicFolder:1443189682077962312>',
    'music_playlist' : '<:MusicPlaylist:1443189686712537098>',
    'coin' : '<:coin:1444123040538693662>',
    'verified' : '<:verified:1460394848761675828>'
}

img = {
    'border' : 'https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=69172232&is=6915d0b2&hm=6fc4724fb6fb44c83c8fb82425f287c19c762d161ff882420f69abaaf725ad3a&',
    'warn' : 'https://media.discordapp.net/attachments/1438505067341680690/1438505320237236345/warn.png?ex=69171ffa&is=6915ce7a&hm=e25be9dacbbb4e718bd6d339c6a41c1740999e8ebacd6cff6bf12d9c4dd537f1&=&format=webp&quality=lossless',
    'member' : 'https://media.discordapp.net/attachments/1438505067341680690/1438505287052169259/member.png?ex=69171ff2&is=6915ce72&hm=bb90f5f2aaed4b7f0a50741e05e3e94d790596f44a99590a430a82fe500800e1&=&format=webp&quality=lossless',
    'logs' : 'https://media.discordapp.net/attachments/1438505067341680690/1438505245625024512/logs.png?ex=69171fe8&is=6915ce68&hm=3530c689a64656f50a78ddafa82138bd2c0d22e92d2ca281eb00423bea7cc7be&=&format=webp&quality=lossless'
}


expressions = {
    
}