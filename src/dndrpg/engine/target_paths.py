from __future__ import annotations
from typing import Dict, List, Literal, Optional

# Re-importing these for type hints, as they are used in the metadata
from .schema_models import ModifierOperator

class TargetPathInfo:
    """
    Metadata for a targetPath prefix, used for schema validation and runtime checks.
    """
    def __init__(self,
                 prefix: str,
                 description: str,
                 allowed_operators: Optional[List[ModifierOperator]] = None,
                 requires_bonus_type: bool = False,
                 value_type: Literal["int", "float", "bool", "str", "any"] = "any",
                 example_paths: Optional[List[str]] = None):
        self.prefix = prefix
        self.description = description
        self.allowed_operators = allowed_operators
        self.requires_bonus_type = requires_bonus_type
        self.value_type = value_type
        self.example_paths = example_paths

# Central registry for target paths and their metadata
TARGET_PATH_REGISTRY: Dict[str, TargetPathInfo] = {
    "abilities": TargetPathInfo(
        prefix="abilities",
        description="Core ability scores (str, dex, con, int, wis, cha) and their modifiers.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["abilities.str.score", "abilities.dex.mod"]
    ),
    "ac": TargetPathInfo(
        prefix="ac",
        description="Armor Class components (total, touch, flat-footed) and their breakdown.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["ac.total", "ac.dodge", "ac.natural_armor"]
    ),
    "save": TargetPathInfo(
        prefix="save",
        description="Saving throws (fort, ref, will).",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["save.fort", "save.ref", "save.will"]
    ),
    "resist": TargetPathInfo(
        prefix="resist",
        description="Energy resistances (fire, cold, acid, electricity, sonic, force, negative, positive).",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False, # Resistances typically stack, but not with bonus types
        value_type="int",
        example_paths=["resist.fire", "resist.cold"]
    ),
    "dr": TargetPathInfo(
        prefix="dr",
        description="Damage Reduction (e.g., dr.physical, dr.slashing).",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False, # DR typically stacks, but not with bonus types
        value_type="int",
        example_paths=["dr.physical", "dr.slashing"]
    ),
    "speed": TargetPathInfo(
        prefix="speed",
        description="Movement speeds (e.g., speed.land, speed.fly).",
        allowed_operators=["add", "subtract", "set", "multiply", "min", "max", "cap", "clamp"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["speed.land", "speed.fly"]
    ),
    "senses": TargetPathInfo(
        prefix="senses",
        description="Special senses (e.g., senses.darkvision, senses.blindsense).",
        allowed_operators=["add", "set", "min", "max", "grantTag", "removeTag"], # Add/remove tags for senses
        requires_bonus_type=False,
        value_type="bool", # Or specific sense value
        example_paths=["senses.darkvision", "senses.blindsense"]
    ),
    "tags": TargetPathInfo(
        prefix="tags",
        description="Entity tags (e.g., tags.prone, tags.invisible).",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["tags.prone", "tags.invisible"]
    ),
    "resources": TargetPathInfo(
        prefix="resources",
        description="Dynamic resources (e.g., spell slots, daily uses, ki points).",
        allowed_operators=["add", "subtract", "set", "min", "max", "cap", "clamp"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["resources.spell_slots.level1", "resources.turn_attempts"]
    ),
    "attack": TargetPathInfo(
        prefix="attack",
        description="Attack bonuses (melee, ranged, touch).",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["attack.melee_bonus", "attack.ranged_bonus"]
    ),
    "bab": TargetPathInfo(
        prefix="bab",
        description="Base Attack Bonus.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["bab.total"]
    ),
    # Add other prefixes as needed, e.g., "hp", "thp", "nonlethal_damage"
    "hp": TargetPathInfo(
        prefix="hp",
        description="Hit Points (current, max).",
        allowed_operators=["add", "subtract", "set", "min", "max", "cap", "clamp"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["hp.current", "hp.max"]
    ),
    "thp": TargetPathInfo(
        prefix="thp",
        description="Temporary Hit Points.",
        allowed_operators=["add", "subtract", "set", "min", "max", "cap", "clamp"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["thp.current"]
    ),
    "nonlethal_damage": TargetPathInfo(
        prefix="nonlethal_damage",
        description="Nonlethal damage taken.",
        allowed_operators=["add", "subtract", "set", "min", "max", "cap", "clamp"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["nonlethal_damage.current"]
    ),
    "size": TargetPathInfo(
        prefix="size",
        description="Entity size category.",
        allowed_operators=["set"], # Size is usually set, not added/subtracted
        requires_bonus_type=False,
        value_type="str", # e.g., "fine", "diminutive", "tiny", "small", "medium", "large", "huge", "gargantuan", "colossal"
        example_paths=["size.category"]
    ),
    "reach": TargetPathInfo(
        prefix="reach",
        description="Melee reach.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["reach.melee"]
    ),
    "weight": TargetPathInfo(
        prefix="weight",
        description="Entity weight (for encumbrance).",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="float",
        example_paths=["weight.carried"]
    ),
    "caster_level": TargetPathInfo(
        prefix="caster_level",
        description="Caster level for specific spellcasting classes or general.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["caster_level.cleric", "caster_level.total"]
    ),
    "initiator_level": TargetPathInfo(
        prefix="initiator_level",
        description="Initiator level for martial adepts.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["initiator_level.total"]
    ),
    "hd": TargetPathInfo(
        prefix="hd",
        description="Hit Dice.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["hd.total"]
    ),
    "level": TargetPathInfo(
        prefix="level",
        description="Overall character level.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["level.total"]
    ),
    "class_level": TargetPathInfo(
        prefix="class_level",
        description="Level in a specific class.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["class_level.fighter", "class_level.cleric"]
    ),
    "feats": TargetPathInfo(
        prefix="feats",
        description="Feats granted or removed.",
        allowed_operators=["grantTag", "removeTag"], # Using grantTag/removeTag for feats
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["feats.power_attack"]
    ),
    "spells": TargetPathInfo(
        prefix="spells",
        description="Spells known or available.",
        allowed_operators=["grantTag", "removeTag"], # Using grantTag/removeTag for spells
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["spells.grease"]
    ),
    "skills": TargetPathInfo(
        prefix="skills",
        description="Skill ranks or modifiers.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["skills.acrobatics", "skills.perception"]
    ),
    "immunities": TargetPathInfo(
        prefix="immunities",
        description="Immunities to damage types or conditions.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["immunities.fire", "immunities.poison"]
    ),
    "vulnerabilities": TargetPathInfo(
        prefix="vulnerabilities",
        description="Vulnerabilities to damage types.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["vulnerabilities.fire"]
    ),
    "crit_range": TargetPathInfo(
        prefix="crit_range",
        description="Critical threat range of a weapon or attack.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["crit_range.weapon.longsword"]
    ),
    "crit_multiplier": TargetPathInfo(
        prefix="crit_multiplier",
        description="Critical multiplier of a weapon or attack.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["crit_multiplier.weapon.longsword"]
    ),
    "damage_dice": TargetPathInfo(
        prefix="damage_dice",
        description="Damage dice of a weapon or attack.",
        allowed_operators=["set"], # Usually set, not modified
        requires_bonus_type=False,
        value_type="str", # e.g., "1d8", "2d6"
        example_paths=["damage_dice.weapon.longsword"]
    ),
    "damage_bonus": TargetPathInfo(
        prefix="damage_bonus",
        description="Bonus damage to attacks.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=True,
        value_type="int",
        example_paths=["damage_bonus.melee", "damage_bonus.ranged"]
    ),
    "spell_slots": TargetPathInfo(
        prefix="spell_slots",
        description="Spell slots per level.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["spell_slots.level1", "spell_slots.level9"]
    ),
    "domains": TargetPathInfo(
        prefix="domains",
        description="Cleric domains.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["domains.fire", "domains.water"]
    ),
    "alignment": TargetPathInfo(
        prefix="alignment",
        description="Character alignment.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="str", # e.g., "lawful_good", "chaotic_evil"
        example_paths=["alignment.moral", "alignment.ethical"]
    ),
    "deity": TargetPathInfo(
        prefix="deity",
        description="Character's chosen deity.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="str",
        example_paths=["deity.name"]
    ),
    "hp_regen": TargetPathInfo(
        prefix="hp_regen",
        description="Hit point regeneration per round/turn.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["hp_regen.amount"]
    ),
    "fast_healing": TargetPathInfo(
        prefix="fast_healing",
        description="Fast healing per round/turn.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["fast_healing.amount"]
    ),
    "immunities_to_condition": TargetPathInfo(
        prefix="immunities_to_condition",
        description="Immunities to specific conditions.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["immunities_to_condition.prone", "immunities_to_condition.stunned"]
    ),
    "vulnerabilities_to_condition": TargetPathInfo(
        prefix="vulnerabilities_to_condition",
        description="Vulnerabilities to specific conditions.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["vulnerabilities_to_condition.prone"]
    ),
    "spell_resistance": TargetPathInfo(
        prefix="spell_resistance",
        description="Spell Resistance.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["spell_resistance.total"]
    ),
    "channel_energy": TargetPathInfo(
        prefix="channel_energy",
        description="Cleric's Channel Energy ability.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["channel_energy.uses", "channel_energy.dice"]
    ),
    "turn_undead": TargetPathInfo(
        prefix="turn_undead",
        description="Cleric's Turn Undead ability.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["turn_undead.uses", "turn_undead.level_check_bonus"]
    ),
    "rebuke_undead": TargetPathInfo(
        prefix="rebuke_undead",
        description="Cleric's Rebuke Undead ability.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["rebuke_undead.uses", "rebuke_undead.level_check_bonus"]
    ),
    "flurry_of_blows": TargetPathInfo(
        prefix="flurry_of_blows",
        description="Monk's Flurry of Blows ability.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["flurry_of_blows.active"]
    ),
    "unarmed_strike_damage": TargetPathInfo(
        prefix="unarmed_strike_damage",
        description="Monk's unarmed strike damage.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="str", # e.g., "1d6", "1d8"
        example_paths=["unarmed_strike_damage.dice"]
    ),
    "ac_bonus": TargetPathInfo(
        prefix="ac_bonus",
        description="Monk's AC bonus.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["ac_bonus.monk"]
    ),
    "fast_movement": TargetPathInfo(
        prefix="fast_movement",
        description="Monk's fast movement bonus.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["fast_movement.speed_bonus"]
    ),
    "evasion": TargetPathInfo(
        prefix="evasion",
        description="Monk's Evasion ability.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["evasion.active"]
    ),
    "mighty_strike": TargetPathInfo(
        prefix="mighty_strike",
        description="Crusader's Mighty Strike ability.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["mighty_strike.damage_bonus"]
    ),
    "steely_resolve": TargetPathInfo(
        prefix="steely_resolve",
        description="Crusader's Steely Resolve ability.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["steely_resolve.damage_reduction"]
    ),
    "furious_counterstrike": TargetPathInfo(
        prefix="furious_counterstrike",
        description="Crusader's Furious Counterstrike ability.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["furious_counterstrike.attack_bonus"]
    ),
    "smite": TargetPathInfo(
        prefix="smite",
        description="Paladin/Crusader's Smite ability.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["smite.damage_bonus"]
    ),
    "soulmelds": TargetPathInfo(
        prefix="soulmelds",
        description="Totemist's soulmelds shaped.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["soulmelds.lammasu_wing_charge"]
    ),
    "essentia": TargetPathInfo(
        prefix="essentia",
        description="Totemist's essentia pool.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["essentia.current", "essentia.max"]
    ),
    "totem_bind": TargetPathInfo(
        prefix="totem_bind",
        description="Totemist's totem bind ability.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["totem_bind.active"]
    ),
    "rebind": TargetPathInfo(
        prefix="rebind",
        description="Totemist's rebind ability.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["rebind.available"]
    ),
    "maneuvers": TargetPathInfo(
        prefix="maneuvers",
        description="Martial maneuvers known or readied.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["maneuvers.strike_of_the_broken_shield"]
    ),
    "stances": TargetPathInfo(
        prefix="stances",
        description="Martial stances known or active.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["stances.iron_guard_s_glare"]
    ),
    "spell_slots_per_day": TargetPathInfo(
        prefix="spell_slots_per_day",
        description="Number of spell slots per day for a given level.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["spell_slots_per_day.level1", "spell_slots_per_day.level9"]
    ),
    "spells_known": TargetPathInfo(
        prefix="spells_known",
        description="Number of spells known for a given level.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["spells_known.level1", "spells_known.level9"]
    ),
    "prepared_spells": TargetPathInfo(
        prefix="prepared_spells",
        description="Number of prepared spells for a given level.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["prepared_spells.level1", "prepared_spells.level9"]
    ),
    "bonus_feats": TargetPathInfo(
        prefix="bonus_feats",
        description="Number of bonus feats available.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["bonus_feats.total"]
    ),
    "skill_points": TargetPathInfo(
        prefix="skill_points",
        description="Skill points available per level.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["skill_points.total"]
    ),
    "gold": TargetPathInfo(
        prefix="gold",
        description="Character's gold pieces.",
        allowed_operators=["add", "subtract", "set"],
        requires_bonus_type=False,
        value_type="float",
        example_paths=["gold.current"]
    ),
    "xp": TargetPathInfo(
        prefix="xp",
        description="Character's experience points.",
        allowed_operators=["add", "subtract", "set"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["xp.current"]
    ),
    "alignment_change": TargetPathInfo(
        prefix="alignment_change",
        description="Changes to alignment (e.g., for specific effects).",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="str",
        example_paths=["alignment_change.moral", "alignment_change.ethical"]
    ),
    "condition_duration": TargetPathInfo(
        prefix="condition_duration",
        description="Duration of a specific condition.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["condition_duration.prone", "condition_duration.stunned"]
    ),
    "resource_capacity": TargetPathInfo(
        prefix="resource_capacity",
        description="Capacity of a specific resource.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["resource_capacity.ki_points"]
    ),
    "resource_current": TargetPathInfo(
        prefix="resource_current",
        description="Current value of a specific resource.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["resource_current.ki_points"]
    ),
    "zone_duration": TargetPathInfo(
        prefix="zone_duration",
        description="Duration of a specific zone.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["zone_duration.grease_area"]
    ),
    "zone_size": TargetPathInfo(
        prefix="zone_size",
        description="Size of a specific zone.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="int",
        example_paths=["zone_size.grease_area"]
    ),
    "item_property": TargetPathInfo(
        prefix="item_property",
        description="Properties of an item (e.g., damage, weight).",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["item_property.longsword.damage", "item_property.chain_shirt.ac_bonus"]
    ),
    "weapon_property": TargetPathInfo(
        prefix="weapon_property",
        description="Properties specific to weapons.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["weapon_property.longsword.crit_range"]
    ),
    "armor_property": TargetPathInfo(
        prefix="armor_property",
        description="Properties specific to armor.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["armor_property.chain_shirt.max_dex_bonus"]
    ),
    "shield_property": TargetPathInfo(
        prefix="shield_property",
        description="Properties specific to shields.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["shield_property.heavy_wooden_shield.ac_bonus"]
    ),
    "feat_property": TargetPathInfo(
        prefix="feat_property",
        description="Properties of a feat.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["feat_property.power_attack.damage_multiplier"]
    ),
    "spell_property": TargetPathInfo(
        prefix="spell_property",
        description="Properties of a spell.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["spell_property.fireball.damage_dice"]
    ),
    "condition_property": TargetPathInfo(
        prefix="condition_property",
        description="Properties of a condition.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["condition_property.prone.ac_penalty"]
    ),
    "resource_property": TargetPathInfo(
        prefix="resource_property",
        description="Properties of a resource.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["resource_property.ki_points.refresh_rate"]
    ),
    "zone_property": TargetPathInfo(
        prefix="zone_property",
        description="Properties of a zone.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["zone_property.grease_area.dc"]
    ),
    "task_property": TargetPathInfo(
        prefix="task_property",
        description="Properties of a task.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["task_property.craft_item.progress_per_day"]
    ),
    "race_property": TargetPathInfo(
        prefix="race_property",
        description="Properties of a race.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["race_property.human.bonus_skill_points"]
    ),
    "class_property": TargetPathInfo(
        prefix="class_property",
        description="Properties of a class.",
        allowed_operators=["add", "subtract", "set", "multiply", "divide"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["class_property.fighter.bonus_feats_at_level"]
    ),
    "alignment_property": TargetPathInfo(
        prefix="alignment_property",
        description="Properties related to alignment.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="str",
        example_paths=["alignment_property.lawful_good.aura_strength"]
    ),
    "deity_property": TargetPathInfo(
        prefix="deity_property",
        description="Properties related to a deity.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="str",
        example_paths=["deity_property.bahamut.favored_weapon"]
    ),
    "game_state": TargetPathInfo(
        prefix="game_state",
        description="Global game state variables.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["game_state.current_round", "game_state.weather"]
    ),
    "player_character": TargetPathInfo(
        prefix="player_character",
        description="Properties of the player character.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["player_character.name", "player_character.gold"]
    ),
    "npc": TargetPathInfo(
        prefix="npc",
        description="Properties of a non-player character.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["npc.goblin_1.hp", "npc.goblin_1.status"]
    ),
    "party": TargetPathInfo(
        prefix="party",
        description="Properties of the player's party.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["party.members", "party.average_level"]
    ),
    "encounter": TargetPathInfo(
        prefix="encounter",
        description="Properties of the current encounter.",
        allowed_operators=["add", "subtract", "set", "min", "max"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["encounter.round_number", "encounter.enemies_remaining"]
    ),
    "world": TargetPathInfo(
        prefix="world",
        description="Properties of the game world.",
        allowed_operators=["set"],
        requires_bonus_type=False,
        value_type="any",
        example_paths=["world.current_area", "world.time_of_day"]
    ),
    "inventory": TargetPathInfo(
        prefix="inventory",
        description="Inventory management (adding/removing items).",
        allowed_operators=["grantTag", "removeTag"], # Using grantTag/removeTag for items
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["inventory.has_item.potion_of_healing"]
    ),
    "equipment": TargetPathInfo(
        prefix="equipment",
        description="Equipped items.",
        allowed_operators=["set"], # Setting equipped item in a slot
        requires_bonus_type=False,
        value_type="str", # Item ID
        example_paths=["equipment.main_hand", "equipment.armor"]
    ),
    "feats_granted": TargetPathInfo(
        prefix="feats_granted",
        description="Feats granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["feats_granted.power_attack"]
    ),
    "spells_granted": TargetPathInfo(
        prefix="spells_granted",
        description="Spells granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["spells_granted.fireball"]
    ),
    "abilities_granted": TargetPathInfo(
        prefix="abilities_granted",
        description="Special abilities granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["abilities_granted.darkvision"]
    ),
    "conditions_applied": TargetPathInfo(
        prefix="conditions_applied",
        description="Conditions applied by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["conditions_applied.prone"]
    ),
    "resources_granted": TargetPathInfo(
        prefix="resources_granted",
        description="Resources granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["resources_granted.ki_points"]
    ),
    "zones_created": TargetPathInfo(
        prefix="zones_created",
        description="Zones created by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["zones_created.grease_area"]
    ),
    "tasks_granted": TargetPathInfo(
        prefix="tasks_granted",
        description="Tasks granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["tasks_granted.craft_magic_item"]
    ),
    "rule_hooks_granted": TargetPathInfo(
        prefix="rule_hooks_granted",
        description="Rule hooks granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["rule_hooks_granted.on_damage_taken_reduce"]
    ),
    "immunities_granted": TargetPathInfo(
        prefix="immunities_granted",
        description="Immunities granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["immunities_granted.fire"]
    ),
    "vulnerabilities_granted": TargetPathInfo(
        prefix="vulnerabilities_granted",
        description="Vulnerabilities granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["vulnerabilities_granted.cold"]
    ),
    "resistances_granted": TargetPathInfo(
        prefix="resistances_granted",
        description="Resistances granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["resistances_granted.fire"]
    ),
    "dr_granted": TargetPathInfo(
        prefix="dr_granted",
        description="Damage Reduction granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["dr_granted.physical"]
    ),
    "speed_granted": TargetPathInfo(
        prefix="speed_granted",
        description="Speed bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["speed_granted.fast_movement"]
    ),
    "senses_granted": TargetPathInfo(
        prefix="senses_granted",
        description="Senses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["senses_granted.darkvision"]
    ),
    "ac_granted": TargetPathInfo(
        prefix="ac_granted",
        description="AC bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["ac_granted.shield_of_faith"]
    ),
    "save_granted": TargetPathInfo(
        prefix="save_granted",
        description="Save bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["save_granted.resistance"]
    ),
    "attack_granted": TargetPathInfo(
        prefix="attack_granted",
        description="Attack bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["attack_granted.bless"]
    ),
    "bab_granted": TargetPathInfo(
        prefix="bab_granted",
        description="BAB bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["bab_granted.divine_power"]
    ),
    "caster_level_granted": TargetPathInfo(
        prefix="caster_level_granted",
        description="Caster level bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["caster_level_granted.orange_prismatic_ray"]
    ),
    "initiator_level_granted": TargetPathInfo(
        prefix="initiator_level_granted",
        description="Initiator level bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["initiator_level_granted.stance_of_alacrity"]
    ),
    "hd_granted": TargetPathInfo(
        prefix="hd_granted",
        description="Hit Dice granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["hd_granted.draconic_aura"]
    ),
    "level_granted": TargetPathInfo(
        prefix="level_granted",
        description="Level bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["level_granted.epic_destiny"]
    ),
    "class_level_granted": TargetPathInfo(
        prefix="class_level_granted",
        description="Class level bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["class_level_granted.prestige_class_level"]
    ),
    "skills_granted": TargetPathInfo(
        prefix="skills_granted",
        description="Skill bonuses granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["skills_granted.skill_focus"]
    ),
    "spell_slots_granted": TargetPathInfo(
        prefix="spell_slots_granted",
        description="Spell slots granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["spell_slots_granted.extra_slot"]
    ),
    "domains_granted": TargetPathInfo(
        prefix="domains_granted",
        description="Domains granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["domains_granted.fire_domain"]
    ),
    "alignment_granted": TargetPathInfo(
        prefix="alignment_granted",
        description="Alignment changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["alignment_granted.chaos_aura"]
    ),
    "deity_granted": TargetPathInfo(
        prefix="deity_granted",
        description="Deity changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["deity_granted.divine_favor"]
    ),
    "hp_regen_granted": TargetPathInfo(
        prefix="hp_regen_granted",
        description="HP regeneration granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["hp_regen_granted.troll_regeneration"]
    ),
    "fast_healing_granted": TargetPathInfo(
        prefix="fast_healing_granted",
        description="Fast healing granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["fast_healing_granted.ring_of_regeneration"]
    ),
    "spell_resistance_granted": TargetPathInfo(
        prefix="spell_resistance_granted",
        description="Spell resistance granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["spell_resistance_granted.cloak_of_resistance"]
    ),
    "channel_energy_granted": TargetPathInfo(
        prefix="channel_energy_granted",
        description="Channel Energy ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["channel_energy_granted.holy_aura"]
    ),
    "turn_undead_granted": TargetPathInfo(
        prefix="turn_undead_granted",
        description="Turn Undead ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["turn_undead_granted.sun_domain"]
    ),
    "rebuke_undead_granted": TargetPathInfo(
        prefix="rebuke_undead_granted",
        description="Rebuke Undead ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["rebuke_undead_granted.death_domain"]
    ),
    "flurry_of_blows_granted": TargetPathInfo(
        prefix="flurry_of_blows_granted",
        description="Flurry of Blows ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["flurry_of_blows_granted.monk_level"]
    ),
    "unarmed_strike_damage_granted": TargetPathInfo(
        prefix="unarmed_strike_damage_granted",
        description="Unarmed strike damage granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["unarmed_strike_damage_granted.monk_level"]
    ),
    "ac_bonus_granted": TargetPathInfo(
        prefix="ac_bonus_granted",
        description="AC bonus granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["ac_bonus_granted.monk_ac_bonus"]
    ),
    "fast_movement_granted": TargetPathInfo(
        prefix="fast_movement_granted",
        description="Fast movement granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["fast_movement_granted.monk_fast_movement"]
    ),
    "evasion_granted": TargetPathInfo(
        prefix="evasion_granted",
        description="Evasion ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["evasion_granted.monk_evasion"]
    ),
    "mighty_strike_granted": TargetPathInfo(
        prefix="mighty_strike_granted",
        description="Mighty Strike ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["mighty_strike_granted.crusader_mighty_strike"]
    ),
    "steely_resolve_granted": TargetPathInfo(
        prefix="steely_resolve_granted",
        description="Steely Resolve ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["steely_resolve_granted.crusader_steely_resolve"]
    ),
    "furious_counterstrike_granted": TargetPathInfo(
        prefix="furious_counterstrike_granted",
        description="Furious Counterstrike ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["furious_counterstrike_granted.crusader_furious_counterstrike"]
    ),
    "smite_granted": TargetPathInfo(
        prefix="smite_granted",
        description="Smite ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["smite_granted.paladin_smite"]
    ),
    "soulmelds_granted": TargetPathInfo(
        prefix="soulmelds_granted",
        description="Soulmelds granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["soulmelds_granted.lammasu_wing_charge"]
    ),
    "essentia_granted": TargetPathInfo(
        prefix="essentia_granted",
        description="Essentia granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["essentia_granted.incandescent_cloud"]
    ),
    "totem_bind_granted": TargetPathInfo(
        prefix="totem_bind_granted",
        description="Totem bind ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["totem_bind_granted.totem_golem"]
    ),
    "rebind_granted": TargetPathInfo(
        prefix="rebind_granted",
        description="Rebind ability granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["rebind_granted.totem_rebind"]
    ),
    "maneuvers_granted": TargetPathInfo(
        prefix="maneuvers_granted",
        description="Martial maneuvers granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["maneuvers_granted.strike_of_the_broken_shield"]
    ),
    "stances_granted": TargetPathInfo(
        prefix="stances_granted",
        description="Martial stances granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["stances_granted.iron_guard_s_glare"]
    ),
    "spell_slots_per_day_granted": TargetPathInfo(
        prefix="spell_slots_per_day_granted",
        description="Spell slots per day granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["spell_slots_per_day_granted.extra_spell_slots"]
    ),
    "spells_known_granted": TargetPathInfo(
        prefix="spells_known_granted",
        description="Spells known granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["spells_known_granted.bonus_spells"]
    ),
    "prepared_spells_granted": TargetPathInfo(
        prefix="prepared_spells_granted",
        description="Prepared spells granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["prepared_spells_granted.bonus_prepared_spells"]
    ),
    "bonus_feats_granted": TargetPathInfo(
        prefix="bonus_feats_granted",
        description="Bonus feats granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["bonus_feats_granted.fighter_bonus_feat"]
    ),
    "skill_points_granted": TargetPathInfo(
        prefix="skill_points_granted",
        description="Skill points granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["skill_points_granted.human_skill_points"]
    ),
    "gold_granted": TargetPathInfo(
        prefix="gold_granted",
        description="Gold granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["gold_granted.treasure_chest"]
    ),
    "xp_granted": TargetPathInfo(
        prefix="xp_granted",
        description="XP granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["xp_granted.quest_completion"]
    ),
    "alignment_change_granted": TargetPathInfo(
        prefix="alignment_change_granted",
        description="Alignment changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["alignment_change_granted.corrupting_influence"]
    ),
    "condition_duration_granted": TargetPathInfo(
        prefix="condition_duration_granted",
        description="Condition duration changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["condition_duration_granted.extended_condition"]
    ),
    "resource_capacity_granted": TargetPathInfo(
        prefix="resource_capacity_granted",
        description="Resource capacity changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["resource_capacity_granted.extra_ki"]
    ),
    "resource_current_granted": TargetPathInfo(
        prefix="resource_current_granted",
        description="Resource current value changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["resource_current_granted.restore_spell_slots"]
    ),
    "zone_duration_granted": TargetPathInfo(
        prefix="zone_duration_granted",
        description="Zone duration changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["zone_duration_granted.extended_zone"]
    ),
    "zone_size_granted": TargetPathInfo(
        prefix="zone_size_granted",
        description="Zone size changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["zone_size_granted.enlarged_zone"]
    ),
    "item_property_granted": TargetPathInfo(
        prefix="item_property_granted",
        description="Item property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["item_property_granted.flaming_sword"]
    ),
    "weapon_property_granted": TargetPathInfo(
        prefix="weapon_property_granted",
        description="Weapon property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["weapon_property_granted.keen_edge"]
    ),
    "armor_property_granted": TargetPathInfo(
        prefix="armor_property_granted",
        description="Armor property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["armor_property_granted.fortification"]
    ),
    "shield_property_granted": TargetPathInfo(
        prefix="shield_property_granted",
        description="Shield property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["shield_property_granted.animated_shield"]
    ),
    "feat_property_granted": TargetPathInfo(
        prefix="feat_property_granted",
        description="Feat property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["feat_property_granted.improved_initiative"]
    ),
    "spell_property_granted": TargetPathInfo(
        prefix="spell_property_granted",
        description="Spell property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["spell_property_granted.empowered_spell"]
    ),
    "condition_property_granted": TargetPathInfo(
        prefix="condition_property_granted",
        description="Condition property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["condition_property_granted.greater_blindness"]
    ),
    "resource_property_granted": TargetPathInfo(
        prefix="resource_property_granted",
        description="Resource property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["resource_property_granted.enhanced_resource"]
    ),
    "zone_property_granted": TargetPathInfo(
        prefix="zone_property_granted",
        description="Zone property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["zone_property_granted.persistent_zone"]
    ),
    "task_property_granted": TargetPathInfo(
        prefix="task_property_granted",
        description="Task property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["task_property_granted.accelerated_crafting"]
    ),
    "race_property_granted": TargetPathInfo(
        prefix="race_property_granted",
        description="Race property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["race_property_granted.improved_darkvision"]
    ),
    "class_property_granted": TargetPathInfo(
        prefix="class_property_granted",
        description="Class property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["class_property_granted.bonus_spell_slots"]
    ),
    "alignment_property_granted": TargetPathInfo(
        prefix="alignment_property_granted",
        description="Alignment property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["alignment_property_granted.aura_of_good"]
    ),
    "deity_property_granted": TargetPathInfo(
        prefix="deity_property_granted",
        description="Deity property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["deity_property_granted.divine_grace"]
    ),
    "game_state_granted": TargetPathInfo(
        prefix="game_state_granted",
        description="Game state changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["game_state_granted.time_stop"]
    ),
    "player_character_granted": TargetPathInfo(
        prefix="player_character_granted",
        description="Player character property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["player_character_granted.heroic_might"]
    ),
    "npc_granted": TargetPathInfo(
        prefix="npc_granted",
        description="NPC property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["npc_granted.charmed_monster"]
    ),
    "party_granted": TargetPathInfo(
        prefix="party_granted",
        description="Party property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["party_granted.bless_party"]
    ),
    "encounter_granted": TargetPathInfo(
        prefix="encounter_granted",
        description="Encounter property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["encounter_granted.surprise_round"]
    ),
    "world_granted": TargetPathInfo(
        prefix="world_granted",
        description="World property changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["world_granted.planar_shift"]
    ),
    "inventory_granted": TargetPathInfo(
        prefix="inventory_granted",
        description="Inventory changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["inventory_granted.summon_item"]
    ),
    "equipment_granted": TargetPathInfo(
        prefix="equipment_granted",
        description="Equipment changes granted by an effect or ability.",
        allowed_operators=["grantTag", "removeTag"],
        requires_bonus_type=False,
        value_type="bool",
        example_paths=["equipment_granted.magic_weapon"]
    ),
}

# Helper function to get info for a given targetPath
def get_target_path_info(target_path: str) -> Optional[TargetPathInfo]:
    prefix = target_path.split(".", 1)[0]
    return TARGET_PATH_REGISTRY.get(prefix)
