
#VERY IMPORTANT TOKEN THAT SHOULD NOT BE SHARED HERE
bot_token = ""

'''SET THE BOT NAME HERE
    THIS WILL BE DISPLAYED AS AUTHOR NAME IN THE EMBED'''
bot_name = "BloxTrade"

'''SET THE BOT ICON HERE
    THIS WILL BE DISPLAYED AS AUTHOR ICON IN THE EMBED'''
bot_icon_link_url = "https://cdn.discordapp.com/icons/970643838047760384/a_a6cfa91910d8e2fff68defeda76dd902.png?size=256"


'''SET THE EMBED BASE OUTLINE COLOR HERE'''
embed_color_code = 0xfa0064

'''ENTER THE SERVER NAME HERE AS YOUR WISH
    THIS WILL BE DISPLAYED IN THE FOOTER OF THE EMBED'''
server_name = "Blox Trade"

'''ENTER THE SERVER INVITE LINK'''
server_invite_link = "https://discord.com/invite/bloxtrade"


'''THIS DETERMINES HOW THE FRUIT SHOULD APPEAR.
    SHOULD THE FRUIT IMAGE BE APPEARED AS A IMAGE OR A THUMBNAIL
    VALUE = 1 -> IMAGE AS THUMBNAIL
    VALUE = 0 -> IMAGE AS IMAGE'''
fruit_value_embed_type = 1

'''PORT SYSTEM - PORTING FROM TEST SERVER TO MAIN SERVER
    CURRENTLY EMOJI DIFFERES SO WHEN WE SET PORT SYSTEM TO 1 IT WORKS BASED ON REAL SERVER CONDITIONS    
'''

port = 1  #CURRENTLY PORT SET TO DEPLOYMENT SERVER

#USED FOR DEVELOPMENT SERVER
if port == 0:
    TRADE_EMOJI_ID = ["1348722170586599465"]
    PERM_EMOJI_ID = ["1349449830048731206"]

    '''ENTER THE MIDDLEMEN CHANNEL HERE SO THAT IF FRUIT VALUE EXCEEDS TO LIKE 5 IT WILL BE PROMPTED THERE
    '''
    middle_men_channel_id = 1349351985626878013

    '''ENTER THE STOCK UPDATE CHANNEL ID HERE
    '''
    stock_update_channel_id = 1349358716054671400

    '''ENTER THE W OR L CHANNEL ID HERE
    '''
    w_or_l_channel_id = 1349753791704072313

    '''ENTER THE FRUIT VALUES CHANNEL ID HERE
    '''
    fruit_values_channel_id = 1349753820053508186

    stock_ping_role_id = "1348020649444114574"


#USED IN REAL SERVER (BLOXTRADE)
else:
    TRADE_EMOJI_ID = ["1324867813067984986", "1039668628561342504"] #CHANGED into lists to support multiple emojis
    PERM_EMOJI_ID = ["1236412085894905887", "1170178840283316244", "1324867811775877241"] #CHANGED into lists to support multiple emojis


    '''ENTER THE MIDDLEMEN CHANNEL HERE SO THAT IF FRUIT VALUE EXCEEDS TO LIKE 5 IT WILL BE PROMPTED THERE
    '''
    middle_men_channel_id = 1341106937676304434

    '''ENTER THE STOCK UPDATE CHANNEL ID HERE
    '''
    stock_update_channel_id = 1324581262413004800

    '''ENTER THE W OR L CHANNEL ID HERE
    '''
    w_or_l_channel_id = 1350503040616235068

    '''ENTER THE FRUIT VALUES CHANNEL ID HERE
    '''
    fruit_values_channel_id = 1350503093963456603

    '''
    MAKE SURE THIS IS FILLED BECAUSE WE CANNOT ACCESS THE STOCK PING ROLE ID
    '''
    stock_ping_role_id = "1348020649444114574"