"""Map a textbook word to a Twemoji SVG when Unicode gives that word an emoji.

The graphics come from https://github.com/jdecked/twemoji (CC-BY 4.0).
The word list is built from Unicode CLDR names, plus a few textbook aliases.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_BASE = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@17.0.2/assets/svg/"
_PAGE = "https://github.com/jdecked/twemoji"

# Textbook spellings that CLDR names differently. The value must be an English CLDR name.
_ALIAS = {
    "sheep": "ewe",
    "dinosaur": "sauropod",
    "grape": "grapes",
    "car": "automobile",
    "plane": "airplane",
    "bike": "bicycle",
    "truck": "delivery truck",
    "boat": "sailboat",
    "father": "man",
    "dad": "man",
    "mother": "woman",
    "mum": "woman",
    "mom": "woman",
    "grandfather": "old man",
    "grandpa": "old man",
    "grandmother": "old woman",
    "grandma": "old woman",
    "brother": "boy",
    "sister": "girl",
    "kid": "child",
    "uncle": "man",
    "aunt": "woman",
    "red": "red circle",
    "blue": "blue circle",
    "green": "green circle",
    "yellow": "yellow circle",
    "purple": "purple circle",
    "brown": "brown circle",
    "black": "black circle",
    "white": "white circle",
    "pink": "pink heart",
    "orange": "tangerine",
    "colour": "artist palette",
    "color": "artist palette",
    "cap": "billed cap",
    "hat": "billed cap",
    "shirt": "t shirt",
    "shoe": "running shoe",
    "sock": "socks",
    "clothes": "t shirt",
    "jacket": "coat",
    "trousers": "jeans",
    "schoolbag": "backpack",
    "rubber": "eraser",
    "noodle": "steaming bowl",
    "noodles": "steaming bowl",
    "rice": "cooked rice",
    "milk": "glass of milk",
    "tea": "teacup without handle",
    "water": "droplet",
    "meat": "cut of meat",
    "beef": "cut of meat",
    "cake": "shortcake",
    "hotpot": "pot of food",
    "hot pot": "pot of food",
    "juice": "cup with straw",
    "cola": "cup with straw",
    "soup": "pot of food",
    "food": "pot of food",
    "fried rice": "cooked rice",
    "seafood": "shrimp",
    "pumpkin": "jack o lantern",
    "salad": "green salad",
    "home": "house",
    "shop": "convenience store",
    "supermarket": "convenience store",
    "bookshop": "open book",
    "park": "national park",
    "forest": "deciduous tree",
    "hill": "mountain",
    "palace": "castle",
    "classroom": "school",
    "doctor": "health worker",
    "nurse": "health worker",
    "dancer": "woman dancing",
    "football player": "soccer ball",
    "pianist": "musical keyboard",
    "delivery worker": "delivery truck",
    "run": "person running",
    "walk": "person walking",
    "climb": "person climbing",
    "dance": "woman dancing",
    "sleep": "sleeping face",
    "eat": "fork and knife",
    "drink": "cup with straw",
    "sing": "microphone",
    "write": "writing hand",
    "read": "open book",
    "hand": "raised hand",
    "arm": "flexed biceps",
    "face": "grinning face",
    "rain": "cloud with rain",
    "snow": "cloud with snow",
    "wind": "wind face",
    "sunny": "sun",
    "cloudy": "cloud",
    "windy": "wind face",
    "rainy": "cloud with rain",
    "snowy": "cloud with snow",
    "one": "keycap 1",
    "two": "keycap 2",
    "three": "keycap 3",
    "four": "keycap 4",
    "five": "keycap 5",
    "six": "keycap 6",
    "seven": "keycap 7",
    "eight": "keycap 8",
    "nine": "keycap 9",
    "ladybird": "lady beetle",
    "jiaozi": "dumpling",
    "mooncake": "moon cake",
    "puppy": "dog face",
    "hen": "rooster",
    "pet": "dog face",
    "football": "soccer ball",
    "ball": "soccer ball",
    "butterfly": "butterfly",
    "flower": "cherry blossom",
    "flowers": "cherry blossom",
    "yard": "house",
    "baby": "baby",
    "dress": "dress",
    "picture": "framed picture",
    "paint": "artist palette",
    "morning": "sunrise",
    "puddle": "droplet",
    "puddles": "droplet",
    "friend": "busts in silhouette",
    "class": "school",
    "book": "open book",
    "bag": "backpack",
    "bottle": "baby bottle",
    "teeth": "tooth",
    "hands": "raising hands",
    "clean": "sparkles",
    "pencil": "pencil",
    "balloon": "balloon",
    "hippo": "hippopotamus",
    "wolf": "wolf",
    "hedgehog": "hedgehog",
    "game": "game die",
    "laugh": "face with tears of joy",
    "share": "handshake",
    "happy": "smiling face",
    "cold": "cold face",
    "quiet": "shushing face",
    "attention": "eyes",
    "favour": "folded hands",
    "favor": "folded hands",
    "help": "folded hands",
    "jump": "person bouncing ball",
    "play": "person bouncing ball",
    "tiger": "tiger",
    "lion": "lion",
    "bird": "bird",
    "cat": "cat face",
    "dog": "dog face",
    "umbrella": "umbrella",
    "sun": "sun",
    "school": "school",
    "boy": "boy",
    "girl": "girl",
    "teacher": "teacher",
    "coat": "coat",
    "hair": "person getting haircut",
    "tree": "deciduous tree",
    "sky": "sun behind cloud",
    "lake": "water wave",
    "doll": "teddy bear",
    "sweater": "coat",
    "mittens": "gloves",
    "listen": "ear",
    "draw": "artist palette",
    "talk": "speaking head",
    "tidy": "broom",
    "homework": "open book",
    "room": "bed",
    "music": "musical notes",
    "picnic": "basket",
    "party": "party popper",
    "weather": "sun behind cloud",
    "day": "sun with face",
    "meet": "handshake",
    "name": "name badge",
    "ready": "ok hand",
    "blocks": "brick",
    "block": "brick",
    "fun": "party popper",
    "job": "thumbs up",
    "slowly": "snail",
    "slow": "snail",
    "bob": "boy",
    "mike": "boy",
    "sarah": "girl",
    "linda": "girl",
    "fly": "bird",
    "push": "raised hand",
    "shout": "speaking head",
    "give": "thumbs up",
    "together": "busts in silhouette",
    "zip": "coat",
    "head": "speaking head",
    "toes": "foot",
    "toe": "foot",
    "body": "person standing",
    "cool": "smiling face with sunglasses",
    "tail": "lizard",
    "colourful": "artist palette",
    "colorful": "artist palette",
    "clean": "sparkles",
    "game": "video game",
    "feet": "foot",
    "gift": "wrapped gift",
    "ruler": "straight ruler",
    "join": "waving hand",
}

# Emoji that CLDR does not name with the textbook word.
_CODE = {
    "ten": "1f51f",
}


@lru_cache(maxsize=1)
def _index() -> dict[str, dict[str, str]]:
    path = Path(__file__).with_name("twemoji_words.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"en": payload.get("en") or {}, "zh": payload.get("zh") or {}}


def _english_key(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def _chinese_keys(text: str) -> list[str]:
    parts = re.split(r"[；;，,、/（）()\s.．。！!？?…·]+", text)
    keys: list[str] = []
    for part in parts:
        key = re.sub(r"\s+", "", part)
        if key:
            keys.append(key)
    return keys


def _is_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def lookup_code(en: str, zh: str = "") -> str | None:
    tables = _index()
    english = _english_key(en) if en and not _is_chinese(en) else ""
    if english and english in tables["en"]:
        return tables["en"][english]
    for key in _chinese_keys(zh or (en if _is_chinese(en) else "")):
        if key in tables["zh"]:
            return tables["zh"][key]
    if english:
        target = _ALIAS.get(english)
        if target and target in tables["en"]:
            return tables["en"][target]
        direct = _CODE.get(english)
        if direct:
            return direct
    return None


def has_emoji(en: str, zh: str = "") -> bool:
    return lookup_code(en, zh) is not None


def lookup_hit(en: str, zh: str = "") -> dict | None:
    code = lookup_code(en, zh)
    if not code:
        return None
    url = f"{_BASE}{code}.svg"
    title = (en or zh).strip() or "emoji"
    return {
        "url": url,
        "thumb": url,
        "source": "twemoji",
        "pageUrl": _PAGE,
        "title": title,
        "credit": "Twemoji · CC-BY 4.0",
    }
