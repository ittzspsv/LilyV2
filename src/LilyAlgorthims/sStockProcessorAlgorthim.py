import re


def StockMessageProcessor(message: str):
    t_regex = re.search(r'Title:\s*\*\*(.+?)\*\*', message, re.DOTALL)
    title = t_regex.group(1).replace("Current ", "").strip() if t_regex else ""
    d_regex = re.search(r'Description:\s*(.+?)<:clock:', message, re.DOTALL)
    description = d_regex.group(1).strip() if d_regex else ""
    i_pattern = re.compile(r'<:[^:]+:\d+>\s*([a-zA-Z0-9 \-]+?)\s*-\s*([\d,]+)')
    raw_items = dict(i_pattern.findall(description))
    items = {k.strip(): int(v.replace(',', '')) for k, v in raw_items.items()}
    return title, items


message = """Title: **Current Normal Stock
**Description: <:spike:1300167770629214298> Spike - 180,000<:dollar:1300186776840835223>
<:trex:1300167828267073556> T-Rex - 2,700,000<:dollar:1300186776840835223>

<:clock:1182328726185312336> Stock Changes in: <t:1745020856:R>"""