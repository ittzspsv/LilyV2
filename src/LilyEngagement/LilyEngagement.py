import aiohttp
import random


links_dict = {
    ("https://dragonball-api.com/api/characters/", "dragon_ball"): {100: 44},
}

LilyReactions = {
    "airkiss": "{name1} blows an air kiss",
    "angrystare": "{name1} gives {name2} an angry stare",
    "bite": "{name1} bites {name2}",
    "bleh": "{name1} sticks out their tongue",
    "blush": "{name1} blushes",
    "brofist": "{name1} brofists {name2}",
    "celebrate": "{name1} celebrates",
    "cheers": "{name1} raises a toast",
    "clap": "{name1} claps",
    "confused": "{name1} looks confused",
    "cool": "{name1} acts cool",
    "cry": "{name1} cries",
    "cuddle": "{name1} cuddles {name2}",
    "dance": "{name1} dances",
    "drool": "{name1} drools",
    "evillaugh": "{name1} laughs evilly",
    "facepalm": "{name1} facepalms",
    "handhold": "{name1} holds hands with {name2}",
    "happy": "{name1} is happy",
    "headbang": "{name1} headbangs",
    "hug": "{name1} hugs {name2}",
    "huh": "{name1} says 'huh?'",
    "kiss": "{name1} kisses {name2}",
    "laugh": "{name1} laughs",
    "lick": "{name1} licks {name2}",
    "love": "{name1} is in love",
    "mad": "{name1} is mad",
    "nervous": "{name1} looks nervous",
    "no": "{name1} says no",
    "nom": "{name1} noms {name2}",
    "nosebleed": "{name1} has a nosebleed",
    "nuzzle": "{name1} nuzzles {name2}",
    "nyah": "{name1} says 'nyah~'",
    "pat": "{name1} pats {name2}",
    "peek": "{name1} peeks",
    "pinch": "{name1} pinches {name2}",
    "poke": "{name1} pokes {name2}",
    "pout": "{name1} pouts",
    "punch": "{name1} punches {name2}",
    "roll": "{name1} rolls on the ground",
    "run": "{name1} runs",
    "sad": "{name1} is sad",
    "scared": "{name1} is scared",
    "shout": "{name1} shouts",
    "shrug": "{name1} shrugs",
    "shy": "{name1} is shy",
    "sigh": "{name1} sighs",
    "sip": "{name1} sips a drink",
    "slap": "{name1} slaps {name2}",
    "sleep": "{name1} sleeps",
    "slowclap": "{name1} slow claps",
    "smack": "{name1} smacks {name2}",
    "smile": "{name1} smiles",
    "smug": "{name1} looks smug",
    "sneeze": "{name1} sneezes",
    "sorry": "{name1} says sorry",
    "stare": "{name1} stares at {name2}",
    "stop": "{name1} says stop",
    "surprised": "{name1} looks surprised",
    "sweat": "{name1} is sweating",
    "thumbsup": "{name1} gives a thumbs up",
    "tickle": "{name1} tickles {name2}",
    "tired": "{name1} is tired",
    "wave": "{name1} waves",
    "wink": "{name1} winks",
    "woah": "{name1} says 'woah!'",
    "yawn": "{name1} yawns",
    "yay": "{name1} says 'yay!'",
    "yes": "{name1} says yes"
}

LilyDialogues = {
    "Ban" : [
        ["{scamemer} has been found to be a scammer", "{scammer} tries to land an attack on {moderator} but...", "{moderator} casually destroyes him leading to a fatality"]
    ]
}
async def SelectVerse():
    choices = []
    weights = []
    for (url, label), nested in links_dict.items():
        key = list(nested.keys())[0]
        choices.append(((url, label), nested))
        weights.append(key)

    selected = random.choices(choices, weights=weights, k=1)[0]
    return selected

async def RandomCharacter():
    (selected_url, selected_label), selected_nested = await SelectVerse()
    max_val = list(selected_nested.values())[0]
    random_character_int = random.randint(0, max_val)

    url = f'{selected_url}{random_character_int}'

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if selected_label == "dragon_ball":
                return data['name'], data['image']
            elif selected_label == "naruto":
                return data['name'], data['images'][0]
            elif selected_label == "aot":
                return data['name'], data['img']
            elif selected_label == "demon_slayer":
                return data[0]['name'], data[0]['img']
