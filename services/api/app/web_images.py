from __future__ import annotations

import ipaddress
import json
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urlparse

import httpx
from fastapi import HTTPException

from app.settings_store import get_settings

log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

UA = "MorningRead/0.1 (local morning-read video)"
_MAX_BYTES = 12 * 1024 * 1024
_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


def search_images(query: str, limit: int = 12) -> list[dict]:
    text = " ".join(query.split())
    if not text:
        return []
    from app.twemoji import lookup_hit

    per_source = 4
    pixabay_key = (get_settings().get("pixabay_key") or "").strip()
    jobs = {
        "lottiefiles": lambda: _lottie(text, per_source),
        "pixabay": lambda: _pixabay(text, per_source, pixabay_key),
        "openverse": lambda: _openverse(text, per_source),
    }
    found: dict[str, list[dict]] = {name: [] for name in jobs}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                found[name] = future.result()
            except Exception as exc:
                log.warning("%s 图片搜索暂时失败，已改用其他来源：%s", name, exc)
                found[name] = []
    emoji = lookup_hit(text)
    buckets = [[emoji] if emoji else [], *(list(found[name]) for name in ("lottiefiles", "pixabay", "openverse"))]
    mixed: list[dict] = []
    seen: set[str] = set()
    while len(mixed) < limit and any(buckets):
        progressed = False
        for bucket in buckets:
            while bucket and bucket[0]["url"] in seen:
                bucket.pop(0)
            if not bucket or len(mixed) >= limit:
                continue
            hit = bucket.pop(0)
            seen.add(hit["url"])
            mixed.append(hit)
            progressed = True
        if not progressed:
            break
    return mixed


def _send(method: str, url: str, **kwargs) -> httpx.Response:
    kwargs.setdefault("timeout", 12)
    kwargs.setdefault("follow_redirects", True)
    headers = {"User-Agent": UA}
    headers.update(kwargs.pop("headers", {}))
    last: Exception | None = None
    for attempt in range(3):
        try:
            response = httpx.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError, httpx.TimeoutException) as exc:
            last = exc
            if attempt == 2:
                raise
            time.sleep(0.6 * (attempt + 1))
    raise last or RuntimeError("request failed")


def download_image(url: str) -> tuple[bytes, str]:
    safe = _public_https(url)
    try:
        response = _send("GET", safe, timeout=25, headers={"Accept": "image/*,application/json,*/*"})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"图片下载失败：{exc}") from exc
    _public_https(str(response.url))
    if len(response.content) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="图片太大")
    if len(response.content) < 32:
        raise HTTPException(status_code=400, detail="图片内容为空")
    if looks_like_lottie(response.content):
        return response.content, ".json"
    suffix = _suffix_for(response.headers.get("content-type") or "", str(response.url))
    return response.content, suffix


def looks_like_lottie(data: bytes) -> bool:
    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    return isinstance(payload, dict) and isinstance(payload.get("layers"), list)


def _suffix_for(content_type: str, url: str) -> str:
    kind = content_type.split(";")[0].strip().lower()
    if kind in _IMAGE_TYPES:
        return _IMAGE_TYPES[kind]
    path_ext = urlparse(url).path.rsplit(".", 1)
    ext = f".{path_ext[1].lower()}" if len(path_ext) == 2 else ""
    if ext == ".jpeg":
        ext = ".jpg"
    if ext == ".json" or kind == "application/json":
        return ".json"
    if ext in _IMAGE_TYPES.values():
        return ext
    raise HTTPException(status_code=400, detail="下载到的不是图片")


def _public_https(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        raise HTTPException(status_code=400, detail="只接受 https 图片地址")
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host.endswith(".local"):
        raise HTTPException(status_code=400, detail="不能使用本机地址")
    try:
        infos = socket.getaddrinfo(host, 443)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="图片地址无法解析") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(status_code=400, detail="不能使用内网图片地址")
    return url


def _lottie(query: str, limit: int) -> list[dict]:
    payload = {
        "query": (
            "query ($q: String!, $first: Int!) {"
            " searchPublicAnimations(query: $q, first: $first) {"
            " edges { node { name gifUrl jsonUrl } } } }"
        ),
        "variables": {"q": query[:80], "first": limit},
    }
    response = _send(
        "POST",
        "https://graphql.lottiefiles.com/",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    edges = (((response.json().get("data") or {}).get("searchPublicAnimations") or {}).get("edges")) or []
    hits = []
    page = f"https://lottiefiles.com/search?q={quote(query)}"
    for edge in edges:
        node = (edge or {}).get("node") or {}
        gif = node.get("gifUrl") or ""
        animation = node.get("jsonUrl") or gif
        if not str(animation).startswith("https://"):
            continue
        title = str(node.get("name") or query)
        hits.append(
            {
                "url": animation,
                "thumb": gif if str(gif).startswith("https://") else animation,
                "source": "lottiefiles",
                "pageUrl": page,
                "title": title,
                "credit": "LottieFiles",
            }
        )
    return hits


def _pixabay(query: str, limit: int, key: str) -> list[dict]:
    if not key:
        return []
    response = _send(
        "GET",
        "https://pixabay.com/api/",
        params={
            "key": key,
            "q": query,
            "image_type": "illustration",
            "safesearch": "true",
            "per_page": min(limit, 20),
        },
    )
    hits = []
    for item in response.json().get("hits") or []:
        url = item.get("webformatURL") or item.get("previewURL") or ""
        if not str(url).startswith("https://"):
            continue
        thumb = item.get("previewURL") or url
        hits.append(
            {
                "url": url,
                "thumb": thumb,
                "source": "pixabay",
                "pageUrl": item.get("pageURL") or "https://pixabay.com/",
                "title": str(item.get("tags") or query),
                "credit": "Pixabay",
            }
        )
    return hits


def _openverse(query: str, limit: int) -> list[dict]:
    response = _send(
        "GET",
        "https://api.openverse.org/v1/images/",
        params={"q": f"cartoon {query}", "page_size": limit, "category": "illustration"},
    )
    hits = []
    for item in response.json().get("results") or []:
        url = item.get("url") or ""
        if not str(url).startswith("https://"):
            continue
        creator = str(item.get("creator") or "").strip()
        license_name = str(item.get("license") or "").strip()
        credit = " · ".join(part for part in ("Openverse", creator, license_name) if part)
        hits.append(
            {
                "url": url,
                "thumb": item.get("thumbnail") or url,
                "source": "openverse",
                "pageUrl": item.get("foreign_landing_url") or "https://openverse.org/",
                "title": str(item.get("title") or query),
                "credit": credit,
            }
        )
    return hits
