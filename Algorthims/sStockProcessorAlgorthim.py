import re

import Algorthims.sTradeFormatAlgorthim as TFA

import Algorthims.sFruitDetectionAlgorthim as FDA


def StockMessageProcessor(message: str):
    t_regex = re.search(r'Title:\s*\*\*(.+?)\*\*', message)
    title = t_regex.group(1).replace("Current ", "") if t_regex else ""

    d_regex = re.search(r'Description:\s*(.+?)<:clock:', message, re.DOTALL)
    description = d_regex.group(1).strip() if d_regex else ""

    i_pattern = re.compile(r'>\s*([^\-<]+?)\s*-\s*([\d,]+)<')
    items = dict(i_pattern.findall(description))
    #items = TFA.MatchFruitSet(items, FDA.fruit_names)

    return title, items


message = """Title: **Current Mirage Stock**
Description: <:chop:1300167881337864224> Blade - 30,000<:dollar:1300186776840835223>
<:rubber:1300167727003996321> Rubber - 750,000<:dollar:1300186776840835223>
<:magma:1300167664475443353> Magma - 960,000<:dollar:1300186776840835223>
<:control:1300167884961484810> Control - 3,200,000<:dollar:1300186776840835223>
<:gas:1317784723690623079> Gas - 3,200,000<:dollar:1300186776840835223>

<:clock:1182328726185312336> Stock Changes in: <t:1744887265:R>"""

