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
from .damage_runtime import DamageEngine
from .zones_runtime import ZoneEngine
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
                 resources: ResourceEngine | None = None, conditions: ConditionsEngine | None = None,
                 hooks: RuleHooksRegistry | None = None, damage: DamageEngine | None = None, zones: ZoneEngine | None = None):
        self.content = content
        self.state = state
        self.resources = resources or ResourceEngine(content, state)
        self.conditions = conditions or ConditionsEngine(content, state)
        self.hooks = hooks  # may be set later by GameEngine to resolve circular init
        self.damage = damage
        self.zones = zones

    def execute_operations(self, ops: List[Operation], actor: Optional[Entity], target: Optional[Entity], *, 
                           parent_instance_id: Optional[str] = None, logs: Optional[List[str]] = None):
        out = logs if logs is not None else []
        actor = actor or (target)  # fallback
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
            elif opname == "damage":
                if not self.damage or not target:
                    out.append("[Ops] damage: missing engine or target")
                    continue
                amt = getattr(op, "amount", 0)
                dtype = getattr(op, "damage_type", "typeless")
                val = amt if isinstance(amt, (int, float)) else eval_for_actor(str(amt), actor) if actor else 0
                self.damage.apply_damage(target.id, int(val), dtype, logs=out)
            elif opname == "heal_hp":
                if not self.damage or not target:
                    out.append("[Ops] heal_hp: missing engine or target")
                    continue
                amt = getattr(op, "amount", 0)
                nlo = bool(getattr(op, "nonlethal_only", False))
                val = amt if isinstance(amt, (int, float)) else eval_for_actor(str(amt), actor) if actor else 0
                self.damage.heal_hp(target.id, int(val), nonlethal_only=nlo, logs=out)
            elif opname == "ability.damage":
                if not self.damage or not target:
                    out.append("[Ops] ability.damage: missing engine or target")
                    continue
                ab = getattr(op, "ability", "str")
                amt = getattr(op, "amount", 0)
                val = amt if isinstance(amt, (int, float)) else eval_for_actor(str(amt), actor) if actor else 0
                self.damage.ability_damage(target.id, ab, int(val), logs=out)
            elif opname == "ability.drain":
                if not self.damage or not target:
                    out.append("[Ops] ability.drain: missing engine or target")
                    continue
                ab = getattr(op, "ability", "str")
                amt = getattr(op, "amount", 0)
                val = amt if isinstance(amt, (int, float)) else eval_for_actor(str(amt), actor) if actor else 0
                self.damage.ability_drain(target.id, ab, int(val), logs=out)
            elif opname == "attach":
                eid = getattr(op, "effect_id", None)
                if eid and actor and target:
                    out += self.attach(eid, actor, target)
            elif opname == "detach":
                eid = getattr(op, "effect_id", None)
                all_instances = bool(getattr(op, "all_instances", False))
                if eid and target:
                    # remove first/all instances by definition_id on target
                    lst = self.state.active_effects.get(target.id, [])
                    kept = []
                    removed = 0
                    for inst in lst:
                        if inst.definition_id == eid and (all_instances or removed == 0):
                            removed += 1
                            if self.hooks:
                                self.hooks.unregister_by_parent(inst.instance_id)
                        else:
                            kept.append(inst)
                    self.state.active_effects[target.id] = kept
                    out.append(f"[Effects] Detached {removed} instance(s) of {eid} from {target.name}")
            elif opname == "zone.create":
                if not self.zones or not target:
                    out.append("[Ops] zone.create: missing engine or target")
                    continue
                zid = getattr(op, "zone_id", None)
                if zid:
                    _zi, log2 = self.zones.create_from_definition(zid, owner_entity_id=target.id)
                    out += log2
                else:
                    shape = getattr(op, "shape", None)
                    name = getattr(op, "name", None) or "Zone"
                    duration = getattr(op, "duration", None)
                    hooks = getattr(op, "hooks", None) or []
                    if shape and duration:
                        _zi, log2 = self.zones.create_inline(name=name, shape=shape, duration=duration, hooks=hooks, owner_entity_id=target.id)
                        out += log2
                    else:
                        out.append("[Ops] zone.create: missing inline name+shape+duration")
            elif opname == "zone.destroy":
                if not self.zones or not target:
                    out.append("[Ops] zone.destroy: missing engine or target")
                    continue
                zid = getattr(op, "zone_id", None)
                zinst = getattr(op, "zone_instance_id", None)
                out += self.zones.destroy(owner_entity_id=target.id, zone_definition_id=zid, zone_instance_id=zinst)
            elif opname == "save":
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

        # Check for initial suppression from active zones
        if self.zones:
            for zone_owner_id, zones_list in self.state.active_zones.items():
                for zone_inst in zones_list:
                    zd = self.content.zones.get(zone_inst.definition_id)
                    if zd and zd.suppression and zd.suppression.kind == "antimagic":
                        if ed.abilityType in (zd.suppression.ability_types or []): # Assuming ability_types is a new field in ZoneSuppression
                            inst.suppressed = True
                            inst.suppressed_by.append(f"zone:{zone_inst.instance_id}")
                            logs.append(f"[Effects] {inst.name} initially suppressed by antimagic zone {zone_inst.name}")

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
