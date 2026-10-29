from __future__ import annotations

import json
from functools import lru_cache

from fastapi import HTTPException

from app.config import CATALOG_PATH
from app.keywords import picture_keyword


@lru_cache(maxsize=1)
def catalog() -> dict:
    if not CATALOG_PATH.is_file():
        raise HTTPException(status_code=500, detail="找不到 data/catalog.json")
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _sentences(piece: dict) -> list[dict]:
    rows = []
    for index, sentence in enumerate(piece.get("sentences") or []):
        en = str(sentence.get("en") or "").strip()
        zh = str(sentence.get("zh") or "").strip()
        if not en:
            continue
        rows.append({"index": index, "en": en, "zh": zh, "keyword": picture_keyword(en, zh)})
    return rows


def find_piece(piece_id: str) -> dict:
    book = catalog()
    for piece in book.get("pieces") or []:
        if piece.get("id") != piece_id:
            continue
        return {
            "id": piece["id"],
            "title": piece.get("title") or piece["id"],
            "file": piece.get("file") or "",
            "basedOn": piece.get("basedOn") or [],
            "introZh": str(piece.get("introZh") or "").strip(),
            "level": book.get("level") or "",
            "series": book.get("title") or "英语晨读",
            "sentences": _sentences(piece),
        }
    raise HTTPException(status_code=404, detail="没有这篇晨读")


def list_pieces() -> dict:
    from app.drafts import draft_count
    from app.video import get_video

    book = catalog()
    pieces = []
    for piece in book.get("pieces") or []:
        piece_id = str(piece.get("id") or "")
        edited_count = draft_count(piece_id)
        sentences = piece.get("sentences") or []
        video = get_video(piece_id)
        pieces.append(
            {
                "id": piece.get("id"),
                "title": piece.get("title"),
                "file": piece.get("file"),
                "basedOn": piece.get("basedOn") or [],
                "count": edited_count if edited_count is not None else len(sentences),
                "edited": edited_count is not None,
                "hasVideo": video is not None,
                "seconds": video["seconds"] if video else None,
            }
        )
    return {
        "title": book.get("title") or "英语晨读",
        "level": book.get("level") or "",
        "notes": book.get("notes") or "",
        "pieces": pieces,
    }


def get_piece(piece_id: str) -> dict:
    from app.drafts import DEFAULT_COVER, load_draft, normalize_cover, normalize_look, normalize_script, normalize_subtitle
    from app.handout import get_handout
    from app.tts import normalize_voices
    from app.video import get_video

    piece = find_piece(piece_id)
    draft = load_draft(piece_id)
    if draft is not None:
        script = normalize_script(str(draft.get("introZh") or ""), list(draft.get("sentences") or []))
        piece["introZh"] = script["introZh"]
        piece["coverTitle"] = normalize_cover(draft.get("coverTitle"))
        piece["subtitle"] = normalize_subtitle(draft.get("subtitle"), piece["title"])
        piece["theme"] = normalize_look(draft.get("theme"))
        piece["voices"] = normalize_voices(draft.get("voices"))
        piece["sentences"] = [
            {**row, "index": index, "picture": row["picture"]} for index, row in enumerate(script["sentences"])
        ]
        piece["edited"] = True
    else:
        piece["coverTitle"] = DEFAULT_COVER
        piece["subtitle"] = piece["title"]
        piece["theme"] = "sun"
        piece["voices"] = normalize_voices(None)
        piece["sentences"] = [{**row, "voice": "", "picture": None} for row in piece["sentences"]]
        piece["edited"] = False
    piece["video"] = get_video(piece_id)
    piece["handout"] = get_handout(piece_id)
    return piece
