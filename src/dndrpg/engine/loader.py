from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple, Annotated, Union
import json
import yaml
from pydantic import TypeAdapter, Field as PField
from .models import Item, Weapon, Armor, Shield
from .campaigns import CampaignDefinition, StartingKit

ItemUnion = Annotated[Union[Weapon, Armor, Shield, Item], PField(discriminator="type")]
ItemAdapter = TypeAdapter(ItemUnion)
CampaignAdapter = TypeAdapter(CampaignDefinition)
KitAdapter = TypeAdapter(StartingKit)

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

    def get_item(self, iid: str) -> Item:
        return self.items_by_id[iid]

    def clone_item(self, iid: str) -> Item:
        return self.items_by_id[iid].model_copy(deep=True)

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

    return ContentIndex(
        items_by_id=items_by_id, weapons=weapons, armors=armors, shields=shields,
        campaigns=campaigns, kits=kits
    )