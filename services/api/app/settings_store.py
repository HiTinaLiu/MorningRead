from __future__ import annotations

import json
import os

from app.config import DATA_DIR

_PATH = DATA_DIR / "settings.json"


def get_settings() -> dict[str, str]:
    stored: dict[str, str] = {}
    if _PATH.is_file():
        try:
            payload = json.loads(_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            stored = {str(key): str(value) for key, value in payload.items()}
    pixabay = stored.get("pixabay_key") or os.environ.get("PIXABAY_API_KEY", "")
    return {"pixabay_key": pixabay}


def save_settings(pixabay_key: str | None) -> dict[str, str]:
    current = get_settings()
    if pixabay_key is not None:
        current["pixabay_key"] = pixabay_key.strip()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_settings()


def public_settings(raw: dict[str, str]) -> dict:
    pixabay = raw.get("pixabay_key") or ""
    hint = f"••••{pixabay[-4:]}" if len(pixabay) >= 4 else ("已填写" if pixabay else "")
    return {"hasPixabayKey": bool(pixabay), "pixabayKeyHint": hint}
