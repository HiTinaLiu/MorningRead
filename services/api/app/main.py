from __future__ import annotations

import json
import logging
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.catalog import get_piece, list_pieces
from app.drafts import clear_draft, save_draft
from app.keywords import picture_keyword
from app.pictures import import_picture, media_file, public_meta, resolve_picture
from app.settings_store import get_settings, public_settings, save_settings
from app.tts import list_roles, speak_batch, tts_file
from app.handout import handout_events, handout_file
from app.video import preview_events, render_events, subtitles_file, video_file
from app.web_images import search_images

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="英语晨读")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SettingsIn(BaseModel):
    pixabayKey: str | None = None


class PictureIn(BaseModel):
    file: str = ""
    kind: str = "image"
    source: str = ""
    credit: str = ""
    keyword: str = ""


class SentenceIn(BaseModel):
    en: str = ""
    zh: str = ""
    keyword: str = ""
    voice: str = ""
    picture: PictureIn | None = None


class VoicesIn(BaseModel):
    zh: str = ""
    en: str = ""


class DraftIn(BaseModel):
    introZh: str = ""
    coverTitle: str = ""
    subtitle: str = ""
    theme: str = ""
    voices: VoicesIn = VoicesIn()
    sentences: list[SentenceIn] = []


class SampleIn(BaseModel):
    role: str = ""
    lang: str = "en"
    text: str = ""


class KeywordIn(BaseModel):
    en: str = ""
    zh: str = ""


class ImportIn(BaseModel):
    url: str
    source: str = ""
    credit: str = ""
    keyword: str = ""


def _script(body: DraftIn) -> dict:
    return {
        "introZh": body.introZh,
        "coverTitle": body.coverTitle,
        "subtitle": body.subtitle,
        "theme": body.theme,
        "voices": body.voices.model_dump(),
        "sentences": [row.model_dump() for row in body.sentences],
    }


def _event_stream(events: Iterator[dict]) -> Iterator[str]:
    import queue
    import threading

    mailbox: queue.Queue = queue.Queue()

    def pump() -> None:
        try:
            for event in events:
                mailbox.put(event)
        except Exception as exc:
            mailbox.put({"kind": "error", "message": f"生成失败：{exc}"})
        finally:
            mailbox.put(None)

    threading.Thread(target=pump, daemon=True).start()
    while True:
        event = mailbox.get()
        if event is None:
            break
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/catalog")
def read_catalog() -> dict:
    return list_pieces()


@app.get("/voices")
def voices() -> dict:
    return list_roles()


_SAMPLE = {"zh": "早上好。请跟我读。", "en": "Good morning. Let's read."}


@app.post("/tts/sample")
def tts_sample(body: SampleIn) -> dict:
    lang = "zh" if body.lang == "zh" else "en"
    text = " ".join(body.text.split()) or _SAMPLE[lang]
    meta = speak_batch([(text, lang, body.role, lang == "en")])[0]
    from app.config import HOST, PORT

    return {"url": f"http://{HOST}:{PORT}/tts/{meta['key']}.mp3", "audioMs": meta["audioMs"]}


@app.get("/pieces/{piece_id}")
def read_piece(piece_id: str) -> dict:
    return get_piece(piece_id)


@app.get("/settings")
def read_settings() -> dict:
    return public_settings(get_settings())


@app.put("/settings")
def write_settings(body: SettingsIn) -> dict:
    return public_settings(save_settings(body.pixabayKey))


@app.put("/pieces/{piece_id}/draft")
def write_draft(piece_id: str, body: DraftIn) -> dict:
    script = _script(body)
    save_draft(piece_id, script["introZh"], script["sentences"], script["voices"], script["coverTitle"], script["theme"], script["subtitle"])
    return get_piece(piece_id)


@app.delete("/pieces/{piece_id}/draft")
def remove_draft(piece_id: str) -> dict:
    clear_draft(piece_id)
    return get_piece(piece_id)


@app.post("/keywords")
def keywords(body: KeywordIn) -> dict:
    return {"keyword": picture_keyword(body.en, body.zh)}


@app.get("/pictures/resolve")
def resolve(keyword: str) -> dict:
    text = " ".join(keyword.split())
    if not text:
        raise HTTPException(status_code=400, detail="请先写配图词")
    found = public_meta(resolve_picture(text))
    if found is None:
        raise HTTPException(status_code=404, detail="没有找到配图")
    return found


@app.get("/images/search")
def image_search(q: str, limit: int = 8) -> dict:
    return {"hits": search_images(q, min(max(limit, 1), 12))}


@app.post("/pictures/import")
def import_hit(body: ImportIn) -> dict:
    try:
        return import_picture(body.url, body.source, body.credit, body.keyword)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"配图下载失败：{exc}") from exc


@app.post("/pieces/{piece_id}/preview/stream")
def preview_stream(piece_id: str, body: DraftIn) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(preview_events(piece_id, _script(body))),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/pieces/{piece_id}/video/stream")
def video_stream(piece_id: str, body: DraftIn) -> StreamingResponse:
    script = _script(body)
    save_draft(piece_id, script["introZh"], script["sentences"], script["voices"], script["coverTitle"], script["theme"], script["subtitle"])
    return StreamingResponse(
        _event_stream(render_events(piece_id, script)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/pieces/{piece_id}/handout/stream")
def handout_stream(piece_id: str, body: DraftIn) -> StreamingResponse:
    script = _script(body)
    save_draft(piece_id, script["introZh"], script["sentences"], script["voices"], script["coverTitle"], script["theme"], script["subtitle"])
    return StreamingResponse(
        _event_stream(handout_events(piece_id, script)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/pieces/{piece_id}/handout/file")
def read_handout_file(piece_id: str) -> FileResponse:
    return FileResponse(handout_file(piece_id), media_type="application/pdf", filename=f"{piece_id}-讲义.pdf")


@app.get("/pieces/{piece_id}/video")
def read_video(piece_id: str) -> dict:
    from app.video import get_video

    return {"video": get_video(piece_id)}


@app.get("/pieces/{piece_id}/video/file")
def read_video_file(piece_id: str) -> FileResponse:
    return FileResponse(video_file(piece_id), media_type="video/mp4", filename=f"{piece_id}.mp4")


@app.get("/pieces/{piece_id}/video/subtitles")
def read_subtitles(piece_id: str) -> FileResponse:
    return FileResponse(subtitles_file(piece_id), media_type="application/x-subrip", filename=f"{piece_id}.srt")


@app.get("/tts/{name}")
def read_tts(name: str) -> FileResponse:
    return FileResponse(tts_file(name), media_type="audio/mpeg")


@app.get("/media/{name}")
def read_media(name: str) -> FileResponse:
    path = media_file(name)
    if path is None:
        raise HTTPException(status_code=404, detail="找不到配图")
    media_type = "application/json" if path.suffix.lower() == ".json" else None
    return FileResponse(path, media_type=media_type)
