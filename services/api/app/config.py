from __future__ import annotations

import os
from pathlib import Path


def _repo_root() -> Path:
    env = os.environ.get("MORNINGREAD_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "catalog.json").is_file():
            return parent
    return here.parents[3]


def _downloads_root() -> Path:
    env = os.environ.get("MORNINGREAD_OUTPUT_DIR")
    if env:
        return Path(env).resolve()
    home = Path.home()
    for name in ("Downloads", "downloads"):
        folder = home / name
        if folder.is_dir():
            return (folder / "MorningRead").resolve()
    return (home / "Downloads" / "MorningRead").resolve()


ROOT = _repo_root()
CATALOG_PATH = ROOT / "data" / "catalog.json"
DATA_DIR = Path(os.environ.get("MORNINGREAD_DATA_DIR", ROOT / "services" / "api" / ".data")).resolve()
OUTPUT_DIR = _downloads_root()
VIDEO_APP = ROOT / "apps" / "video"
HOST = "127.0.0.1"
PORT = int(os.environ.get("MORNINGREAD_PORT", "8776"))
