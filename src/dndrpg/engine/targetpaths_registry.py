from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Set

@dataclass(frozen=True)
class PathMeta:
    kind: str                      # "numeric", "tags", "resource"
    allowed_ops: Set[str]          # {"add","set","min","max",...}
    require_bonus_type_for_add: bool = False
    allowed_bonus_types: Optional[Set[str]] = None  # None = any; else restricted

# Exact registry entries (most specific first)
_REGISTRY_EXACT: Dict[str, PathMeta] = {
    # Abilities (apply to score directly; typed bonuses needed for add/sub)
    "abilities.str": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "abilities.dex": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "abilities.con": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "abilities.int": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "abilities.wis": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "abilities.cha": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),

    # AC components
    "ac.natural":     PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, {"natural_armor","natural_armor_enhancement"}),
    "ac.deflection":  PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, {"deflection"}),
    "ac.dodge":       PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, {"dodge"}),
    "ac.misc":        PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    # Totals (rare; allowed but we still require typed for add/sub)
    "ac.total":       PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "ac.touch":       PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "ac.flat_footed": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),

    # Saves
    "save.fort": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "save.ref":  PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "save.will": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),

    # Attacks / BAB
    "attack.bab.effective": PathMeta("numeric", {"set","min","max","replace"}, False, None),
    "attack.melee.bonus":   PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "attack.ranged.bonus":  PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),

    # Speed
    "speed.land": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp","multiply"}, False, None),

    # Senses (numeric radii)
    "senses.darkvision": PathMeta("numeric", {"add","set","min","max","cap","clamp"}, False, None),
    "senses.blindsense": PathMeta("numeric", {"add","set","min","max","cap","clamp"}, False, None),
    "senses.blindsight": PathMeta("numeric", {"add","set","min","max","cap","clamp"}, False, None),
    "senses.low_light":  PathMeta("numeric", {"add","set","min","max","cap","clamp"}, False, None),

    # Tags: grant/remove only (handled by other systems)
    "tags": PathMeta("tags", {"grantTag","removeTag"}, False, None),

    # Resources: numeric pools, generally add/set/etc.
    "resources": PathMeta("resource", {"add","set","min","max","cap","clamp"}, False, None),
}

# Wildcard registry (prefix-based)
_REGISTRY_PREFIX: Dict[str, PathMeta] = {
    "abilities.": PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "ac.":        PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "save.":      PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "resist.":    PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, True, None),
    "dr.":        PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp"}, False, None),
    "bab.":       PathMeta("numeric", {"add","subtract","set","min","max","replace"}, True, None),
    "attack.":    PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp","replace"}, True, None),
    "speed.":     PathMeta("numeric", {"add","subtract","set","min","max","cap","clamp","multiply"}, False, None),
    "senses.":    PathMeta("numeric", {"add","set","min","max","cap","clamp"}, False, None),
    "tags.":      PathMeta("tags", {"grantTag","removeTag"}, False, None),
    "resources.": PathMeta("resource", {"add","set","min","max","cap","clamp"}, False, None),
}

def resolve_meta(path: str) -> Optional[PathMeta]:
    if path in _REGISTRY_EXACT:
        return _REGISTRY_EXACT[path]
    for pref, meta in _REGISTRY_PREFIX.items():
        if path.startswith(pref):
            return meta
    return None
