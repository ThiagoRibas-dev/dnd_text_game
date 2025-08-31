from __future__ import annotations
from typing import Optional, Dict, List, Tuple
from uuid import uuid4
from pydantic import BaseModel, Field
from dndrpg.engine.schema_models import ConditionDefinition, DurationSpec
from dndrpg.engine.expr import eval_for_actor
from dndrpg.engine.models import Entity
from dndrpg.engine.loader import ContentIndex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dndrpg.engine.state import GameState

class ConditionInstance(BaseModel):
    instance_id: str = Field(default_factory=lambda: uuid4().hex)
    definition_id: str
    name: str
    source_entity_id: str
    target_entity_id: str

    precedence: Optional[int] = None
    tags: List[str] = Field(default_factory=list)

    duration_type: str = "instantaneous"
    remaining_rounds: Optional[int] = None
    active: bool = True
    suppressed: bool = False
    applied_at_round: int = 0

    params: Dict[str, int | float | str] = Field(default_factory=dict)
    notes: Optional[str] = None

class ConditionsEngine:
    """
    Apply/remove/list conditions at runtime.
    Duration policy:
      - If OpConditionApply provides a duration override, use it; else use ConditionDefinition.default_duration.
      - Instantaneous conditions are attached and immediately eligible for cleanup by the engine (we keep the instance this round for visibility).
      - Re-applying same condition id refreshes duration to the max of old/new (no stacking by default).
        If an Op explicitly requests stacks=True, allow multiple instances.
    """

    def __init__(self, content: ContentIndex, state: "GameState"):
        self.content = content
        self.state = state

    def _snapshot_duration_rounds(
        self,
        cd: ConditionDefinition,
        override: Optional[DurationSpec],
        source: Entity,
        target: Entity
    ) -> Tuple[str, Optional[int]]:
        ds: Optional[DurationSpec] = override or cd.default_duration
        if ds is None:
            # default to instantaneous for conditions with no default declared
            return ("instantaneous", None)
        dt = ds.type
        if dt in ("instantaneous", "permanent", "special"):
            return (dt, None)
        if dt == "rounds":
            if ds.value is not None:
                return ("rounds", max(0, int(ds.value)))
            if ds.formula:
                val = eval_for_actor(ds.formula, source)
                try:
                    return ("rounds", max(0, int(val)))
                except Exception:
                    return ("rounds", None)
            return ("rounds", None)
        # For minutes/hours/days: scheduler converts later
        return (dt, None)

    def _list_for_entity(self, entity_id: str) -> List[ConditionInstance]:
        return list(self.state.active_conditions.get(entity_id, []))

    def list_for_entity(self, entity_id: str) -> List[ConditionInstance]:
        return self._list_for_entity(entity_id)

    def apply(
        self,
        cond_id: str,
        source: Entity,
        target: Entity,
        *,
        duration_override: Optional[DurationSpec] = None,
        stacks: Optional[bool] = None,
        params: Optional[Dict[str, int | float | str]] = None
    ) -> list[str]:
        logs: list[str] = []
        if cond_id not in self.content.conditions:
            return [f"[Cond] Unknown condition id: {cond_id}"]
        cd = self.content.conditions[cond_id]

        dur_type, rem_rounds = self._snapshot_duration_rounds(cd, duration_override, source, target)
        new_inst = ConditionInstance(
            definition_id=cd.id,
            name=cd.name,
            source_entity_id=source.id,
            target_entity_id=target.id,
            precedence=cd.precedence,
            tags=list(cd.tags or []),
            duration_type=dur_type,
            remaining_rounds=rem_rounds,
            applied_at_round=self.state.round_counter,
            params=params or {}
        )

        lst = self.state.active_conditions.setdefault(target.id, [])

        if not stacks:
            # Find an existing same-id instance
            for inst in lst:
                if inst.definition_id == cond_id:
                    # Refresh/extend duration
                    if inst.duration_type == "rounds" and rem_rounds is not None:
                        if inst.remaining_rounds is None or rem_rounds > inst.remaining_rounds:
                            inst.remaining_rounds = rem_rounds
                    inst.active = True
                    logs.append(f"[Cond] Refreshed {cd.name} on {target.name} ({inst.remaining_rounds or 0} rounds)")
                    return logs

        # Else add a new instance
        lst.append(new_inst)
        desc = dur_type + (f" {rem_rounds} rounds" if rem_rounds is not None else "")
        logs.append(f"[Cond] {cd.name} applied to {target.name} ({desc})")
        return logs

    def remove(self, cond_id: Optional[str] = None, *, instance_id: Optional[str] = None, target: Optional[Entity] = None) -> list[str]:
        logs: list[str] = []
        if not target:
            return ["[Cond] remove: missing target"]
        lst = self.state.active_conditions.get(target.id, [])
        if instance_id:
            for i, inst in enumerate(lst):
                if inst.instance_id == instance_id:
                    lst.pop(i)
                    logs.append(f"[Cond] Removed {inst.name} from {target.name}")
                    return logs
            return ["[Cond] remove: instance not found"]
        if cond_id:
            kept = []
            removed_any = False
            for inst in lst:
                if inst.definition_id == cond_id:
                    removed_any = True
                    logs.append(f"[Cond] Removed {inst.name} from {target.name}")
                else:
                    kept.append(inst)
            self.state.active_conditions[target.id] = kept
            if not removed_any:
                logs.append(f"[Cond] {cond_id} not present on {target.name}")
            return logs
        return ["[Cond] remove: specify cond_id or instance_id"]

    def tick_round(self) -> list[str]:
        logs: list[str] = []
        self.state.round_counter += 1
        for entity_id, lst in list(self.state.active_conditions.items()):
            keep: list[ConditionInstance] = []
            for inst in lst:
                if inst.duration_type == "rounds" and inst.remaining_rounds is not None:
                    if inst.remaining_rounds > 0:
                        inst.remaining_rounds -= 1
                    if inst.remaining_rounds <= 0:
                        logs.append(f"[Cond] {inst.name} expired")
                        continue
                keep.append(inst)
            self.state.active_conditions[entity_id] = keep
        return logs