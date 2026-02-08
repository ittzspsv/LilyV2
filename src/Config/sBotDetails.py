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
    'verified' : '<:verified:1460394848761675828>',
    'perm' : '<:PermanentIcon:1467159355119108116>',
    'beli' : '<:beli:1467159970842939443>'
}

img = {
    'border' : 'https://cdn.discordapp.com/attachments/1438505067341680690/1438507704275570869/Border.png?ex=69172232&is=6915d0b2&hm=6fc4724fb6fb44c83c8fb82425f287c19c762d161ff882420f69abaaf725ad3a&',
    'warn' : 'https://media.discordapp.net/attachments/1438505067341680690/1438505320237236345/warn.png?ex=69171ffa&is=6915ce7a&hm=e25be9dacbbb4e718bd6d339c6a41c1740999e8ebacd6cff6bf12d9c4dd537f1&=&format=webp&quality=lossless',
    'member' : 'https://media.discordapp.net/attachments/1438505067341680690/1438505287052169259/member.png?ex=69171ff2&is=6915ce72&hm=bb90f5f2aaed4b7f0a50741e05e3e94d790596f44a99590a430a82fe500800e1&=&format=webp&quality=lossless',
    'logs' : 'https://media.discordapp.net/attachments/1438505067341680690/1438505245625024512/logs.png?ex=69171fe8&is=6915ce68&hm=3530c689a64656f50a78ddafa82138bd2c0d22e92d2ca281eb00423bea7cc7be&=&format=webp&quality=lossless'
}

fruit_emojis = {
    "emerald_diamond": "<:emerald_diamond:1467154507724226640>",
    "sadness_pain": "<:sadness_pain:1467154513763897458>",
    "purple_lightning": "<:purple_lightning:1467154519841575015>",
    "red_lightning": "<:red_lightning:1467154527026151633>",
    "flame": "<:flame:1467154534005608592>",
    "spring": "<:spring:1467154540229951488>",
    "torment_pain": "<:torment_pain:1467154546135531814>",
    "matrix_eagle": "<:matrix_eagle:1467154552649158686>",
    "love": "<:love:1467154559133548625>",
    "permanent_dragon_token": "<:permanent_dragon_token:1467154566662459587>",
    "celestial_pain": "<:celestial_pain:1467154572995985631>",
    "2x_boss_drops": "<:2x_boss_drops:1467154579719323864>",
    "eagle": "<:eagle:1467154587189252312>",
    "sound": "<:sound:1467154593296158740>",
    "rubber": "<:rubber:1467154598845350094>",
    "control": "<:control:1467154605501583535>",
    "parrot_chromatic": "<:parrot_chromatic:1467154611075809382>",
    "super_spirit_pain": "<:super_spirit_pain:1467154617258217484>",
    "rose_quartz_diamond": "<:rose_quartz_diamond:1467154623667376256>",
    "pain": "<:pain:1467154629241475158>",
    "topaz_diamond": "<:topaz_diamond:1467154635306303576>",
    "dough": "<:dough:1467154641698423021>",
    "fruit_notifier": "<:fruit_notifier:1467154649764331755>",
    "creation": "<:creation:1467154657284460658>",
    "frustration_pain": "<:frustration_pain:1467154662984646667>",
    "venom": "<:venom:1467154669577961586>",
    "requiem_eagle": "<:requiem_eagle:1467154675508842683>",
    "ice": "<:ice:1467154682123259956>",
    "legendary_scrolls": "<:legendary_scrolls:1467154689626865686>",
    "sand": "<:sand:1467154695356289057>",
    "ruby_diamond": "<:ruby_diamond:1467154702549520455>",
    "gas": "<:gas:1467154710996848884>",
    "west_dragon": "<:west_dragon:1467154719083335852>",
    "yellow_lightning": "<:yellow_lightning:1467154725215666268>",
    "empyrean_kitsune": "<:empyrean_kitsune:1467154737701851358>",
    "lightning": "<:lightning:1467154743737585862>",
    "celebration_bomb": "<:celebration_bomb:1467154749835972674>",
    "glacier_eagle": "<:glacier_eagle:1467154757415206976>",
    "blade": "<:blade:1467154765866598440>",
    "ember_dragon": "<:ember_dragon:1467154772904771688>",
    "t_rex": "<:t_rex:1467154779326120110>",
    "bomb": "<:bomb:1467154785298809087>",
    "2x_money": "<:2x_money:1467154793188557055>",
    "spin": "<:spin:1467154799244873839>",
    "blizzard": "<:blizzard:1467154805213364357>",
    "yeti": "<:yeti:1467154810900840628>",
    "thermite_bomb": "<:thermite_bomb:1467154817792348384>",
    "t_rex": "<:trex:1467154824578596925>",
    "smoke": "<:smoke:1467154830244974614>",
    "buddha": "<:buddha:1467154837069238365>",
    "dark_blade": "<:dark_blade:1467156337556459628>",
    "light": "<:light:1467156343717888207>",
    "east_dragon": "<:east_dragon:1467156352089460777>",
    "tiger": "<:tiger:1467156359186485319>",
    "portal": "<:portal:1467156365133746309>",
    "spirit": "<:spirit:1467156371647496345>",
    "fruit_storage": "<:fruit_storage:1467157163381100609>",
    "mythical_scrolls": "<:mythical_scrolls:1467157170478121071>",
    "chromatic_eclipse": "<:chromatic_eclipse:1467157177096474716>",
    "kitsune": "<:kitsune:1467157186143846532>",
    "spike": "<:spike:1467157192275787847>",
    "dragon_token": "<:dragon_token:1467157199146061836>",
    "gravity": "<:gravity:1467157207861694545>",
    "divine_portal": "<:divine_portal:1467157214073716817>",
    "dragon": "<:dragon:1467157220306456616>",
    "magma": "<:magma:1467157226371289160>",
    "nuclear_bomb": "<:nuclear_bomb:1467157232306360354>",
    "mammoth": "<:mammoth:1467157239512174858>",
    "dark": "<:dark:1467157245661020202>",
    "shadow": "<:shadow:1467157251663069186>",
    "spider": "<:spider:1467157258138943562>",
    "ghost": "<:ghost:1467157264027750688>",
    "meme": "<:meme:1467157270331658377>",
    "rocket": "<:rocket:1467157277415968902>",
    "quake": "<:quake:1467157283434659842>",
    "azura_bomb": "<:azura_bomb:1467157289873047574>",
    "green_lightning": "<:green_lightning:1467157295896068237>",
    "werewolf": "<:werewolf:1467157302208626848>",
    "phoenix": "<:phoenix:1467157308193898516>",
    "galaxy_kitsune": "<:galaxy_kitsune:1467157314787086509>",
    "fast_boats": "<:fast_boats:1467157322257400013>",
    "2x_mastery": "<:2x_mastery:1467157330129981683>",
    "diamond": "<:diamond:1467157336219979787>",
    "falcon": "<:falcon:1467157342306045953>",
}