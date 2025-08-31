from __future__ import annotations
from typing import Any, Dict, Optional
from dndrpg.engine.expr import eval_expr
from dndrpg.engine.models import Entity

class BuildView:
    """
    Read-only view used by prereq evaluator. Provides minimal API while building.
    """
    def __init__(self, entity: Optional[Entity], picks: dict):
        self.entity = entity
        self.picks = picks  # {"abilities": {...}, "skills": {...}, "feats": set([...]), "class": "cleric", "race": "human", ...}

    # functions used in prereq exprs
    def has_feat(self, feat_id: str) -> bool:
        feats = self.picks.get("feats", set())
        if isinstance(feats, set):
            return feat_id in feats
        return feat_id in (feats or [])

    def skill_ranks(self, name: str) -> int:
        return int(self.picks.get("skills", {}).get(name.lower(), 0))

    def bab(self) -> int:
        if self.entity:
            return self.entity.base_attack_bonus
        return int(self.picks.get("bab", 0))

    def save(self, which: str) -> int:
        if self.entity:
            return {
                "fort": self.entity.base_fort + self.entity.abilities.con.mod(),
                "ref":  self.entity.base_ref + self.entity.abilities.dex.mod(),
                "will": self.entity.base_will + self.entity.abilities.wis.mod(),
            }[which.lower()]
        # while building, use tentative
        tentative = self.picks.get("saves", {})
        return int(tentative.get(which.lower(), 0))

    def race(self) -> str:
        return str(self.picks.get("race", ""))

    def clazz(self) -> str:
        return str(self.picks.get("class", ""))

    def alignment(self) -> str:
        return str(self.picks.get("alignment", ""))

    def deity(self) -> str:
        return str(self.picks.get("deity", ""))

    def has_domain(self, name: str) -> bool:
        return name.lower() in [d.lower() for d in (self.picks.get("domains", []) or [])]

def eval_prereq(expr: str, view: BuildView) -> bool:
    extra: Dict[str, Any] = {
        "has_feat": view.has_feat,
        "skill_ranks": view.skill_ranks,
        "bab": view.bab,
        "save": view.save,
        "race_is": lambda r: view.race().lower() == str(r).lower(),
        "class_is": lambda c: view.clazz().lower() == str(c).lower(),
        "alignment_is": lambda a: view.alignment().lower() == str(a).lower(),
        "deity_is": lambda d: view.deity().lower() == str(d).lower(),
        "has_domain": view.has_domain,
        "abil": view.picks.get("abilities", {}),
        "skills": view.picks.get("skills", {}),
    }
    # expr may include ability_mod('str'), class_level('cleric'), etc. via eval_expr functions
    try:
        val = eval_expr(expr, extra=extra)
        return bool(val)
    except Exception:
        return False
