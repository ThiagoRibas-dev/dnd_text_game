from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

SETTINGS_PATH = Path.home() / ".dndrpg" / "settings.json"

class Settings(BaseModel):
    hp_first_level_max: bool = True
    point_buy: int = 28
    rng_seed_mode: str = "fixed"  # fixed | random | session
    default_content_pack: Optional[str] = None
    ui_show_expr_cache: bool = False

def load_settings() -> Settings:
    if SETTINGS_PATH.exists():
        return Settings.model_validate_json(SETTINGS_PATH.read_text(encoding="utf-8"))
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    s = Settings()
    SETTINGS_PATH.write_text(s.model_dump_json(indent=2), encoding="utf-8")
    return s

def save_settings(s: Settings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(s.model_dump_json(indent=2), encoding="utf-8")
