from __future__ import annotations
from pathlib import Path
import sys

def frozen_base_dir() -> Path:
    # When packaged with PyInstaller --onefile, data is unpacked to sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # dev mode: src/dndrpg
    return Path(__file__).resolve().parent.parent # This should be src/dndrpg

def content_dir() -> Path:
    # In dev, this resolves to src/dndrpg/content
    # In onefile, use --add-data to embed content as "dndrpg/content"
    base = frozen_base_dir()
    return base / "content" # This should be content directly under src/dndrpg
