import json


def EvaluateSkill(name, age=1, weight=1):
    def time_to_seconds(t: str) -> int:
        m, s = map(int, t.split(":"))
        return m * 60 + s

    def seconds_to_time(sec: int) -> str:
        m, s = divmod(sec, 60)
        return f"{m:02}:{s:02}"

    def interpolate(start, end, age, stat_type, weight=10):
        factor = (age - 1) / 99 * (weight / 10)

        if stat_type == "time":
            start_sec = time_to_seconds(start)
            end_sec = time_to_seconds(end)
            val = start_sec + (end_sec - start_sec) * factor
            return seconds_to_time(round(val))
        elif stat_type == "float":
            val = start + (end - start) * factor
            return round(val, 2)
        elif stat_type == "int":
            val = start + (end - start) * factor
            return int(round(val))
        return start

    def get_ability_text(ability, age, weight=10):
        stats = {}
        for k, v in ability["stats"].items():
            stats[k] = interpolate(v["start"], v["end"], age, v["type"], weight)
        return ability["description"].format(**stats)

    # Example usage with abilities.json
    with open("abilities.json") as f:
        data = json.load(f)

    for ability in data["abilities"]:
        print("Age 1  :", get_ability_text(ability, 1))
        print("Age 50 :", get_ability_text(ability, 50))
        print("Age 100:", get_ability_text(ability, 100))
        print("-" * 50)
        break
