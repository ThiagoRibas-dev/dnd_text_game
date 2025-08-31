from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from dndrpg.engine.models import Entity, Abilities, AbilityScore, Size, Weapon, Armor, Shield
from dndrpg.engine.loader import ContentIndex
from dndrpg.engine.effects_runtime import EffectsEngine
from dndrpg.engine.resources_runtime import ResourceEngine
from dndrpg.engine.conditions_runtime import ConditionsEngine
from dndrpg.engine.rulehooks_runtime import RuleHooksRegistry
from dndrpg.engine.state import GameState

@dataclass
class CharBuildState:
    name: str = "Hero"
    alignment: str = "neutral"
    deity: Optional[str] = None
    race: str = "human"
    clazz: str = "fighter"
    level: int = 1

    abilities: Dict[str, int] = field(default_factory=lambda: {"str":15,"dex":12,"con":14,"int":10,"wis":12,"cha":8})
    skills: Dict[str, int] = field(default_factory=dict)   # skill->ranks
    feats: Set[str] = field(default_factory=set)
    languages: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    spells_known: List[str] = field(default_factory=list)
    spells_prepared: Dict[int, List[str]] = field(default_factory=dict)  # level -> ids
    gear_ids: List[str] = field(default_factory=list)  # simple; kits will fill

def build_entity_from_state(content: ContentIndex, gs: GameState, picks: CharBuildState,
                            effects: EffectsEngine, resources: ResourceEngine, conditions: ConditionsEngine, hooks: RuleHooksRegistry) -> Entity:
    # Instantiate entity
    ab = Abilities(
        str_=AbilityScore(base=picks.abilities["str"]),
        dex=AbilityScore(base=picks.abilities["dex"]),
        con=AbilityScore(base=picks.abilities["con"]),
        int_=AbilityScore(base=picks.abilities["int"]),
        wis=AbilityScore(base=picks.abilities["wis"]),
        cha=AbilityScore(base=picks.abilities["cha"]),
    )
    ent = Entity(
        id="pc.hero", name=f"{picks.name} ({picks.race.title()} {picks.clazz.title()} 1)",
        level=1, size=Size.MEDIUM, abilities=ab
    )
    # Base class table (extend later)
    CLASS = {
        "fighter": {"hd":10, "bab":"full", "fort":"good","ref":"poor","will":"poor"},
        "cleric":  {"hd": 8, "bab":"three_quarter","fort":"good","ref":"poor","will":"good"},
        "sorcerer":{"hd": 4, "bab":"half","fort":"poor","ref":"poor","will":"good"},
        "monk":    {"hd": 8, "bab":"three_quarter","fort":"good","ref":"good","will":"good"},
    }
    def bab_from_prog(prog: str, lvl: int) -> int:
        return {"full":lvl,"three_quarter":(lvl*3)//4,"half":lvl//2}.get(prog, 0)
    cls = CLASS[picks.clazz]
    ent.base_attack_bonus = bab_from_prog(cls["bab"], 1)
    ent.base_fort = 2 if cls["fort"]=="good" else 0
    ent.base_ref  = 2 if cls["ref"]=="good" else 0
    ent.base_will = 2 if cls["will"]=="good" else 0
    ent.hp_max = max(1, cls["hd"] + ent.abilities.con.mod())
    ent.hp_current = ent.hp_max
    ent.classes = {picks.clazz: 1}
    if picks.clazz in {"cleric","sorcerer"}:
        ent.caster_levels = {picks.clazz: 1}
    ent.hd = 1

    # Inventory/equip via kits or picks.gear_ids
    inv = []
    for iid in picks.gear_ids:
        if iid in content.items_by_id:
            inv.append(content.items_by_id[iid].model_copy(deep=True))
    ent.inventory = inv
    # naive auto-equip based on id prefixes
    for item in inv:
        if isinstance(item, Armor) and item.armor_type in {"light","medium","heavy"}:
            ent.equipment["armor"] = item.id
        elif isinstance(item, Shield):
            ent.equipment["shield"] = item.id
        elif isinstance(item, Weapon):
            if "main_hand" not in ent.equipment:
                ent.equipment["main_hand"] = item.id
            elif "ranged" not in ent.equipment and item.kind != "melee":
                ent.equipment["ranged"] = item.id

    # Attach race/class passive effects (continuous/permanent)
    # Expect content/effects/races/*.yaml and content/effects/classes/*.yaml with ids like race.human, class.fighter.l1
    for race_eff in [f"race.{picks.race}"]:
        if race_eff in content.effects:
            effects.attach(race_eff, ent, ent)
    for cls_eff in [f"class.{picks.clazz}.l1"]:
        if cls_eff in content.effects:
            effects.attach(cls_eff, ent, ent)

    # Create class resources (turn attempts, spell slots, etc.)
    # Expect resources like res.turn_attempts; res.spell_slots.cleric.1
    if picks.clazz == "cleric" and "res.turn_attempts" in content.resources:
        resources.create_from_definition("res.turn_attempts", owner_scope="entity", owner_entity_id=ent.id)

    # Domains for cleric (store on entity tags for later; or attach domain effects)
    # e.g., effect ids: domain.war.grant; domain.sun.grant
    for d in picks.domains or []:
        eff_id = f"domain.{d.lower()}.grant"
        if eff_id in content.effects:
            effects.attach(eff_id, ent, ent)

    # Feats: attach feats as effects (source 'feat'), content id e.g. "feat.power_attack"
    for feat_id in picks.feats:
        if feat_id in content.effects:
            effects.attach(feat_id, ent, ent)

    # Skills & languages: store on entity (add fields if needed later)
    # For now, keep in a side-map (we can add fields to Entity later)
    # Return entity; GameState already exists; assign entity into state.player
    gs.player = ent
    return ent
