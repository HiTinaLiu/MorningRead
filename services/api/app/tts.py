from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path

from fastapi import HTTPException

from app.config import DATA_DIR

logger = logging.getLogger(__name__)
_LETTERS = re.compile(r"[\w]", re.UNICODE)

TTS_DIR = DATA_DIR / "tts"
SLOW_RATE = "-20%"
BYTES_PER_MS = 48000 / 8 / 1000
TAIL_MS = 250

ROLES = (
    {"id": "xiaoxiao", "lang": "zh", "name": "晓晓", "detail": "女老师", "voice": "zh-CN-XiaoxiaoNeural"},
    {"id": "xiaoyi", "lang": "zh", "name": "晓伊", "detail": "女孩", "voice": "zh-CN-XiaoyiNeural"},
    {"id": "yunxi", "lang": "zh", "name": "云希", "detail": "男老师", "voice": "zh-CN-YunxiNeural"},
    {"id": "yunyang", "lang": "zh", "name": "云扬", "detail": "男声", "voice": "zh-CN-YunyangNeural"},
    {"id": "jenny", "lang": "en", "name": "Jenny", "detail": "美音女老师", "voice": "en-US-JennyNeural"},
    {"id": "aria", "lang": "en", "name": "Aria", "detail": "美音女声", "voice": "en-US-AriaNeural"},
    {"id": "guy", "lang": "en", "name": "Guy", "detail": "美音男老师", "voice": "en-US-GuyNeural"},
    {"id": "ana", "lang": "en", "name": "Ana", "detail": "美音小朋友", "voice": "en-US-AnaNeural"},
    {"id": "maisie", "lang": "en", "name": "Maisie", "detail": "英音小朋友", "voice": "en-GB-MaisieNeural"},
    {"id": "sonia", "lang": "en", "name": "Sonia", "detail": "英音女老师", "voice": "en-GB-SoniaNeural"},
)
DEFAULT_ROLES = {"zh": "xiaoxiao", "en": "jenny"}
_BY_ID = {role["id"]: role for role in ROLES}


def list_roles() -> dict:
    return {
        "zh": [_public_role(role) for role in ROLES if role["lang"] == "zh"],
        "en": [_public_role(role) for role in ROLES if role["lang"] == "en"],
        "defaults": dict(DEFAULT_ROLES),
    }


def _public_role(role: dict) -> dict:
    return {"id": role["id"], "lang": role["lang"], "name": role["name"], "detail": role["detail"]}


def optional_role(role_id: str, lang: str) -> str:
    role = _BY_ID.get(role_id)
    if role and role["lang"] == lang:
        return role["id"]
    return ""


def normalize_role(role_id: str, lang: str) -> str:
    role = _BY_ID.get(role_id)
    if role and role["lang"] == lang:
        return role["id"]
    return DEFAULT_ROLES[lang]


def normalize_voices(raw: object) -> dict[str, str]:
    found = raw if isinstance(raw, dict) else {}
    return {
        "zh": normalize_role(str(found.get("zh") or ""), "zh"),
        "en": normalize_role(str(found.get("en") or ""), "en"),
    }


def resolve_voice(role_id: str, lang: str) -> str:
    role = _BY_ID.get(normalize_role(role_id, lang))
    assert role is not None
    return str(role["voice"])


def speakable(text: str) -> bool:
    return bool(_LETTERS.search(text or ""))


def tts_key(text: str, voice: str, rate: str) -> str:
    return hashlib.sha1(f"{voice}|{rate}|{text}".encode("utf-8")).hexdigest()[:20]


def tts_file(key: str) -> Path:
    path = (TTS_DIR / f"{Path(key).stem}.mp3").resolve()
    if path.parent != TTS_DIR.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="找不到这段配音")
    return path


async def _synthesize(text: str, voice: str, rate: str) -> tuple[bytes, list[dict]]:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    audio = bytearray()
    words: list[dict] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 10000
            words.append(
                {
                    "text": chunk["text"],
                    "startMs": round(start),
                    "endMs": round(start + chunk["duration"] / 10000),
                }
            )
    if not audio:
        raise RuntimeError("没有收到音频")
    return bytes(audio), words


async def _speak(text: str, voice: str, rate: str) -> dict:
    if not speakable(text):
        raise RuntimeError(f"配音失败：这句没有可读的字（{text[:20]!r}）")
    key = tts_key(text, voice, rate)
    meta_path = TTS_DIR / f"{key}.json"
    audio_path = TTS_DIR / f"{key}.mp3"
    if meta_path.is_file() and audio_path.is_file():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    last: Exception | None = None
    for attempt in range(5):
        try:
            audio, words = await _synthesize(text, voice, rate)
            break
        except Exception as exc:
            last = exc
            logger.warning("TTS retry %s for %r (%s): %s", attempt + 1, text[:20], voice, exc)
            await asyncio.sleep(1.5 * (attempt + 1))
    else:
        raise RuntimeError(f"配音失败：{text[:20]}（{last}）")
    audio_ms = round(len(audio) / BYTES_PER_MS)
    speech_ms = min(audio_ms, words[-1]["endMs"] + TAIL_MS) if words else audio_ms
    meta = {"key": key, "voice": voice, "audioMs": audio_ms, "speechMs": speech_ms, "words": words}
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(audio)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


def speak_batch(requests: list[tuple[str, str, str, bool]]) -> list[dict]:
    """Synthesize (text, lang, role, slow) requests. Cached lines return immediately."""

    async def run() -> list[dict]:
        gate = asyncio.Semaphore(2)

        async def one(text: str, lang: str, role: str, slow: bool) -> dict:
            async with gate:
                return await _speak(text, resolve_voice(role, lang), SLOW_RATE if slow else "+0%")

        return await asyncio.gather(*(one(*request) for request in requests))

    return asyncio.run(run())
