import re

def mute_parser(duration: str) -> int:
    match = re.match(r"(\d+)([smhd])", duration.strip().lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration}")

    value = int(match.group(1))
    unit = match.group(2)
    if unit == "s":
        return value
    elif unit == "m":
        return value * 60
    elif unit == "h":
        return value * 3600
    elif unit == "d":
        return value * 86400
    else:
        raise ValueError(f"Unsupported unit: {unit}")