"""A4 worksheet that matches the piece currently used for the video."""

from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from app.config import DATA_DIR, HOST, PORT
from app.drafts import script_for
from app.pictures import media_file, resolve_picture

PAGE_W, PAGE_H = 1240, 1754
MARGIN = 48
PER_PAGE = 4
FOLDER = DATA_DIR / "videos"

# Same ids and colors as apps/video/src/looks.ts.
LOOKS = {
    "sun": ("#fff6d8", "#3b2a1a", "#8a5a32", "#c4a27a", "#fffdf6", "#ffe0a3", "#f4a261", "#e76f51", "#2a9d8f", "#ffe8a3"),
    "meadow": ("#e9fbe3", "#1d3b24", "#4d7a45", "#9ec49a", "#fbfff8", "#c7efc0", "#2f9e44", "#f4a261", "#74c0fc", "#d3f9d8"),
    "bubble": ("#e7f6ff", "#16324f", "#3b6f99", "#9ec4e6", "#f8fcff", "#c5e4ff", "#1c7ed6", "#f06595", "#ffd43b", "#d0ebff"),
    "candy": ("#fff0f6", "#5c2142", "#a5527a", "#e7a8c4", "#fffafc", "#ffd0e4", "#e64980", "#be4bdb", "#ff922b", "#ffdeeb"),
    "rainbow": ("#fff9db", "#3d2c1e", "#9a6b2f", "#d4b07a", "#fffef8", "#ffe8a3", "#f76707", "#ae3ec9", "#12b886", "#fff3bf"),
    "zoo": ("#fff4e6", "#3d2914", "#8a5a2b", "#d4b48a", "#fffaf3", "#ffe0c2", "#e67700", "#2b8a3e", "#1c7ed6", "#ffe8cc"),
}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _rgb(value: str) -> tuple[int, int, int]:
    text = value.lstrip("#")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def _theme(theme_id: str) -> dict[str, tuple[int, int, int]]:
    raw = LOOKS.get(theme_id) or LOOKS["sun"]
    keys = ("paper", "ink", "muted", "faint", "card", "line", "accent", "accent2", "accent3", "soft")
    return {key: _rgb(value) for key, value in zip(keys, raw)}


def _piece_dir(piece_id: str) -> Path:
    return FOLDER / Path(piece_id).name


def get_handout(piece_id: str) -> dict | None:
    folder = _piece_dir(piece_id)
    meta_path = folder / "handout.json"
    if not meta_path.is_file():
        return None
    info = json.loads(meta_path.read_text(encoding="utf-8"))
    path = folder / str(info.get("file") or "")
    if not path.is_file() or path.suffix.lower() != ".pdf":
        return None
    created = info["createdAt"]
    return {
        **info,
        "url": f"http://{HOST}:{PORT}/pieces/{piece_id}/handout/file?v={created}",
        "path": str(path.resolve()),
    }


def handout_file(piece_id: str) -> Path:
    info = get_handout(piece_id)
    if info is None:
        raise HTTPException(status_code=404, detail="还没有讲义")
    return _piece_dir(piece_id) / info["file"]


def _fonts():
    import os

    from PIL import ImageFont

    windir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

    def open_font(names: tuple[str, ...], size: int):
        for name in names:
            path = windir / name
            if path.is_file():
                try:
                    return ImageFont.truetype(str(path), size)
                except OSError:
                    continue
        return ImageFont.load_default()

    return open_font


def _wrap(text: str, font, width: int) -> list[str]:
    text = " ".join(str(text or "").split())
    if not text:
        return []
    lines: list[str] = []
    current = ""

    def chunks(word: str) -> list[str]:
        if font.getlength(word) <= width:
            return [word]
        parts: list[str] = []
        buf = ""
        for char in word:
            trial = buf + char
            if buf and font.getlength(trial) > width:
                parts.append(buf)
                buf = char
            else:
                buf = trial
        if buf:
            parts.append(buf)
        return parts or [word]

    for word in text.split(" "):
        for piece in chunks(word):
            trial = piece if not current else f"{current} {piece}"
            if current and font.getlength(trial) > width:
                lines.append(current)
                current = piece
            else:
                current = trial
    if current:
        lines.append(current)
    return lines


def _svg_image(path: Path, size: int):
    import resvg_py
    from PIL import Image

    raw = resvg_py.svg_to_bytes(svg_path=str(path), width=size, height=size)
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def _load_art(path: Path | None, size: int):
    from PIL import Image

    if path is None or path.suffix.lower() == ".json":
        return None
    try:
        if path.suffix.lower() == ".svg":
            image = _svg_image(path, size * 2)
        else:
            image = Image.open(path).convert("RGBA")
    except Exception:
        return None
    image.thumbnail((size, size), Image.Resampling.LANCZOS)
    return image


def _picture_path(sentence: dict, cache: dict[str, Path | None]) -> Path | None:
    picture = sentence.get("picture")
    if isinstance(picture, dict) and picture.get("file"):
        found = media_file(str(picture["file"]))
        if found is not None:
            return found
    keyword = str(sentence.get("keyword") or "")
    if keyword not in cache:
        meta = resolve_picture(keyword) if keyword else None
        cache[keyword] = media_file(str(meta["file"])) if meta and meta.get("file") else None
    return cache[keyword]


def _paste_art(page, image, box: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int]) -> None:
    from PIL import Image, ImageDraw

    x, y, w, h = box
    canvas = Image.new("RGBA", (w, h), (*fill, 255))
    art = image.copy()
    art.thumbnail((w - 16, h - 16), Image.Resampling.LANCZOS)
    canvas.paste(art, ((w - art.width) // 2, (h - art.height) // 2), art)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((1, 1, w - 2, h - 2), radius=radius, fill=255)
    page.paste(canvas.convert("RGB"), (x, y), mask)


def _dots(draw, x: int, y: int, width: int, color: tuple[int, int, int]) -> None:
    cursor = x
    while cursor < x + width:
        draw.ellipse((cursor, y, cursor + 7, y + 7), fill=color)
        cursor += 18


def _pages(piece: dict, arts: list) -> list:
    from PIL import Image, ImageDraw

    open_font = _fonts()
    theme = _theme(str(piece.get("theme") or "sun"))
    cover = str(piece.get("coverTitle") or "英语美文晨读")
    subtitle = str(piece.get("subtitle") or piece.get("title") or "")
    sentences = piece["sentences"]
    page_count = max(1, (len(sentences) + PER_PAGE - 1) // PER_PAGE)
    title_font = open_font(("msyhbd.ttc", "msyh.ttc", "simhei.ttf"), 42)
    sub_font = open_font(("comicbd.ttf", "comic.ttf", "arialbd.ttf", "arial.ttf"), 34)
    en_font = open_font(("comicbd.ttf", "comic.ttf", "arialbd.ttf", "arial.ttf"), 34)
    zh_font = open_font(("msyh.ttc", "simhei.ttf"), 26)
    small_font = open_font(("msyh.ttc", "simhei.ttf"), 22)
    num_font = open_font(("comicbd.ttf", "arialbd.ttf", "arial.ttf"), 28)
    pages = []
    for page_index in range(page_count):
        image = Image.new("RGB", (PAGE_W, PAGE_H), theme["paper"])
        draw = ImageDraw.Draw(image)
        header = (MARGIN, MARGIN, PAGE_W - MARGIN, MARGIN + 168)
        draw.rounded_rectangle((header[0] + 10, header[1] + 10, header[2] + 10, header[3] + 10), radius=36, fill=theme["accent2"])
        draw.rounded_rectangle(header, radius=36, fill=theme["card"], outline=theme["accent"], width=6)
        title = cover if title_font.getlength(cover) < PAGE_W - 180 else cover[:18]
        title_w = title_font.getlength(title)
        draw.text(((PAGE_W - title_w) / 2, MARGIN + 28), title, font=title_font, fill=theme["ink"])
        pill = subtitle or piece.get("title") or ""
        pill_w = sub_font.getlength(pill) + 56
        pill_x = (PAGE_W - pill_w) / 2
        pill_box = (pill_x, MARGIN + 92, pill_x + pill_w, MARGIN + 146)
        draw.rounded_rectangle(pill_box, radius=28, fill=theme["accent"])
        draw.text((pill_x + 28, MARGIN + 98), pill, font=sub_font, fill=theme["card"])
        top = MARGIN + 196
        bottom = PAGE_H - MARGIN - 42
        gap = 16
        row_h = (bottom - top - gap * (PER_PAGE - 1)) // PER_PAGE
        chunk = sentences[page_index * PER_PAGE : (page_index + 1) * PER_PAGE]
        for row_index, sentence in enumerate(chunk):
            y = top + row_index * (row_h + gap)
            card = (MARGIN, y, PAGE_W - MARGIN, y + row_h)
            draw.rounded_rectangle(card, radius=28, fill=theme["card"], outline=theme["line"], width=4)
            badge = 54
            bx = MARGIN + 18
            by = y + (row_h - badge) // 2
            draw.ellipse((bx, by, bx + badge, by + badge), fill=theme["accent"])
            number = str(page_index * PER_PAGE + row_index + 1)
            nw = num_font.getlength(number)
            draw.text((bx + (badge - nw) / 2, by + 10), number, font=num_font, fill=theme["card"])
            pic = min(row_h - 28, 210)
            px = bx + badge + 16
            py = y + (row_h - pic) // 2
            draw.rounded_rectangle((px, py, px + pic, py + pic), radius=24, fill=theme["soft"])
            art = arts[page_index * PER_PAGE + row_index]
            if art is not None:
                _paste_art(image, art, (px + 8, py + 8, pic - 16, pic - 16), 20, theme["soft"])
            text_x = px + pic + 22
            text_w = PAGE_W - MARGIN - 22 - text_x
            english = _wrap(sentence["en"], en_font, text_w)
            chinese = _wrap(sentence["zh"], zh_font, text_w)
            block = len(english) * 44 + 8 + len(chinese) * 36 + 18 + 28 + 22
            text_y = y + max(16, (row_h - block) // 2)
            for line in english:
                draw.text((text_x, text_y), line, font=en_font, fill=theme["ink"])
                text_y += 44
            text_y += 4
            for line in chinese:
                draw.text((text_x, text_y), line, font=zh_font, fill=theme["muted"])
                text_y += 36
            text_y += 12
            draw.text((text_x, text_y), "写一写", font=small_font, fill=theme["accent2"])
            _dots(draw, text_x + 86, text_y + 12, text_w - 86, theme["faint"])
        draw.text((MARGIN, PAGE_H - MARGIN - 8), cover, font=small_font, fill=theme["muted"])
        mark = f"{page_index + 1} / {page_count}"
        draw.text((PAGE_W - MARGIN - small_font.getlength(mark), PAGE_H - MARGIN - 8), mark, font=small_font, fill=theme["muted"])
        pages.append(image)
    return pages


def handout_events(piece_id: str, override: dict | None = None):
    piece = script_for(piece_id, override)
    sentences = piece["sentences"]
    if not sentences:
        yield {"kind": "error", "message": "至少留一句英文"}
        return
    yield {"kind": "step", "id": "pictures", "label": "配图", "status": "active", "detail": "正在准备讲义配图"}
    cache: dict[str, Path | None] = {}
    arts = []
    for index, sentence in enumerate(sentences, start=1):
        path = _picture_path(sentence, cache)
        arts.append(_load_art(path, 420))
        yield {
            "kind": "step",
            "id": "pictures",
            "label": "配图",
            "status": "active",
            "detail": f"{index}/{len(sentences)} · {sentence['en']}",
        }
    yield {"kind": "step", "id": "pictures", "label": "配图", "status": "done", "detail": f"{len(sentences)} 张"}
    yield {"kind": "step", "id": "write", "label": "排版", "status": "active", "detail": "正在排 A4 讲义"}
    try:
        pages = _pages(piece, arts)
    except Exception as exc:
        yield {"kind": "error", "message": f"讲义没有排好：{exc}"}
        return
    folder = _piece_dir(piece_id)
    folder.mkdir(parents=True, exist_ok=True)
    pdf_path = folder / "handout.pdf"
    first, rest = pages[0], pages[1:]
    first.save(pdf_path, "PDF", resolution=150.0, save_all=bool(rest), append_images=rest)
    created = _now()
    info = {"file": pdf_path.name, "createdAt": created, "pages": len(pages), "sentences": len(sentences)}
    (folder / "handout.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    yield {"kind": "step", "id": "write", "label": "排版", "status": "done", "detail": f"{len(pages)} 页"}
    yield {"kind": "done", "record": get_handout(piece_id)}
