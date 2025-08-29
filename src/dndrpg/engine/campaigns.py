from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List

class StartingKit(BaseModel):
    id: str
    name: str
    items: List[str] = Field(default_factory=list)
    auto_equip: Dict[str, str] = Field(default_factory=dict)  # slot -> item id

class CampaignDefinition(BaseModel):
    id: str
    name: str
    description: str = ""
    start_area: str = "overworld"
    start_coords: tuple[int, int] = (0, 0)
    start_time: str = "1000-01-01T08:00:00Z"
    start_level: int = 1
    allowed: Dict[str, List[str] | str] = Field(default_factory=lambda: {"races": "*", "classes": "*", "feats": "*", "alignments": "*"})
    starting_gold_policy: str = "kits"  # kits | roll
    starting_equipment_packs: Dict[str, List[str]] = Field(default_factory=dict)  # class -> [kit ids]
    rest_rules: Dict[str, dict] = Field(default_factory=dict)
    houserules: Dict[str, object] = Field(default_factory=dict)
    encounters: Dict[str, str] = Field(default_factory=dict)
