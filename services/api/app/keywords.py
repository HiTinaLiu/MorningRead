from __future__ import annotations

import re

# Classroom phrases whose picture is clearer than any single leftover word.
_PHRASES: tuple[tuple[str, str], ...] = (
    ("jumping rope", "person bouncing ball"),
    ("jump rope", "person bouncing ball"),
    ("sit-ups", "person lifting weights"),
    ("turn around", "counterclockwise arrows button"),
    ("good morning", "sunrise"),
    ("good afternoon", "sun with face"),
    ("good evening", "cityscape at dusk"),
    ("good night", "crescent moon"),
    ("nice to meet", "handshake"),
    ("happy birthday", "birthday cake"),
    ("stand up", "person standing"),
    ("sit down", "chair"),
    ("be quiet", "shushing face"),
    ("pay attention", "eyes"),
    ("listen carefully", "ear"),
    ("brush my teeth", "toothbrush"),
    ("brush your teeth", "toothbrush"),
    ("wash my hands", "soap"),
    ("wash my face", "soap"),
    ("brush my hair", "person getting haircut"),
    ("open your book", "open book"),
    ("close your book", "closed book"),
    ("show me your book", "open book"),
    ("take your seat", "seat"),
    ("ready for class", "school"),
    ("ready for school", "school"),
    ("ready to go", "backpack"),
    ("new day", "sunrise"),
    ("get up", "sunrise"),
    ("pencil case", "pencil"),
    ("teddy bear", "teddy bear"),
    ("toy car", "automobile"),
    ("t-shirt", "t shirt"),
    ("blow out", "candle"),
    ("make a wish", "glowing star"),
    ("clap our hands", "clapping hands"),
    ("flying a kite", "kite"),
    ("fly a kite", "kite"),
    ("what's the weather", "sun behind cloud"),
    ("what do you see", "eye"),
    ("what can you do", "flexed biceps"),
    ("what do you like", "red heart"),
    ("what do you want", "wrapped gift"),
    ("show me what you have", "eye"),
    ("what do you have", "backpack"),
    ("what am i doing", "thinking face"),
    ("who is that girl", "girl"),
    ("who is that woman", "woman"),
    ("who is that man", "man"),
    ("who is she", "woman"),
    ("who is he", "man"),
    ("this is me", "smiling face"),
    ("yes, i can", "ok hand"),
    ("let's go", "person walking"),
    ("try again", "counterclockwise arrows button"),
    ("good job", "thumbs up"),
    ("hold the rail", "raised hand"),
    ("give them a try", "thumbs up"),
    ("pass it slowly", "snail"),
    ("what's your name", "name badge"),
    ("my name is", "name badge"),
    ("zip it up", "coat"),
    ("go out", "person walking"),
    ("try them", "thumbs up"),
)

_STOP = {
    "a",
    "an",
    "the",
    "i",
    "you",
    "we",
    "they",
    "he",
    "she",
    "it",
    "me",
    "my",
    "your",
    "his",
    "her",
    "our",
    "their",
    "this",
    "that",
    "these",
    "those",
    "am",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "do",
    "does",
    "did",
    "can",
    "could",
    "will",
    "would",
    "shall",
    "should",
    "must",
    "may",
    "might",
    "let",
    "lets",
    "please",
    "and",
    "or",
    "but",
    "to",
    "of",
    "in",
    "on",
    "at",
    "for",
    "with",
    "from",
    "into",
    "onto",
    "over",
    "under",
    "up",
    "down",
    "out",
    "about",
    "again",
    "here",
    "there",
    "today",
    "now",
    "very",
    "too",
    "also",
    "just",
    "not",
    "no",
    "yes",
    "oh",
    "what",
    "who",
    "how",
    "where",
    "when",
    "which",
    "whose",
    "many",
    "much",
    "some",
    "any",
    "all",
    "us",
    "him",
    "them",
    "come",
    "look",
    "see",
    "away",
    "carefully",
    "so",
    "wow",
    "again",
    "let's",
    "dont",
    "don't",
    "it's",
    "that's",
    "there's",
    "i'm",
    "have",
    "has",
    "want",
    "like",
    "likes",
    "feel",
    "feels",
    "think",
    "use",
    "uses",
    "show",
    "get",
    "go",
    "try",
    "pass",
}

# Colors and soft adjectives. Used only when the sentence has no clearer noun.
_LOW = {
    "big",
    "little",
    "small",
    "good",
    "cute",
    "yummy",
    "wonderful",
    "new",
    "fat",
    "cold",
    "high",
    "early",
    "more",
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "black",
    "white",
    "pink",
    "purple",
    "brown",
    "clean",
    "happy",
    "strong",
    "fast",
    "slow",
    "slowly",
    "fun",
}

_REWRITE = {
    "barks": "dog",
    "bark": "dog",
    "favour": "help",
    "favor": "help",
    "teeth": "tooth",
    "happily": "dance",
    "flowers": "flower",
    "puddles": "puddle",
    "bob": "boy",
    "mike": "boy",
    "sarah": "girl",
    "linda": "girl",
    "apples": "apple",
}

_VERBS = {"fly", "run", "jump", "sing", "play", "eat", "walk", "push", "climb", "draw", "talk", "sleep", "give"}


def _forms(word: str) -> list[str]:
    forms = [word]
    if word.endswith("ing") and len(word) > 5:
        base = word[:-3]
        forms.extend([base, f"{base}e"])
        if len(base) > 2 and base[-1] == base[-2]:
            forms.append(base[:-1])
    elif word.endswith("ily") and len(word) > 4:
        forms.append(word[:-3] + "y")
    elif word.endswith("ies") and len(word) > 4:
        forms.append(word[:-3] + "y")
    elif word.endswith("es") and len(word) > 4:
        forms.extend([word[:-2], word[:-1]])
    elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        forms.append(word[:-1])
    return list(dict.fromkeys(forms))


def picture_keyword(en: str, _zh: str = "") -> str:
    """Pick the word a sentence should be illustrated with. Chinese stays on screen."""
    text = en.lower().replace("’", "'")
    candidates: list[str] = []
    phrase_query = ""
    matched = [item for item in _PHRASES if item[0] in text]
    if matched:
        _phrase, phrase_query = max(matched, key=lambda item: len(item[0]))
        candidates.append(phrase_query)
    for token in re.findall(r"[a-z']+", text):
        token = token.strip("'")
        if token and token not in _STOP:
            candidates.append(token)
    if not candidates:
        return "sun"

    from app.twemoji import has_emoji

    best = candidates[-1]
    best_score = -1
    for index, word in enumerate(candidates):
        forms = _forms(word)
        emoji = any(has_emoji(form) for form in forms)
        concrete = all(form not in _LOW for form in forms)
        verb = any(form in _VERBS for form in forms)
        score = (100 if emoji else 0) + (40 if concrete else 0) + index
        if word == phrase_query:
            score += 80
        if verb and word != phrase_query:
            score -= 25
        if score >= best_score:
            best_score = score
            best = next((form for form in forms if has_emoji(form)), word)
    return _REWRITE.get(best, best)
