from __future__ import annotations
from typing import Optional, Dict, List, TYPE_CHECKING
from uuid import uuid4
from pydantic import BaseModel, Field
from .schema_models import EffectDefinition, Operation
from .expr import eval_for_actor
from .models import Entity
from .loader import ContentIndex
from dndrpg.engine.resources_runtime import ResourceEngine
from dndrpg.engine.conditions_runtime import ConditionsEngine
if TYPE_CHECKING:
    from .state import GameState
    from dndrpg.engine.rulehooks_runtime import RuleHooksRegistry

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

    def __init__(self, content: ContentIndex, state: "GameState",
                 resources: ResourceEngine | None = None,
                 conditions: ConditionsEngine | None = None,
                 hooks: RuleHooksRegistry | None = None):
        self.content = content
        self.state = state
        self.resources = resources or ResourceEngine(content, state)
        self.conditions = conditions or ConditionsEngine(content, state)
        self.hooks = hooks  # may be set later by GameEngine to resolve circular init

    def execute_operations(self, ops: List[Operation], actor: Optional[Entity], target: Optional[Entity], *, 
                           parent_instance_id: Optional[str] = None, logs: Optional[List[str]] = None):
        out = logs if logs is not None else []
        # dummy = EffectInstance(
        #     definition_id="ops",
        #     name="Ops",
        #     abilityType="Ex",
        #     source_entity_id=actor.id if actor else (target.id if target else ""),
        #     target_entity_id=target.id if target else (actor.id if actor else ""),
        #     duration_type="instantaneous"
        # )
        for op in ops:
            opname = getattr(op, "op", None)
            if opname == "temp_hp":
                amt = getattr(op, "amount", 0)
                out += self.resources.grant_temp_hp(target.id if target else "", amt,
                                                    effect_instance_id=parent_instance_id)
            elif opname == "resource.create":
                rid = getattr(op, "resource_id", None)
                if rid:
                    _rs, log2 = self.resources.create_from_definition(
                        rid,
                        owner_scope=getattr(op, "owner_scope", None) or None,
                        owner_entity_id=target.id if target else None,
                        owner_effect_instance_id=parent_instance_id,
                        initial_current=getattr(op, "initial_current", None)
                    )
                    out += log2
            elif opname == "resource.restore":
                rid = getattr(op, "resource_id", None)
                if rid:
                    if getattr(op, "to_max", False):
                        self.resources.restore(target.id if target else "", rid, to_max=True)
                    else:
                        amt = getattr(op, "amount", None)
                        if amt is not None and actor:
                            val = eval_for_actor(str(amt), actor)
                            self.resources.restore(target.id if target else "", rid, amount=int(val))
            elif opname == "resource.spend":
                rid = getattr(op, "resource_id", None)
                amt = getattr(op, "amount", 0)
                if rid and actor:
                    val = eval_for_actor(str(amt), actor) if not isinstance(amt, (int,)) else amt
                    self.resources.spend(target.id if target else "", rid, int(val))
            elif opname == "resource.set":
                rid = getattr(op, "resource_id", None)
                cur = getattr(op, "current", None)
                if rid and cur is not None:
                    v = eval_for_actor(str(cur), actor) if (actor and not isinstance(cur, (int,))) else cur
                    self.resources.set_current(target.id if target else "", rid, int(v))
            elif opname == "condition.apply":
                cid = getattr(op, "id", None)
                dur = getattr(op, "duration", None)
                stacks = getattr(op, "stacks", None)
                if cid and target and actor:
                    out += self.conditions.apply(cid, actor, target, duration_override=dur, stacks=stacks, params=getattr(op, "params", None))
            elif opname == "condition.remove":
                cid = getattr(op, "id", None)
                if cid and target:
                    out += self.conditions.remove(cond_id=cid, target=target)
            elif opname == "save":
                # Minimal: not implemented yet
                out.append("[Ops] save op not implemented in executor")
        return out

    def _exec_operations_on_attach(self, ed: EffectDefinition, inst: EffectInstance, source: Entity, target: Entity, logs: list[str]):
        self.execute_operations(list(ed.operations or []), source, target, parent_instance_id=inst.instance_id, logs=logs)

    def attach(self, effect_id: str, source: Entity, target: Entity) -> list[str]:
        logs: list[str] = []
        if effect_id not in self.content.effects:
            return [f"[Effects] Unknown effect id: {effect_id}"]
        ed = self.content.effects[effect_id]

        # 0) incoming.effect hook decision
        if self.hooks:
            dec = self.hooks.incoming_effect(target.id, effect_def=ed, actor_entity_id=source.id)
            if not dec.allow:
                logs.append(f"[Effects] {ed.name} blocked ({'; '.join(dec.notes)})")
                return logs

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

        # Execute operations on attach
        self._exec_operations_on_attach(ed, inst, source, target, logs)

        if dur_type == "instantaneous":
            logs.append(f"[Effects] {ed.name} (instantaneous) applied to {target.name}")
            return logs

        # Retain instance and register hooks
        self.state.active_effects.setdefault(target.id, []).append(inst)
        if self.hooks:
            self.hooks.register_for_effect(ed, inst.instance_id, target.id)

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
