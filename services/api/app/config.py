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


ROOT = _repo_root()
CATALOG_PATH = ROOT / "data" / "catalog.json"
DATA_DIR = Path(os.environ.get("MORNINGREAD_DATA_DIR", ROOT / "services" / "api" / ".data")).resolve()
VIDEO_APP = ROOT / "apps" / "video"
HOST = "127.0.0.1"
PORT = int(os.environ.get("MORNINGREAD_PORT", "8776"))
