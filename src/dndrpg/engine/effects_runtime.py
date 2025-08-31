from __future__ import annotations
from typing import Optional, Dict, List
from uuid import uuid4
from pydantic import BaseModel, Field
from .schema_models import EffectDefinition, DurationSpec
from .expr import eval_for_actor
from .models import Entity
from .loader import ContentIndex

class EffectInstance(BaseModel):
    instance_id: str = Field(default_factory=lambda: uuid4().hex)
    definition_id: str
    name: str
    abilityType: str
    source_entity_id: str
    target_entity_id: str

    # Duration snapshot (rounds for now; we’ll support minutes/hours/days in scheduler later)
    duration_type: str = "instantaneous"  # matches DurationSpec.type
    remaining_rounds: Optional[int] = None  # None for non-round durations or permanent/instant
    active: bool = True
    suppressed: bool = False

    started_at_round: int = 0  # simple logical counter (to hook scheduler later)
    variables: Dict[str, int | float | str] = Field(default_factory=dict)  # runtime variables if needed
    notes: Optional[str] = None

class EffectsEngine:
    """
    Runtime manager for effect instances:
      - attach() creates an EffectInstance from a blueprint
      - detach() removes an instance
      - list_for_entity() returns active instances on an entity
    Gates/saves/attacks, modifiers, and operations execution will be wired in subsequent M2 steps.
    """

    def __init__(self, content: ContentIndex, state: "GameState"):
        self.content = content
        self.state = state

    def _snapshot_duration_rounds(self, ed: EffectDefinition, source: Entity, target: Entity) -> tuple[str, Optional[int]]:
        # Returns (duration_type, remaining_rounds)
        ds: Optional[DurationSpec] = ed.duration
        if ds is None:
            # Already enforced by schema for Spell/Sp; allow continuous for passives
            return ("permanent", None)
        dt = ds.type
        if dt == "instantaneous":
            return ("instantaneous", None)
        if dt == "rounds":
            # value or formula; evaluate formula if present
            if ds.value is not None:
                return ("rounds", max(0, int(ds.value)))
            if ds.formula:
                val = eval_for_actor(ds.formula, source)  # actor=source; can extend env later
                try:
                    return ("rounds", max(0, int(val)))
                except Exception:
                    return ("rounds", None)
            return ("rounds", None)
        # For minutes/hours/days/permanent/special, we record type; scheduler will translate later
        return (dt, None)

    def attach(self, effect_id: str, source: Entity, target: Entity) -> list[str]:
        """
        Create and attach an EffectInstance from EffectDefinition, snapshotting basic duration.
        Instantaneous effects are not retained (we’ll execute operations in later steps).
        """
        logs: list[str] = []
        if effect_id not in self.content.effects:
            return [f"[Effects] Unknown effect id: {effect_id}"]

        ed = self.content.effects[effect_id]
        dur_type, rem_rounds = self._snapshot_duration_rounds(ed, source, target)

        inst = EffectInstance(
            definition_id=ed.id,
            name=ed.name,
            abilityType=ed.abilityType,
            source_entity_id=source.id,
            target_entity_id=target.id,
            duration_type=dur_type,
            remaining_rounds=rem_rounds,
            started_at_round=self.state.round_counter
        )

        if dur_type == "instantaneous":
            # For now: log only; later we’ll execute ed.operations immediately and skip retention
            logs.append(f"[Effects] {ed.name} (instantaneous) applied to {target.name}")
            return logs

        # Retain persistent instance
        self.state.active_effects.setdefault(target.id, []).append(inst)
        logs.append(f"[Effects] {ed.name} attached to {target.name} ({dur_type}{f' {rem_rounds} rounds' if rem_rounds is not None else ''})")
        return logs

    def detach(self, instance_id: str, target: Entity) -> bool:
        lst = self.state.active_effects.get(target.id, [])
        for i, inst in enumerate(lst):
            if inst.instance_id == instance_id:
                lst.pop(i)
                return True
        return False

    def list_for_entity(self, entity_id: str) -> List[EffectInstance]:
        return list(self.state.active_effects.get(entity_id, []))