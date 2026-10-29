from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

from app.config import DATA_DIR, HOST, PORT
from app.twemoji import lookup_hit

log = logging.getLogger(__name__)
PIC_DIR = DATA_DIR / "pictures"

_RANK = {"lottiefiles": 0, "pixabay": 2, "openverse": 3}


def public_meta(meta: dict | None) -> dict | None:
    if not meta or not meta.get("file"):
        return None
    name = Path(str(meta["file"])).name
    if media_file(name) is None:
        return None
    kind = "lottie" if name.lower().endswith(".json") else str(meta.get("kind") or "image")
    if kind not in {"image", "lottie"}:
        kind = "image"
    return {
        "file": name,
        "kind": kind,
        "source": str(meta.get("source") or ""),
        "credit": str(meta.get("credit") or ""),
        "keyword": str(meta.get("keyword") or ""),
        "url": f"http://{HOST}:{PORT}/media/{name}",
    }


def media_file(name: str) -> Path | None:
    path = (PIC_DIR / Path(name).name).resolve()
    if path.parent != PIC_DIR.resolve() or not path.is_file():
        return None
    return path


def _slug(keyword: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")[:40]
    return slug or "pic"


def _cache_key(keyword: str) -> str:
    return hashlib.sha1(keyword.strip().lower().encode("utf-8")).hexdigest()[:12]


def _read_cache(keyword: str) -> dict | None:
    key = _cache_key(keyword)
    meta_path = PIC_DIR / f"{key}.json"
    if not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    name = str(meta.get("file") or "")
    if media_file(name) is None:
        return None
    return meta


def _write_cache(keyword: str, content: bytes, suffix: str, source: str, credit: str) -> dict:
    PIC_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(keyword)
    name = f"{_slug(keyword)}-{key}{suffix}"
    (PIC_DIR / name).write_bytes(content)
    meta = {
        "keyword": keyword,
        "file": name,
        "kind": "lottie" if suffix == ".json" else "image",
        "source": source,
        "credit": credit,
    }
    (PIC_DIR / f"{key}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


def _rank(hit: dict) -> tuple[int, int]:
    source = str(hit.get("source") or "")
    url = str(hit.get("url") or "").lower().split("?", 1)[0]
    json_first = 0 if source == "lottiefiles" and url.endswith(".json") else 1
    return (json_first, _RANK.get(source, 9))


def resolve_picture(keyword: str) -> dict | None:
    """Twemoji first. Otherwise Lottie JSON, then Pixabay, then Openverse."""
    text = " ".join(keyword.split())
    if not text:
        return None
    cached = _read_cache(text)
    if cached:
        return cached
    emoji = lookup_hit(text)
    if emoji:
        try:
            from app.web_images import download_image

            content, suffix = download_image(emoji["url"])
            return _write_cache(text, content, suffix, "twemoji", emoji.get("credit") or "Twemoji")
        except Exception as exc:
            log.warning("Twemoji 下载失败 %s：%s", text, exc)
    try:
        from app.web_images import download_image, search_images

        hits = [hit for hit in search_images(text, limit=8) if hit.get("source") != "twemoji"]
    except Exception as exc:
        log.warning("配图搜索失败 %s：%s", text, exc)
        return None
    hits.sort(key=_rank)
    for hit in hits:
        try:
            content, suffix = download_image(str(hit["url"]))
        except Exception as exc:
            log.warning("配图下载失败 %s：%s", hit.get("url"), exc)
            continue
        return _write_cache(text, content, suffix, str(hit.get("source") or "openverse"), str(hit.get("credit") or ""))
    return None


def import_picture(url: str, source: str, credit: str, keyword: str) -> dict:
    """Download one chosen search hit without replacing the keyword's automatic picture."""
    from app.web_images import download_image

    content, suffix = download_image(url)
    PIC_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    name = f"{_slug(keyword or source or 'pic')}-{key}{suffix}"
    (PIC_DIR / name).write_bytes(content)
    meta = public_meta(
        {
            "file": name,
            "kind": "lottie" if suffix == ".json" else "image",
            "source": source,
            "credit": credit,
            "keyword": keyword,
        }
    )
    if meta is None:
        raise RuntimeError("配图没有保存下来")
    return meta
