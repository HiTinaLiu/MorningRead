from __future__ import annotations

import json
import math
import shutil
import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from app.config import HOST, OUTPUT_DIR, PORT, VIDEO_APP
from app.drafts import script_for
from app.pictures import media_file, resolve_picture
from app.tts import speak_batch, speakable

VIDEO_DIR = OUTPUT_DIR / "videos"
API = f"http://{HOST}:{PORT}"
FPS = 30
LINE_GAP = 8
PAGE_PAD = 10
MIN_LINE = 15
BATCH = 6
INTRO_PAUSE_MS = 700


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _piece_dir(piece_id: str) -> Path:
    return VIDEO_DIR / Path(piece_id).name


def get_video(piece_id: str) -> dict | None:
    meta_path = _piece_dir(piece_id) / "video.json"
    if not meta_path.is_file():
        return None
    info = json.loads(meta_path.read_text(encoding="utf-8"))
    path = _piece_dir(piece_id) / info["file"]
    if not path.is_file():
        return None
    created = info["createdAt"]
    return {
        **info,
        "url": f"{API}/pieces/{piece_id}/video/file?v={created}",
        "subtitlesUrl": f"{API}/pieces/{piece_id}/video/subtitles?v={created}",
        "path": str(path.resolve()),
    }


def video_file(piece_id: str) -> Path:
    info = get_video(piece_id)
    if info is None:
        raise HTTPException(status_code=404, detail="还没有生成视频")
    return _piece_dir(piece_id) / info["file"]


def subtitles_file(piece_id: str) -> Path:
    info = get_video(piece_id)
    if info is None:
        raise HTTPException(status_code=404, detail="还没有生成视频")
    path = _piece_dir(piece_id) / info["subtitles"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="找不到字幕")
    return path


def _repeat_pause(text: str) -> int:
    words = [part for part in text.split() if part]
    return max(2400, len(words) * 700)


def _media(meta: dict | None) -> dict | None:
    if not meta:
        return None
    return {"url": f"{API}/media/{meta['file']}", "kind": meta["kind"]}


def _chosen_picture(sentence: dict, cache: dict[str, dict | None]) -> dict | None:
    picture = sentence.get("picture")
    if isinstance(picture, dict) and picture.get("file") and media_file(str(picture["file"])):
        return picture
    keyword = str(sentence.get("keyword") or "")
    if keyword not in cache:
        cache[keyword] = resolve_picture(keyword) if keyword else None
    return cache[keyword]


def prepare_events(piece_id: str, override: dict | None = None):
    piece = script_for(piece_id, override)
    sentences = piece["sentences"]
    pictures: dict[str, dict | None] = {}
    chosen: list[dict | None] = []
    yield {"kind": "step", "id": "pictures", "label": "配图", "status": "active", "detail": "正在准备"}
    for index, sentence in enumerate(sentences, start=1):
        found = _chosen_picture(sentence, pictures)
        chosen.append(found)
        source = found["source"] if found else "无配图"
        yield {
            "kind": "step",
            "id": "pictures",
            "label": "配图",
            "status": "active",
            "detail": f"{index}/{len(sentences)} · {sentence['en']} · {source}",
        }
    yield {"kind": "step", "id": "pictures", "label": "配图", "status": "done", "detail": f"{len(sentences)} 张"}

    lines: list[dict] = []
    voices = piece["voices"]
    if speakable(piece["introZh"]):
        lines.append(
            {
                "id": "intro",
                "text": piece["introZh"],
                "lang": "zh",
                "role": voices["zh"],
                "slow": False,
                "pauseMs": INTRO_PAUSE_MS,
            }
        )
    for sentence in sentences:
        lines.append(
            {
                "id": f"s{sentence['index']}",
                "text": sentence["en"],
                "lang": "en",
                "role": sentence.get("voice") or voices["en"],
                "slow": True,
                "pauseMs": _repeat_pause(sentence["en"]),
                "zh": sentence["zh"],
            }
        )
    requests = [(line["text"], line["lang"], line["role"], line["slow"]) for line in lines if speakable(line["text"])]
    spoken: dict[str, dict] = {}
    yield {"kind": "step", "id": "tts", "label": "配音", "status": "active", "detail": "正在准备"}
    try:
        for start in range(0, len(requests), BATCH):
            chunk = [line for line in lines if speakable(line["text"])][start : start + BATCH]
            for line, meta in zip(chunk, speak_batch(requests[start : start + BATCH])):
                spoken[line["id"]] = meta
            yield {
                "kind": "step",
                "id": "tts",
                "label": "配音",
                "status": "active",
                "detail": f"{min(start + BATCH, len(requests))}/{len(requests)} 句",
            }
    except RuntimeError as exc:
        yield {"kind": "error", "message": str(exc)}
        return
    yield {"kind": "step", "id": "tts", "label": "配音", "status": "done", "detail": f"{len(spoken)} 句"}

    pages = []
    intro = spoken.get("intro")
    if intro:
        pages.append(
            {
                "id": "intro",
                "kind": "intro",
                "index": 0,
                "title": piece["title"],
                "keyword": "",
                "image": None,
                "credit": "",
                "line": {
                    "id": "intro",
                    "lang": "zh",
                    "text": "",
                    "subtitle": "",
                    "audioUrl": f"{API}/tts/{intro['key']}.mp3",
                    "audioMs": intro["audioMs"],
                    "speechMs": intro["speechMs"],
                    "pauseMs": INTRO_PAUSE_MS,
                    "words": intro["words"],
                },
            }
        )
    number = 0
    for sentence, picture in zip(sentences, chosen):
        meta = spoken.get(f"s{sentence['index']}")
        if meta is None:
            continue
        number += 1
        pages.append(
            {
                "id": f"s{sentence['index']}",
                "kind": "sentence",
                "index": number,
                "title": piece["title"],
                "keyword": sentence["keyword"],
                "image": _media(picture),
                "credit": (picture or {}).get("credit") or "",
                "line": {
                    "id": f"s{sentence['index']}",
                    "lang": "en",
                    "text": sentence["en"],
                    "subtitle": sentence["zh"],
                    "audioUrl": f"{API}/tts/{meta['key']}.mp3",
                    "audioMs": meta["audioMs"],
                    "speechMs": meta["speechMs"],
                    "pauseMs": _repeat_pause(sentence["en"]),
                    "words": meta["words"],
                },
            }
        )
    props = {
        "title": piece["title"],
        "series": piece["series"],
        "level": piece["level"],
        "coverTitle": piece["coverTitle"],
        "subtitle": piece["subtitle"],
        "theme": piece["theme"],
        "pages": pages,
    }
    yield {"kind": "props", "props": props}


def _node_problem() -> str | None:
    if shutil.which("node") is None:
        return "没有找到 Node.js，导出视频需要它"
    if not (VIDEO_APP / "node_modules" / "remotion").is_dir():
        return "视频模块还没装好，请先在 apps/video 里运行 npm install"
    return None


def _run_render(props: dict, output: Path, step: dict, result: dict):
    props_path = output.parent / f"{output.stem}.props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    yield {"kind": "step", **step, "status": "active", "detail": "正在打包画面"}
    process = subprocess.Popen(
        [shutil.which("node") or "node", str(VIDEO_APP / "render.mjs"), str(props_path), str(output)],
        cwd=VIDEO_APP,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail: deque[str] = deque(maxlen=12)
    duration = 0.0
    shown = -1
    assert process.stdout is not None
    for raw in process.stdout:
        text = raw.strip()
        if not text:
            continue
        try:
            message = json.loads(text)
        except json.JSONDecodeError:
            tail.append(text)
            continue
        if not isinstance(message, dict):
            continue
        stage = message.get("stage")
        if stage == "meta":
            duration = float(message.get("seconds") or 0)
        elif stage in {"bundle", "browser", "render"}:
            percent = int(float(message.get("progress") or 0) * 100)
            if percent != shown:
                shown = percent
                label = {"bundle": "正在打包画面", "browser": "正在准备浏览器", "render": "正在渲染"}[stage]
                yield {"kind": "step", **step, "status": "active", "detail": f"{label} {percent}%"}
    code = process.wait()
    props_path.unlink(missing_ok=True)
    if code != 0 or not output.is_file():
        detail = " / ".join(list(tail)[-3:]) or f"退出码 {code}"
        yield {"kind": "error", "message": f"渲染失败：{detail}"}
        result["ok"] = False
        return
    result["ok"] = True
    result["seconds"] = duration


def _stamped(prefix: str, suffix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}{suffix}"


def _drop_old(folder: Path, pattern: str, keep: str) -> None:
    for old in folder.glob(pattern):
        if old.stem != Path(keep).stem:
            try:
                old.unlink()
            except OSError:
                pass


def _frames(ms: float) -> int:
    return math.floor(ms * FPS / 1000 + 0.5)


def _stamp(frame: int) -> str:
    total = frame * 1000 // FPS
    hours, rest = divmod(total, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def _srt(props: dict) -> str:
    entries: list[str] = []
    cursor = 0
    for page in props["pages"]:
        line = page["line"]
        speech = max(MIN_LINE, _frames(line["speechMs"]))
        if page.get("kind") != "intro":
            text = line["text"]
            if line.get("subtitle"):
                text = f"{text}\n{line['subtitle']}"
            entries.append(f"{len(entries) + 1}\n{_stamp(cursor)} --> {_stamp(cursor + speech)}\n{text}\n")
        cursor += speech + _frames(line["pauseMs"]) + LINE_GAP + PAGE_PAD
    return "\n".join(entries)


def preview_events(piece_id: str, override: dict | None = None):
    result: dict = {}
    for event in prepare_events(piece_id, override):
        if event["kind"] == "props":
            result["props"] = event["props"]
        else:
            yield event
            if event["kind"] == "error":
                return
    yield {"kind": "done", "record": result["props"]}


def render_events(piece_id: str, override: dict | None = None):
    problem = _node_problem()
    if problem:
        yield {"kind": "error", "message": problem}
        return
    result: dict = {}
    for event in prepare_events(piece_id, override):
        if event["kind"] == "props":
            result["props"] = event["props"]
        else:
            yield event
            if event["kind"] == "error":
                return
    props = result.get("props")
    if not props or not props["pages"]:
        yield {"kind": "error", "message": "这篇晨读没有可以朗读的句子"}
        return
    folder = _piece_dir(piece_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = _stamped("read", ".mp4")
    output = folder / name
    rendered: dict = {}
    yield from _run_render(props, output, {"id": "render", "label": "渲染视频"}, rendered)
    if not rendered.get("ok"):
        return
    duration = rendered["seconds"]
    yield {"kind": "step", "id": "render", "label": "渲染视频", "status": "done", "detail": f"{round(duration)} 秒"}
    subtitles = output.with_suffix(".srt")
    subtitles.write_text(_srt(props), encoding="utf-8")
    info = {
        "file": name,
        "subtitles": subtitles.name,
        "createdAt": _now(),
        "seconds": duration,
        "pages": len(props["pages"]),
    }
    (folder / "video.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    _drop_old(folder, "read-*.mp4", name)
    _drop_old(folder, "read-*.srt", name)
    yield {"kind": "done", "record": get_video(piece_id)}
