from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from app.catalog import find_piece
from app.config import DATA_DIR
from app.keywords import picture_keyword
from app.pictures import media_file, public_meta
from app.tts import normalize_voices, optional_role

DRAFT_DIR = DATA_DIR / "drafts"
DEFAULT_COVER = "英语美文晨读 - 低年级"
LOOKS = {"sun", "meadow", "bubble", "candy", "rainbow", "zoo"}


def normalize_cover(value: object) -> str:
    text = " ".join(str(value or "").split())
    return text or DEFAULT_COVER


def normalize_subtitle(value: object, fallback: str) -> str:
    text = " ".join(str(value or "").split())
    base = " ".join(str(fallback or "").split()) or "晨读"
    return text or base


def normalize_look(value: object) -> str:
    theme = str(value or "").strip()
    return theme if theme in LOOKS else "sun"


def _path(piece_id: str) -> Path:
    return DRAFT_DIR / f"{Path(piece_id).name}.json"


def load_draft(piece_id: str) -> dict | None:
    path = _path(piece_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def draft_count(piece_id: str) -> int | None:
    draft = load_draft(piece_id)
    if draft is None:
        return None
    rows = [row for row in draft.get("sentences") or [] if str(row.get("en") or "").strip()]
    return len(rows)


def clear_draft(piece_id: str) -> None:
    _path(piece_id).unlink(missing_ok=True)


def _picture(raw: object, keyword: str) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = Path(str(raw.get("file") or "")).name
    if not name or media_file(name) is None:
        return None
    kind = "lottie" if name.lower().endswith(".json") else "image"
    return public_meta(
        {
            "file": name,
            "kind": kind,
            "source": str(raw.get("source") or ""),
            "credit": str(raw.get("credit") or ""),
            "keyword": keyword,
        }
    )


def normalize_script(intro_zh: str, sentences: list[dict]) -> dict:
    rows = []
    for raw in sentences:
        if not isinstance(raw, dict):
            continue
        en = str(raw.get("en") or "").strip()
        zh = str(raw.get("zh") or "").strip()
        if not en and not zh:
            continue
        keyword = " ".join(str(raw.get("keyword") or "").split())
        if not keyword and en:
            keyword = picture_keyword(en, zh)
        voice = str(raw.get("voice") or "").strip()
        rows.append(
            {
                "en": en,
                "zh": zh,
                "keyword": keyword,
                "voice": optional_role(voice, "en"),
                "picture": _picture(raw.get("picture"), keyword),
            }
        )
    if not any(row["en"] for row in rows):
        raise HTTPException(status_code=400, detail="至少留一句英文")
    return {"introZh": intro_zh.strip(), "sentences": rows}


def save_draft(
    piece_id: str,
    intro_zh: str,
    sentences: list[dict],
    voices: object = None,
    cover_title: object = "",
    theme: object = "",
    subtitle: object = "",
) -> dict:
    piece = find_piece(piece_id)
    script = normalize_script(intro_zh, sentences)
    chosen = normalize_voices(voices)
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    stored = {
        "introZh": script["introZh"],
        "coverTitle": normalize_cover(cover_title),
        "subtitle": normalize_subtitle(subtitle, piece["title"]),
        "theme": normalize_look(theme),
        "voices": chosen,
        "sentences": [
            {
                "en": row["en"],
                "zh": row["zh"],
                "keyword": row["keyword"],
                "voice": row["voice"],
                "picture": row["picture"],
            }
            for row in script["sentences"]
        ],
    }
    _path(piece_id).write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
    return stored


def script_for(piece_id: str, override: dict | None = None) -> dict:
    piece = find_piece(piece_id)
    if override is not None:
        script = normalize_script(str(override.get("introZh") or ""), list(override.get("sentences") or []))
        voices = normalize_voices(override.get("voices"))
        cover_title = normalize_cover(override.get("coverTitle"))
        subtitle = normalize_subtitle(override.get("subtitle"), piece["title"])
        theme = normalize_look(override.get("theme"))
    else:
        draft = load_draft(piece_id)
        if draft is None:
            script = {
                "introZh": piece["introZh"],
                "sentences": [
                    {"en": row["en"], "zh": row["zh"], "keyword": row["keyword"], "voice": "", "picture": None}
                    for row in piece["sentences"]
                ],
            }
            voices = normalize_voices(None)
            cover_title = DEFAULT_COVER
            subtitle = piece["title"]
            theme = "sun"
        else:
            script = normalize_script(str(draft.get("introZh") or ""), list(draft.get("sentences") or []))
            voices = normalize_voices(draft.get("voices"))
            cover_title = normalize_cover(draft.get("coverTitle"))
            subtitle = normalize_subtitle(draft.get("subtitle"), piece["title"])
            theme = normalize_look(draft.get("theme"))
    numbered = []
    for index, row in enumerate(script["sentences"]):
        if not row["en"]:
            continue
        numbered.append({**row, "index": index})
    return {
        "title": piece["title"],
        "series": piece["series"],
        "level": piece["level"],
        "introZh": script["introZh"],
        "coverTitle": cover_title,
        "subtitle": subtitle,
        "theme": theme,
        "voices": voices,
        "sentences": numbered,
    }
