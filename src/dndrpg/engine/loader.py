from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple
import json
import yaml
from pydantic import TypeAdapter
from .models import Item, Weapon, Armor, Shield

# Discriminated union for items by "type"
from typing import Annotated, Union
from pydantic import Field as PField
ItemUnion = Annotated[Union[Weapon, Armor, Shield, Item], PField(discriminator="type")]
ItemAdapter = TypeAdapter(ItemUnion)

def _load_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in [".yaml", ".yml"]:
        return yaml.safe_load(text) or {}
    return json.loads(text)

def _iter_files(root: Path, exts: Tuple[str,...]=(".json",".yaml",".yml")) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p

@dataclass
class ContentIndex:
    items_by_id: Dict[str, Item]
    weapons: Dict[str, Weapon]
    armors: Dict[str, Armor]
    shields: Dict[str, Shield]

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
    if not items_dir.exists():
        items_dir.mkdir(parents=True, exist_ok=True)

    # Load all item files
    for fp in _iter_files(items_dir):
        data = _load_file(fp)
        try:
            item = ItemAdapter.validate_python(data)
        except Exception as e:
            raise RuntimeError(f"Failed parsing {fp}: {e}") from e

        if item.id in items_by_id:
            raise RuntimeError(f"Duplicate item id {item.id} in {fp}")

        items_by_id[item.id] = item
        if isinstance(item, Weapon):
            weapons[item.id] = item
        elif isinstance(item, Armor):
            armors[item.id] = item
        elif isinstance(item, Shield):
            shields[item.id] = item

    return ContentIndex(items_by_id=items_by_id, weapons=weapons, armors=armors, shields=shields)