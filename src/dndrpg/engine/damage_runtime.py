from __future__ import annotations
from typing import Optional, List, Literal, TYPE_CHECKING
from .models import Entity
from .resources_runtime import ResourceState
from .loader import ContentIndex
if TYPE_CHECKING:
    from .state import GameState

DamageKind = Literal[
    "physical.bludgeoning", "physical.piercing", "physical.slashing",
    "fire", "cold", "acid", "electricity", "sonic", "force",
    "negative", "positive", "nonlethal", "bleed", "typeless"
]

class DamageEngine:
    """
    Minimal HP/nonlethal and ability damage/drain application with temp HP / ablative pool absorption.
    - Uses ResourceState.absorption when present (absorbTypes, absorbPerHit).
    - For now, we do not apply DR/resist (that comes in M3); we just absorb via pools first, then HP/nonlethal.
    """

    def __init__(self, content: ContentIndex, state: "GameState"):
        self.content = content
        self.state = state

    def _entity_by_id(self, ent_id: str) -> Optional[Entity]:
        if self.state.player.id == ent_id:
            return self.state.player
        return None

    def _matching_absorbers(self, owner_entity_id: str, damage_type: DamageKind) -> List[ResourceState]:
        matches: List[ResourceState] = []
        # entity scope
        key_ent = f"entity:{owner_entity_id}"
        for rs in self.state.resources.get(key_ent, []):
            if rs.absorption:
                if self._absorption_matches(rs, damage_type):
                    matches.append(rs)
        # effect-instance scope owned by this entity
        for key, lst in self.state.resources.items():
            if not key.startswith("effect:"):
                continue
            for rs in lst:
                if rs.owner_entity_id == owner_entity_id and rs.absorption:
                    if self._absorption_matches(rs, damage_type):
                        matches.append(rs)
        return matches

    def _absorption_matches(self, rs: ResourceState, damage_type: DamageKind) -> bool:
        if not rs.absorption:
            return False
        types = set(rs.absorption.absorbTypes or [])
        if "any" in types:
            return True
        if "physical" in types and damage_type.startswith("physical."):
            return True
        return damage_type in types

    def apply_damage(self, target_entity_id: str, amount: int, damage_type: DamageKind, *, logs: Optional[List[str]] = None) -> int:
        """
        Apply damage to target. Returns final HP damage applied (nonlethal is tracked separately).
        Order:
         1) Absorption pools (temp HP / ablative), respecting absorbPerHit where defined
         2) If nonlethal -> add to nonlethal_damage; else subtract from hp_current
        """
        if logs is None:
            logs = []
        ent = self._entity_by_id(target_entity_id)
        if not ent:
            logs.append("[Dmg] unknown target")
            return 0
        remaining = max(0, int(amount))
        # Absorb into pools
        absorbers = self._matching_absorbers(target_entity_id, damage_type)
        for rs in absorbers:
            if remaining <= 0:
                break
            per_hit_cap = rs.absorption.absorbPerHit if rs.absorption else None
            can = rs.current
            if per_hit_cap is not None:
                can = min(can, per_hit_cap)
            take = min(can, remaining)
            if take > 0:
                rs.current -= take
                remaining -= take
                logs.append(f"[Dmg] {rs.name or rs.definition_id} absorbed {take} ({rs.current} left)")

        if remaining <= 0:
            return 0

        if damage_type == "nonlethal":
            ent.nonlethal_damage = max(0, ent.nonlethal_damage + remaining)
            logs.append(f"[Dmg] {ent.name} took {remaining} nonlethal (total {ent.nonlethal_damage})")
            return 0

        # lethal HP
        before = ent.hp_current
        ent.hp_current = max(0, ent.hp_current - remaining)
        applied = before - ent.hp_current
        logs.append(f"[Dmg] {ent.name} took {applied} {damage_type} (HP {ent.hp_current}/{ent.hp_max})")
        return applied

    def heal_hp(self, target_entity_id: str, amount: int, *, nonlethal_only: bool = False, logs: Optional[List[str]] = None) -> int:
        if logs is None:
            logs = []
        ent = self._entity_by_id(target_entity_id)
        if not ent:
            logs.append("[Heal] unknown target")
            return 0
        healed = 0
        amt = max(0, int(amount))
        if nonlethal_only:
            nl_before = ent.nonlethal_damage
            ent.nonlethal_damage = max(0, ent.nonlethal_damage - amt)
            healed = nl_before - ent.nonlethal_damage
            logs.append(f"[Heal] {ent.name} healed {healed} nonlethal (now {ent.nonlethal_damage})")
            return healed
        # heal lethal HP first, then optionally reduce nonlethal (RAW: healing heals nonlethal 1:1 as well; can refine later)
        before = ent.hp_current
        ent.hp_current = min(ent.hp_max, ent.hp_current + amt)
        healed = ent.hp_current - before
        logs.append(f"[Heal] {ent.name} healed {healed} HP (HP {ent.hp_current}/{ent.hp_max})")
        return healed

    def ability_damage(self, target_entity_id: str, ability: str, amount: int, *, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        ent = self._entity_by_id(target_entity_id)
        if not ent:
            logs.append("[Ability] unknown target")
            return
        ab = ent.abilities.get(ability)
        prev = ab.damage
        ab.damage = max(0, prev + max(0, int(amount)))
        logs.append(f"[Ability] {ent.name} took {amount} {ability.upper()} damage (now {ab.damage})")

    def ability_drain(self, target_entity_id: str, ability: str, amount: int, *, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        ent = self._entity_by_id(target_entity_id)
        if not ent:
            logs.append("[Ability] unknown target")
            return
        ab = ent.abilities.get(ability)
        prev = ab.drain
        ab.drain = max(0, prev + max(0, int(amount)))
        logs.append(f"[Ability] {ent.name} drained {amount} {ability.upper()} (now {ab.drain})")