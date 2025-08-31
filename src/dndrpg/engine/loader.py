from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple, Annotated, Union
import json
import yaml
from pydantic import TypeAdapter, Field as PField
from .models import Item, Weapon, Armor, Shield
from .campaigns import CampaignDefinition, StartingKit
from .schema_models import EffectDefinition  # blueprint

ItemUnion = Annotated[Union[Weapon, Armor, Shield, Item], PField(discriminator="type")]
ItemAdapter = TypeAdapter(ItemUnion)
CampaignAdapter = TypeAdapter(CampaignDefinition)
KitAdapter = TypeAdapter(StartingKit)
EffectAdapter = TypeAdapter(EffectDefinition)

def _load_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in [".yaml", ".yml"]:
        return yaml.safe_load(text) or {}
    return json.loads(text)

def _iter_files(root: Path, exts: Tuple[str,...]=(".json",".yaml",".yml")) -> Iterable[Path]:
    if not root.exists():
        return []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p

@dataclass
class ContentIndex:
    items_by_id: Dict[str, Item]
    weapons: Dict[str, Weapon]
    armors: Dict[str, Armor]
    shields: Dict[str, Shield]
    campaigns: Dict[str, CampaignDefinition]
    kits: Dict[str, StartingKit]
    effects: Dict[str, EffectDefinition]   # NEW

    def get_item(self, iid: str) -> Item:
        return self.items_by_id[iid]

    def clone_item(self, iid: str) -> Item:
        return self.items_by_id[iid].model_copy(deep=True)

    def get_effect(self, eid: str) -> EffectDefinition:  # NEW
        return self.effects[eid]

def load_content(base_dir: Path) -> ContentIndex:
    items_by_id: Dict[str, Item] = {}
    weapons: Dict[str, Weapon] = {}
    armors: Dict[str, Armor] = {}
    shields: Dict[str, Shield] = {}

    items_dir = base_dir / "items"
    for fp in _iter_files(items_dir):
        data = _load_file(fp)
        item = ItemAdapter.validate_python(data)
        if item.id in items_by_id:
            raise RuntimeError(f"Duplicate item id {item.id} in {fp}")
        items_by_id[item.id] = item
        if isinstance(item, Weapon):
            weapons[item.id] = item
        elif isinstance(item, Armor):
            armors[item.id] = item
        elif isinstance(item, Shield):
            shields[item.id] = item

    campaigns: Dict[str, CampaignDefinition] = {}
    for fp in _iter_files(base_dir / "campaigns"):
        data = _load_file(fp)
        camp = CampaignAdapter.validate_python(data)
        if camp.id in campaigns:
            raise RuntimeError(f"Duplicate campaign id {camp.id} in {fp}")
        campaigns[camp.id] = camp

    kits: Dict[str, StartingKit] = {}
    for fp in _iter_files(base_dir / "kits"):
        data = _load_file(fp)
        kit = KitAdapter.validate_python(data)
        if kit.id in kits:
            raise RuntimeError(f"Duplicate kit id {kit.id} in {fp}")
        kits[kit.id] = kit

    # Load effects
    effects: Dict[str, EffectDefinition] = {}
    effects_dir = base_dir / "effects"
    for fp in _iter_files(effects_dir):
        data = _load_file(fp)
        eff = EffectAdapter.validate_python(data)
        if eff.id in effects:
            raise RuntimeError(f"Duplicate effect id {eff.id} in {fp}")
        effects[eff.id] = eff

    return ContentIndex(
        items_by_id=items_by_id, weapons=weapons, armors=armors, shields=shields,
        campaigns=campaigns, kits=kits, effects=effects
    )