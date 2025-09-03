from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from dndrpg.engine.models import Entity, Abilities, AbilityScore, Size, Weapon, Armor, Shield
from dndrpg.engine.loader import ContentIndex
from dndrpg.engine.effects_runtime import EffectsEngine
from dndrpg.engine.resources_runtime import ResourceEngine
from dndrpg.engine.conditions_runtime import ConditionsEngine
from dndrpg.engine.rulehooks_runtime import RuleHooksRegistry
from dndrpg.engine.state import GameState
from dndrpg.engine.skills import skill_points_at_level1, max_ranks, CLASS_SKILLS
from dndrpg.engine.spells import bonus_slots_from_mod, sorcerer_spells_known_from_cha, CLERIC_SPELLS_PER_DAY
from dndrpg.engine.prereq import eval_prereq, BuildView

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
    feat_choices: Dict[str, Dict[str, str]] = field(default_factory=dict)  # feat_id -> {choice_name: value}

def validate_character_picks(content: ContentIndex, picks: CharBuildState, campaign_id: str) -> tuple[bool, str]:
    # Validate Deity
    if picks.deity:
        deity_id = picks.deity # Assuming picks.deity is the ID
        if deity_id not in content.deities:
            return False, f"Selected deity '{deity_id}' does not exist."
        deity_def = content.deities[deity_id]

        # Validate Deity Alignment
        if picks.alignment not in deity_def.allowed_alignments:
            return False, f"Alignment '{picks.alignment}' is not allowed by deity '{deity_def.name}'."

        # Validate Cleric Domains against Deity's allowed domains
        if picks.clazz == "cleric" and picks.domains:
            for domain_id in picks.domains:
                if domain_id not in deity_def.allowed_domains:
                    return False, f"Domain '{domain_id}' is not allowed by deity '{deity_def.name}'."

    # Validate Campaign Allowed Lists
    if campaign_id not in content.campaigns:
        return False, f"Campaign '{campaign_id}' not found in content."
    campaign_allowed = content.campaigns[campaign_id].allowed

    # Validate Alignment against campaign allowed list
    if isinstance(campaign_allowed.alignments, list) and picks.alignment not in campaign_allowed.alignments:
        return False, f"Alignment '{picks.alignment}' is not allowed by the campaign."

    # Validate Domains against campaign allowed list
    if picks.clazz == "cleric" and picks.domains:
        if isinstance(campaign_allowed.domains, list):
            for domain_id in picks.domains:
                if domain_id not in campaign_allowed.domains:
                    return False, f"Domain '{domain_id}' is not allowed by the campaign."

    # Validate Skills
    temp_int_score = picks.abilities.get("int", 10)
    temp_int_mod = (temp_int_score - 10) // 2
    total_skill_points = skill_points_at_level1(picks.clazz, temp_int_mod, picks.race == "human")
    allocated_points = sum(picks.skills.values())

    if allocated_points > total_skill_points:
        return False, f"Allocated skill points ({allocated_points}) exceed available ({total_skill_points})."

    for skill_name, ranks in picks.skills.items():
        is_class_skill = skill_name in CLASS_SKILLS.get(picks.clazz, [])
        max_allowed_ranks = max_ranks(picks.level, is_class_skill)
        if ranks > max_allowed_ranks:
            return False, f"Skill '{skill_name}' has too many ranks ({ranks}). Max allowed: {max_allowed_ranks}."

    # Validate Feats
    picks_dict = {
        "abilities": picks.abilities,
        "class": picks.clazz, # Use "class" key for BuildView
        "level": picks.level,
        "race": picks.race,
        "feats": picks.feats,
        "skills": picks.skills,
        "alignment": picks.alignment,
        "deity": picks.deity,
        "domains": picks.domains,
    }
    build_view = BuildView(entity=None, picks=picks_dict)
    for feat_id in picks.feats:
        feat_def = content.effects.get(feat_id)
        if not feat_def:
            return False, f"Selected feat '{feat_id}' does not exist."
        if feat_def.prerequisites:
            can_take_feat, prereq_msg = eval_prereq(feat_def.prerequisites, build_view)
            if not can_take_feat:
                return False, f"Feat '{feat_def.name}' prerequisites not met: {prereq_msg}"

    # Validate Spells
    if picks.clazz == "cleric":
        wis_mod = (picks.abilities.get("wis", 10) - 10) // 2
        base_slots = CLERIC_SPELLS_PER_DAY.get(picks.level, [0]*10)
        bonus_slots = bonus_slots_from_mod(wis_mod, max_level=picks.level)

        for level, prepared_spells in picks.spells_prepared.items():
            total_slots = base_slots[level] + bonus_slots.get(level, 0)
            # Add domain slot
            if level > 0:
                total_slots += 1

            if len(prepared_spells) > total_slots:
                return False, f"Cleric prepared too many level {level} spells ({len(prepared_spells)}). Max allowed: {total_slots}."
            for spell_id in prepared_spells:
                if spell_id not in content.effects: # Assuming spells are effects
                    return False, f"Prepared spell '{spell_id}' does not exist."

    elif picks.clazz == "sorcerer":
        cha_mod = (picks.abilities.get("cha", 10) - 10) // 2
        expected_known = sorcerer_spells_known_from_cha(picks.level, cha_mod)

        for level, known_count in expected_known.items():
            # Count spells known for this level
            actual_known_count = 0
            for spell_id in picks.spells_known:
                # This is a simplification. A proper check would involve knowing the spell's level.
                # For now, we'll just count all known spells and compare to the total expected.
                # This assumes picks.spells_known only contains spells for levels they can cast.
                if spell_id in content.effects: # Assuming spells are effects
                    # Need to get spell level from content.effects[spell_id]
                    # For now, a basic check:
                    actual_known_count += 1
            
            # This comparison is flawed as it compares total known spells to per-level known.
            # A more robust solution would involve categorizing picks.spells_known by level.
            # For MVP, we'll just check if the total number of known spells exceeds the sum of expected known spells.
            total_expected_known = sum(expected_known.values())
            if len(picks.spells_known) > total_expected_known:
                return False, f"Sorcerer knows too many spells ({len(picks.spells_known)}). Max allowed: {total_expected_known}."
            
            for spell_id in picks.spells_known:
                if spell_id not in content.effects:
                    return False, f"Known spell '{spell_id}' does not exist."

    return True, "Character picks are valid."

def build_entity_from_state(content: ContentIndex, gs: GameState, picks: CharBuildState, campaign_id: str,
                            effects: EffectsEngine, resources: ResourceEngine, conditions: ConditionsEngine, hooks: RuleHooksRegistry) -> tuple[Entity | None, str | None]:
    # Validate character picks first
    is_valid, validation_message = validate_character_picks(content, picks, campaign_id)
    if not is_valid:
        return None, validation_message

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
    CLASS: Dict[str, Dict[str, Any]] = { # Added type hint for CLASS
        "fighter": {"hd":10, "bab":"full", "fort":"good","ref":"poor","will":"poor"},
        "cleric":  {"hd": 8, "bab":"three_quarter","fort":"good","ref":"poor","will":"good"},
        "sorcerer":{"hd": 4, "bab":"half","fort":"poor","ref":"poor","will":"good"},
        "monk":    {"hd": 8, "bab":"three_quarter","fort":"good","ref":"good","will":"good"},
    }
    def bab_from_prog(prog: str, lvl: int) -> int:
        return {"full":lvl,"three_quarter":(lvl*3)//4,"half":lvl//2}.get(prog, 0)
    cls = CLASS[picks.clazz]
    ent.base_attack_bonus = bab_from_prog(str(cls["bab"]), 1) # Explicitly cast to str
    ent.base_fort = 2 if cls["fort"]=="good" else 0
    ent.base_ref  = 2 if cls["ref"]=="good" else 0
    ent.base_will = 2 if cls["will"]=="good" else 0
    ent.hp_max = max(1, int(cls["hd"]) + ent.abilities.con.mod()) # Explicitly cast to int
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
    if picks.clazz == "cleric":
        if "res.turn_attempts" in content.resources:
            resources.create_from_definition("res.turn_attempts", owner_scope="entity", owner_entity_id=ent.id)
        
        # Add bonus spell slots from WIS
        wis_mod = ent.abilities.wis.mod()
        bonus_slots = bonus_slots_from_mod(wis_mod)
        for level, count in bonus_slots.items():
            if count > 0:
                res_id = f"res.spell_slots.cleric.{level}"
                if res_id in content.resources:
                    # Assuming create_from_definition can update existing or add to initial_current
                    # For now, we'll just create it with the bonus if it doesn't exist
                    # A more robust solution would be to update an existing resource's current/max
                    resources.create_from_definition(res_id, owner_scope="entity", owner_entity_id=ent.id, initial_current=count)

        # Domains for cleric (store on entity tags for later; or attach domain effects)
        # e.g., effect ids: domain.war.grant; domain.sun.grant
        for d in picks.domains or []:
            eff_id = f"domain.{d.lower()}.grant"
            if eff_id in content.effects:
                effects.attach(eff_id, ent, ent)

    elif picks.clazz == "sorcerer":
        cha_mod = ent.abilities.cha.mod()
        spells_known = sorcerer_spells_known_from_cha(picks.level, cha_mod)
        
        # Populate spells_known in the entity
        ent.spells_known = picks.spells_known # Use spells picked by the user in UI

        # Create spell slot resources for Sorcerer
        # Assuming a resource definition like "res.spell_slots.sorcerer.0", "res.spell_slots.sorcerer.1"
        for level, count in spells_known.items(): # Use spells_known to determine available levels
            if count > 0:
                res_id = f"res.spell_slots.sorcerer.{level}"
                if res_id in content.resources:
                    resources.create_from_definition(res_id, owner_scope="entity", owner_entity_id=ent.id, initial_current=count)

    # Feats: attach feats as effects (source 'feat'), content id e.g. "feat.power_attack"
    for feat_id in picks.feats:
        if feat_id in content.effects:
            # Pass feat choices to the effect attachment
            bound_choices = picks.feat_choices.get(feat_id)
            effects.attach(feat_id, ent, ent, bound_choices=bound_choices)

    # Skills: apply allocated skill ranks
    ent.skills = picks.skills

    # Skills & languages: store on entity (add fields if needed later)
    # For now, keep in a side-map (we can add fields to Entity later)
    # Return entity; GameState already exists; assign entity into state.player
    gs.player = ent
    return ent, None
