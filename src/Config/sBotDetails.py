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
    "creation": "<:creation:1488572682378154014>",
    "pain": "<:pain:1488572687520501891>",
    "2x_money": "<:2x_money:1488572693543522335>",
    "green_lightning": "<:green_lightning:1488572699084329031>",
    "2x_mastery": "<:2x_mastery:1488572706197868564>",
    "legendary_scrolls": "<:legendary_scrolls:1488572713483374753>",
    "fiend_yeti": "<:fiend_yeti:1488572719372042443>",
    "eagle": "<:eagle:1488572726691102978>",
    "blizzard": "<:blizzard:1488572732508602368>",
    "phoenix": "<:phoenix:1488572737512542430>",
    "dark_blade": "<:dark_blade:1488572743342358698>",
    "portal": "<:portal:1488572748853809253>",
    "east_dragon": "<:east_dragon:1488572756252688556>",
    "quake": "<:quake:1488572761453498499>",
    "sand": "<:sand:1488572766645915810>",
    "gas": "<:gas:1488572774334206160>",
    "venom": "<:venom:1488572779929276516>",
    "fruit_notifier": "<:fruit_notifier:1488572787743527022>",
    "purple_lightning": "<:purple_lightning:1488572793145659393>",
    "celebration_bomb": "<:celebration_bomb:1488572798333882533>",
    "trex": "<:trex:1488572804017426492>",
    "ruby_diamond": "<:ruby_diamond:1488572809700442222>",
    "permanent_dragon_token": "<:permanent_dragon_token:1488572816361263234>",
    "lightning": "<:lightning:1488572822354919466>",
    "west_dragon": "<:west_dragon:1488572830118580426>",
    "fast_boats": "<:fast_boats:1488572836225482853>",
    "2x_boss_drops": "<:2x_boss_drops:1488572842223341741>",
    "falcon": "<:falcon:1488572847705292810>",
    "red_lightning": "<:red_lightning:1488572853862268948>",
    "shadow": "<:shadow:1488572859268731092>",
    "spider": "<:spider:1488572864452886770>",
    "meme": "<:meme:1488572869494439938>",
    "rubber": "<:rubber:1488572882312237198>",
    "dough": "<:dough:1488572888129867906>",
    "mythical_scrolls": "<:mythical_scrolls:1488572893972660245>",
    "gravity": "<:gravity:1488572901354639481>",
    "fruit_storage": "<:fruit_storage:1488572908132634646>",
    "frustration_pain": "<:frustration_pain:1488572913677238412>",
    "requiem_eagle": "<:requiem_eagle:1488572918911995956>",
    "galaxy_kitsune": "<:galaxy_kitsune:1488572924779565286>",
    "dragon_token": "<:dragon_token:1488572930689466660>",
    "empyrean_kitsune": "<:empyrean_kitsune:1488572936725074002>",
    "sound": "<:sound:1488572941846315140>",
    "bomb": "<:bomb:1488572947537985738>",
    "divine_portal": "<:divine_portal:1488572952793317447>",
    "nuclear_bomb": "<:nuclear_bomb:1488572958921461832>",
    "ice": "<:ice:1488572964185313352>",
    "mammoth": "<:mammoth:1488572969428189224>",
    "smoke": "<:smoke:1488572975019065344>",
    "matrix_eagle": "<:matrix_eagle:1488572980496961536>",
    "azura_bomb": "<:azura_bomb:1488572985911541800>",
    "topaz_diamond": "<:topaz_diamond:1488572996934308011>",
    "glacier_eagle": "<:glacier_eagle:1488573002495955122>",
    "thermite_bomb": "<:thermite_bomb:1488573007847882862>",
    "spin": "<:spin:1488573013040435220>",
    "sadness_pain": "<:sadness_pain:1488573018530648174>",
    "emerald_diamond": "<:emerald_diamond:1488573023757013283>",
    "blade": "<:blade:1488573029075255458>",
    "ember_dragon": "<:ember_dragon:1488573042425725060>",
    "rose_quartz_diamond": "<:rose_quartz_diamond:1488573047551033430>",
    "tiger": "<:tiger:1488573053599486094>",
    "rocket": "<:rocket:1488573066371006495>",
    "yeti": "<:yeti:1488573071248986225>",
    "light": "<:light:1488573077271871818>",
    "diamond": "<:diamond:1488573082502172967>",
    "dragon": "<:dragon:1488573087631937588>",
    "kitsune": "<:kitsune:1488573094993068145>",
    "magma": "<:magma:1488573100546064507>",
    "love": "<:love:1488573105721966695>",
    "yellow_lightning": "<:yellow_lightning:1488573111652585764>",
    "celestial_pain": "<:celestial_pain:1488573117134803067>",
    "dark": "<:dark:1488573129038233792>",
    "ghost": "<:ghost:1488573134490701944>",
    "buddha": "<:buddha:1488573139678924850>",
    "spring": "<:spring:1488573145207148736>",
    "chromatic_eclipse": "<:chromatic_eclipse:1488573150567334031>",
    "parrot_chromatic": "<:parrot_chromatic:1488573155621474425>",
    "spirit": "<:spirit:1488573161367666689>",
    "spike": "<:spike:1488573166677917756>",
    "control": "<:control:1488573171916603555>",
    "torment_pain": "<:torment_pain:1488573177243242747>",
    "super_spirit_pain": "<:super_spirit_pain:1488573182527934805>",
    "werewolf": "<:werewolf:1488573188920180968>",
    "flame": "<:flame:1488573194393616676>"
}

expression = {
    "neutral" : "",
    "focused" : "",
    "explaining" : "",
    "pouting" : "",
    "blushing" : "",
    "concerned" : "",
    "hand_to_chest_neutral" : "",
    "curious" : "",
    "shyness" : "",
    "adjusting_hair" : "",
    "yawning" : "",
    "deep_thought" : "",
    "puffing_cheeks" : "",
    "confused" : "",
    "hoodie_on" : "",
    "rubbing_eyes" : "",
    "sleeping"  : "",
    "pensive" : "",
    "aha" : "",
    "stop" : "",
    "disappointed" : ""
}