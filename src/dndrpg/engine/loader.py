from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple, Annotated, Union
import json
import yaml
from pydantic import TypeAdapter, Field as PField
from .models import Item, Weapon, Armor, Shield
from .campaigns import CampaignDefinition, StartingKit
from .schema_models import EffectDefinition, ResourceDefinition, ConditionDefinition, DeityDefinition

ItemUnion = Annotated[Union[Weapon, Armor, Shield, Item], PField(discriminator="type")]
ItemAdapter = TypeAdapter(ItemUnion)
CampaignAdapter = TypeAdapter(CampaignDefinition)
KitAdapter = TypeAdapter(StartingKit)
EffectAdapter = TypeAdapter(EffectDefinition)
ResourceAdapter = TypeAdapter(ResourceDefinition)
ConditionAdapter = TypeAdapter(ConditionDefinition)

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
    effects: Dict[str, EffectDefinition]
    resources: Dict[str, ResourceDefinition]
    conditions: Dict[str, ConditionDefinition]
    deities: Dict[str, DeityDefinition] # NEW

    def get_item(self, iid: str) -> Item:
        return self.items_by_id[iid]

    def clone_item(self, iid: str) -> Item:
        return self.items_by_id[iid].model_copy(deep=True)

    def get_effect(self, eid: str) -> EffectDefinition:
        return self.effects[eid]

    def get_resource(self, rid: str) -> ResourceDefinition:
        return self.resources[rid]
    def get_condition(self, cid: str) -> ConditionDefinition: return self.conditions[cid]

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

    # Resources
    resources: Dict[str, ResourceDefinition] = {}
    for fp in _iter_files(base_dir / "resources"):
        data = _load_file(fp)
        res = ResourceAdapter.validate_python(data)
        if res.id in resources:
            raise RuntimeError(f"Duplicate resource id {res.id} in {fp}")
        resources[res.id] = res

    conditions: Dict[str, ConditionDefinition] = {}
    for fp in _iter_files(base_dir / "conditions"):
        data = _load_file(fp)
        cond = ConditionAdapter.validate_python(data)
        if cond.id in conditions:
            raise RuntimeError(f"Duplicate condition id {cond.id} in {fp}")
        conditions[cond.id] = cond

    deities: Dict[str, DeityDefinition] = {}
    DeityAdapter = TypeAdapter(DeityDefinition) # Define adapter here
    for fp in _iter_files(base_dir / "deities"):
        data = _load_file(fp)
        deity = DeityAdapter.validate_python(data)
        if deity.id in deities:
            raise RuntimeError(f"Duplicate deity id {deity.id} in {fp}")
        deities[deity.id] = deity

    return ContentIndex(
        items_by_id=items_by_id, weapons=weapons, armors=armors, shields=shields,
        campaigns=campaigns, kits=kits, effects=effects, resources=resources,
        conditions=conditions, deities=deities
    )