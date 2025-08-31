import random
from pydantic import BaseModel, Field
from typing import Dict, List
from .models import Entity, Abilities, AbilityScore, Size, Item
from .loader import ContentIndex
from .effects_runtime import EffectInstance
from .resources_runtime import ResourceState
from .conditions_runtime import ConditionInstance  # NEW
from .zones_runtime import ZoneInstance

class GameState(BaseModel):
    player: Entity
    log: list[str] = Field(default_factory=list)
    active_effects: Dict[str, List[EffectInstance]] = Field(default_factory=dict)
    active_conditions: Dict[str, List[ConditionInstance]] = Field(default_factory=dict)  # NEW
    round_counter: int = 0
    # NEW: resource storage: map owner key -> list of ResourceState
    resources: Dict[str, List[ResourceState]] = Field(default_factory=dict)
    active_zones: Dict[str, List[ZoneInstance]] = Field(default_factory=dict)  # owner_entity_id -> zones
    seed: int = Field(default_factory=lambda: random.randint(0, 2**32 - 1))
    rng_state: tuple = Field(default_factory=lambda: random.getstate())

    def resources_summary(self) -> dict[str, int]:
        # Aggregate entity-scoped resources for player
        out: dict[str, int] = {}
        key = f"entity:{self.player.id}"
        for rs in self.resources.get(key, []):
            nm = rs.name or (rs.definition_id or "resource")
            out[nm] = rs.current
        # Sum Temp HP from all effect-instance scopes for this entity
        total_thp = 0
        for k, lst in self.resources.items():
            if not k.startswith("effect:"):
                continue
            for rs in lst:
                if rs.owner_entity_id == self.player.id and (rs.definition_id == "res.temp_hp" or (rs.name and "Temp" in rs.name)):
                    total_thp += rs.current
        if total_thp > 0:
            out["Temp HP"] = total_thp
        return out

    def initialize_rng(self):
        random.setstate(self.rng_state)

    def update_rng_state(self):
        self.rng_state = random.getstate()


def default_cleric_lvl1(content: ContentIndex) -> Entity:
    abilities = Abilities(
        str_=AbilityScore(base=14), dex=AbilityScore(base=12), con=AbilityScore(base=12),
        int_=AbilityScore(base=10), wis=AbilityScore(base=14), cha=AbilityScore(base=10),
    )
    # Clone items from content
    mace = content.clone_item("wp.mace.heavy")
    chain_shirt = content.clone_item("ar.chain_shirt")
    heavy_wooden_shield = content.clone_item("sh.heavy_wooden")
    holy_symbol = content.clone_item("it.holy_symbol")
    rations = content.clone_item("it.rations.5")

    inv: list[Item] = [mace, chain_shirt, heavy_wooden_shield, holy_symbol, rations]

    ent = Entity(
        id="pc.aria", name="Aria (Human Cleric 1)", level=1, size=Size.MEDIUM, abilities=abilities,
        base_attack_bonus=0, base_fort=2, base_ref=0, base_will=2,
        hp_max=9, hp_current=9, speed_land=30, inventory=inv,
        equipment={"armor": chain_shirt.id, "shield": heavy_wooden_shield.id, "main_hand": mace.id},
        classes={"cleric": 1},
        caster_levels={"cleric": 1},
        hd=1
    )
    return ent

def default_state(content: ContentIndex) -> GameState:
    game_state = GameState(player=default_cleric_lvl1(content))
    random.seed(game_state.seed)
    game_state.update_rng_state()
    return game_state

GameState.model_rebuild()
