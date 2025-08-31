from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from typing_extensions import Annotated
from pydantic import Field as PField

IDStr = Annotated[str, PField(pattern=r"^[a-z0-9_.:-]+$")]

class StartingKit(BaseModel):
    id: IDStr
    name: str
    items: List[str] = Field(default_factory=list)
    auto_equip: Dict[str, str] = Field(default_factory=dict)

class WealthRules(BaseModel):
    mode: Literal["kits","roll","fixed"] = "kits"
    fixed_gp: Optional[int] = None

class HouseRules(BaseModel):
    hp_first_level_max: bool = True
    point_buy: int = 28
    dr_policy: Literal["per_attack_total","per_packet"] = "per_attack_total"
    save_nat20_auto: bool = True
    save_nat1_auto_fail: bool = True

class AllowedLists(BaseModel):
    races: List[str] | str = "*"
    classes: List[str] | str = "*"
    feats: List[str] | str = "*"
    alignments: List[str] | str = "*"
    deities: List[str] | str = "*"
    domains: List[str] | str = "*"

class CampaignDefinition(BaseModel):
    id: IDStr
    name: str
    description: str = ""

    start_area: str = "overworld"
    start_coords: tuple[int,int] = (0, 0)
    start_time: str = "1000-01-01T08:00:00Z"
    start_level: int = 1

    allowed: AllowedLists = Field(default_factory=AllowedLists)
    wealth: WealthRules = Field(default_factory=WealthRules)
    rest_rules: Dict[str, dict] = Field(default_factory=dict)
    houserules: HouseRules = Field(default_factory=HouseRules)

    starting_equipment_packs: Dict[str, List[str]] = Field(default_factory=dict)
    encounters: Dict[str, str] = Field(default_factory=dict)
