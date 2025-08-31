from __future__ import annotations
from typing import Optional, Dict, List, TYPE_CHECKING
from uuid import uuid4
from pydantic import BaseModel, Field
from .schema_models import EffectDefinition, DurationSpec
from .expr import eval_for_actor
from .models import Entity
from .loader import ContentIndex
from dndrpg.engine.resources_runtime import ResourceEngine
from dndrpg.engine.conditions_runtime import ConditionsEngine

if TYPE_CHECKING:
    from .state import GameState

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

    def __init__(self, content: ContentIndex, state: "GameState", resources: ResourceEngine | None = None, conditions: ConditionsEngine | None = None):
        self.content = content
        self.state = state
        self.resources = resources or ResourceEngine(content, state)
        self.conditions = conditions or ConditionsEngine(content, state)  # NEW

    def _snapshot_duration_rounds(self, ed: EffectDefinition, source: Entity, target: Entity) -> tuple[str, Optional[int]]:
        # Returns (duration_type, remaining_rounds)
        ds: Optional[DurationSpec] = ed.duration
        if ds is None:
            # Already enforced by schema for Spell/Sp; allow continuous for passives
            return ("permanent", None)
        dt = ds.type
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

    def _exec_operations_on_attach(self, ed: EffectDefinition, inst: EffectInstance, source: Entity, target: Entity, logs: list[str]):
        # Minimal executor: temp_hp and resource.* ops
        for op in ed.operations or []:
            opname = getattr(op, "op", None)
            if opname == "temp_hp":
                amt = getattr(op, "amount", 0)
                logs += self.resources.grant_temp_hp(target.id, amt, effect_instance_id=inst.instance_id)
            elif opname == "resource.create":
                rid = getattr(op, "resource_id", None)
                if rid:
                    rs, log2 = self.resources.create_from_definition(
                        rid,
                        owner_scope=op.owner_scope or None,
                        owner_entity_id=target.id,
                        owner_effect_instance_id=inst.instance_id,
                        initial_current=op.initial_current
                    )
                    logs += log2
            elif opname == "resource.restore":
                rid = getattr(op, "resource_id", None)
                if rid:
                    if getattr(op, "to_max", False):
                        self.resources.restore(target.id, rid, to_max=True)
                    else:
                        amt = getattr(op, "amount", None)
                        if amt is not None:
                            val = eval_for_actor(str(amt), source)
                            self.resources.restore(target.id, rid, amount=int(val))
            elif opname == "resource.spend":
                rid = getattr(op, "resource_id", None)
                amt = getattr(op, "amount", 0)
                if rid:
                    val = eval_for_actor(str(amt), source) if not isinstance(amt, (int,)) else amt
                    self.resources.spend(target.id, rid, int(val))
            elif opname == "resource.set":
                rid = getattr(op, "resource_id", None)
                cur = getattr(op, "current", None)
                if rid and cur is not None:
                    val = eval_for_actor(str(cur), source) if not isinstance(cur, (int,)) else cur
                    self.resources.set_current(target.id, rid, int(val))
            elif opname == "condition.apply":
                cid = getattr(op, "id", None)
                dur = getattr(op, "duration", None)
                stacks = getattr(op, "stacks", None)
                if cid:
                    logs += self.conditions.apply(cid, source, target, duration_override=dur, stacks=stacks, params=getattr(op, "params", None))
            elif opname == "condition.remove":
                cid = getattr(op, "id", None)
                if cid:
                    logs += self.conditions.remove(cond_id=cid, target=target)

    def attach(self, effect_id: str, source: Entity, target: Entity) -> list[str]:
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
        # Execute on-attach operations now
        self._exec_operations_on_attach(ed, inst, source, target, logs)
        if dur_type == "instantaneous":
            logs.append(f"[Effects] {ed.name} (instantaneous) applied to {target.name}")
            return logs
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
