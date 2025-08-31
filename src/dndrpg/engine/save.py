from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import List, Optional
from pydantic import BaseModel

SAVE_ROOT = Path.home() / ".dndrpg" / "saves"

@dataclass
class SaveMeta:
    slot_id: str
    campaign_id: str
    engine_version: str
    last_played_ts: float
    description: str
    rng_seed: Optional[int] = None
    mode: Optional[str] = None
    clock_seconds: Optional[float] = None

def _slot_dir(slot_id: str) -> Path:
    return SAVE_ROOT / slot_id

def ensure_save_root() -> None:
    SAVE_ROOT.mkdir(parents=True, exist_ok=True)

def list_saves() -> List[SaveMeta]:
    ensure_save_root()
    metas: List[SaveMeta] = []
    for slot in SAVE_ROOT.iterdir():
        if not slot.is_dir():
            continue
        meta_path = slot / "meta.json"
        if not meta_path.exists():
            continue
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        metas.append(SaveMeta(
            slot_id=slot.name,
            campaign_id=data.get("campaign_id","unknown"),
            engine_version=data.get("engine_version","0.0"),
            last_played_ts=data.get("last_played_ts",0.0),
            description=data.get("description",""),
            rng_seed=data.get("rng_seed"),
            mode=data.get("mode"),
            clock_seconds=data.get("clock_seconds")
        ))
    metas.sort(key=lambda m: m.last_played_ts, reverse=True)
    return metas

def latest_save() -> Optional[SaveMeta]:
    saves = list_saves()
    return saves[0] if saves else None

def save_game(slot_id: str, campaign_id: str, engine_version: str, state: BaseModel, description: str = "") -> None:
    ensure_save_root()
    sd = _slot_dir(slot_id)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "save.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
    meta = {
        "campaign_id": campaign_id,
        "engine_version": engine_version,
        "last_played_ts": time.time(),
        "description": description,
        "rng_seed": state.rng_seed if hasattr(state, 'rng_seed') else None,
        "mode": state.mode if hasattr(state, 'mode') else None,
        "clock_seconds": state.clock_seconds if hasattr(state, 'clock_seconds') else None,
    }
    (sd / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

def load_game(slot_id: str, model_cls) -> BaseModel:
    sd = _slot_dir(slot_id)
    data = json.loads((sd / "save.json").read_text(encoding="utf-8"))
    return model_cls.model_validate(data)

def delete_save(slot_id: str) -> None:
    sd = _slot_dir(slot_id)
    if not sd.exists():
        return
    for p in sd.iterdir():
        if p.is_file():
            p.unlink()
    sd.rmdir()
