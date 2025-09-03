from __future__ import annotations
from typing import Optional, Dict, List, TYPE_CHECKING
from uuid import uuid4
import random
from pydantic import BaseModel, Field
from .schema_models import Operation, EffectDefinition
from .expr import eval_for_actor
from .models import Entity
from .loader import ContentIndex
from dndrpg.engine.resources_runtime import ResourceEngine
from dndrpg.engine.conditions_runtime import ConditionsEngine
from .damage_runtime import DamageEngine, DamagePacket, AttackContext
from .zones_runtime import ZoneEngine
from .gates_runtime import GatesEngine
from .modifiers_runtime import ModifiersEngine
from .trace import TraceSession

if TYPE_CHECKING:
    from .state import GameState
    from dndrpg.engine.rulehooks_runtime import RuleHooksRegistry
    from .scheduler import Scheduler

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
                 hooks: RuleHooksRegistry | None = None,
                 damage: DamageEngine | None = None,
                 zones: ZoneEngine | None = None,
                 modifiers: ModifiersEngine | None = None,
                 rng: Optional[random.Random] = None,
                 scheduler: "Scheduler" | None = None): # Add scheduler parameter
        self.content = content
        self.state = state
        self.resources = resources or ResourceEngine(content, state)
        self.conditions = conditions or ConditionsEngine(content, state)
        self.hooks = hooks
        self.damage = damage
        self.zones = zones
        self.modifiers = modifiers
        self.rng = rng or random.Random()
        self.gates = GatesEngine(self.modifiers, self.rng) if self.modifiers else None
        self.scheduler = scheduler # Assign scheduler

    def execute_operations(self, ops: List[Operation], actor: Optional[Entity], target: Optional[Entity], *,
                           parent_instance_id: Optional[str] = None, logs: Optional[List[str]] = None,
                           damage_scale: float = 1.0, crit_mult: int = 1):
        out = logs if logs is not None else []
        actor = actor or target
        buffered_packets: List[DamagePacket] = []

        def flush_packets():
            nonlocal buffered_packets
            if not buffered_packets or not self.damage or not target:
                buffered_packets = []
                return
            # Pre-phase hooks handled inside damage engine; we just call once per batch (treat as one attack)
            result = self.damage.apply_packets(target.id, buffered_packets, ctx=AttackContext(source_entity_id=actor.id if actor else None))
            out.extend(result.logs)
            buffered_packets = []

        for op in ops:
            if op.op == "damage":
                amt = op.amount
                base = amt if isinstance(amt, (int, float)) else eval_for_actor(str(amt), actor) if actor else 0
                final = int(round(float(base) * max(0.0, damage_scale) * max(1, crit_mult)))
                dtype = op.damage_type
                pkt = DamagePacket(
                    amount=max(0, int(final)),
                    dkind=dtype,
                    counts_as_magic=bool(op.counts_as_magic),
                    counts_as_material=op.counts_as_material,
                    counts_as_alignment=op.counts_as_alignment,
                )
                buffered_packets.append(pkt)
                continue
            
            flush_packets()

            if op.op == "heal_hp":
                if actor:
                    amt = int(eval_for_actor(op.amount, actor))
                    if target:
                        if getattr(op, "nonlethal_only", False):
                            target.nonlethal_damage = max(0, target.nonlethal_damage - amt)
                        else:
                            target.hp_current = min(target.hp_max, target.hp_current + amt)
                        out.append(f"[Heal] {target.name} +{amt} HP")
            elif op.op == "temp_hp":
                if self.resources and target and actor:
                    out += self.resources.grant_temp_hp(target.id, op.amount, effect_instance_id=parent_instance_id)
            elif op.op == "ability.damage":
                if target and actor:
                    ab = op.ability
                    sc = target.abilities.get(ab)
                    if sc:
                        sc.damage = max(0, sc.damage + int(eval_for_actor(op.amount, actor)))
                        out.append(f"[Ability] {target.name} {ab.upper()} damage +{op.amount}")
            elif op.op == "ability.drain":
                ...
            elif op.op == "condition.apply":
                if self.conditions and target and actor:
                    out += self.conditions.apply(op.id, actor, target, duration_override=op.duration, stacks=op.stacks, params=op.params)
            elif op.op == "condition.remove":
                if self.conditions and target:
                    out += self.conditions.remove(op.id, target=target)
            elif op.op == "resource.create":
                if self.resources and target:
                    _, logs2 = self.resources.create_from_definition(op.resource_id, owner_scope=op.owner_scope or "entity", owner_entity_id=target.id, initial_current=op.initial_current)
                    out += logs2
            elif op.op == "resource.spend":
                if self.resources and target and actor:
                    ok = self.resources.spend(target.id, op.resource_id, int(eval_for_actor(op.amount, actor)))
                    out.append(f"[Res] spend {op.resource_id} {'OK' if ok else 'insufficient'}")
            elif op.op == "resource.restore":
                if self.resources and target and actor:
                    amt = int(eval_for_actor(op.amount, actor)) if op.amount is not None else None
                    self.resources.restore(target.id, op.resource_id, amount=amt, to_max=op.to_max)
            elif op.op == "resource.set":
                ...
            elif op.op == "zone.create":
                if self.zones and target:
                    if op.zone_id:
                        _, logs2 = self.zones.create_from_definition(op.zone_id, target.id)
                    elif op.shape:
                        _, logs2 = self.zones.create_inline(op.name or "Zone", op.shape, op.duration, op.hooks or [], target.id)
                    out += logs2
            elif op.op == "zone.destroy":
                if self.zones and target:
                    out += self.zones.destroy(target.id, zone_definition_id=op.zone_id, zone_instance_id=op.zone_instance_id)
            elif op.op == "save":
                # A nested save op inside hooks/ops: roll locally and run branches
                # Resolve DC and roll a save on target using modifiers.resolved_stats
                ...
            else:
                out.append(f"[Effects] Unhandled op '{op.op}' (no-op)")

        # End: flush any remaining packets
        flush_packets()
        return out

    def tick_round(self) -> list[str]:
        logs: list[str] = []
        # decrement remaining_rounds for each entity's effects; detach on 0
        for entity_id, lst in list(self.state.active_effects.items()):
            keep: list[EffectInstance] = []
            for inst in lst:
                if inst.duration_type == "rounds" and inst.remaining_rounds is not None:
                    if inst.remaining_rounds > 0:
                        inst.remaining_rounds -= 1
                    if inst.remaining_rounds <= 0:
                        # unregister hooks and drop
                        if self.hooks:
                            self.hooks.unregister_by_parent(inst.instance_id)
                        logs.append(f"[Effects] {inst.name} expired")
                        continue
                keep.append(inst)
            self.state.active_effects[entity_id] = keep
        return logs

    def _snapshot_duration_rounds(self, ed: EffectDefinition, source: Entity, target: Entity) -> tuple[str, int | None]:
        ds = ed.duration
        if not ds:
            return "instantaneous", None
        if ds.type == "rounds":
            if ds.value is not None:
                return "rounds", max(0, int(ds.value))
            if ds.formula:
                v = eval_for_actor(ds.formula, source)
                return "rounds", max(0, int(v)) if isinstance(v, (int, float)) else None
            return "rounds", None
        return ds.type, None

    def attach(self, effect_id: str, source: Entity, target: Entity, *, bound_choices: Optional[dict] = None) -> list[str]:
        trace = TraceSession()
        logs: list[str] = []
        if effect_id not in self.content.effects:
            self.state.last_trace = ["[Trace] Unknown effect id."]
            return [f"[Effects] Unknown effect id: {effect_id}"]
        ed = self.content.effects[effect_id]

        trace.add(f"[Effect] {ed.name} ({ed.abilityType}) on {target.name}")

        # Antimagic and incoming.effect decisions
        if self.zones and ed.abilityType in ("Su","Sp","Spell"):
            if self.zones.is_entity_under_antimagic(target.id):
                msg = f"[Effects] {ed.name} suppressed by antimagic; no effect"
                logs.append(msg)
                trace.add(msg)
                self.state.last_trace = trace.dump()
                return logs
        if self.hooks:
            dec = self.hooks.incoming_effect(target.id, effect_def=ed, actor_entity_id=source.id)
            trace.add(dec.notes and f"[Hooks] incoming.effect: {'; '.join(dec.notes)}" or "[Hooks] incoming.effect: allow")
            if not dec.allow:
                msg = f"[Effects] {ed.name} blocked"
                logs.append(msg)
                trace.add(msg)
                self.state.last_trace = trace.dump()
                return logs

        # Before resolved stats
        before_stats = self.modifiers.resolved_stats(target) if self.modifiers else None
        if before_stats:
            trace.add(f"[Before] AC {before_stats['ac_total']} (T {before_stats['ac_touch']}/FF {before_stats['ac_ff']}), "
                      f"Atk +{before_stats['attack_melee_bonus']}/+{before_stats['attack_ranged_bonus']}, "
                      f"Saves F+{before_stats['save_fort']} R+{before_stats['save_ref']} W+{before_stats['save_will']}")

        # Gates
        if self.gates:
            outcome, glogs = self.gates.evaluate(ed, source, target)
            logs += glogs
            trace.extend(glogs)
            if not outcome.allowed:
                msg = f"[Effects] {ed.name} did not take effect"
                logs.append(msg)
                trace.add(msg)
                self.state.last_trace = trace.dump()
                return logs
        else:
            from .gates_runtime import GateOutcome, SRResult, SaveResult, AttackResult
            outcome = GateOutcome(True, SRResult(False,True,""), SaveResult(False,False,None,0,0,0,None,""),
                                  AttackResult(False,True,False,1,0,0,0,False,""), 1.0, False, 1)

        dur_type, rem_rounds = self._snapshot_duration_rounds(ed, source, target)
        inst = EffectInstance(
            definition_id=ed.id, name=ed.name, abilityType=ed.abilityType,
            source_entity_id=source.id, target_entity_id=target.id,
            duration_type=dur_type, remaining_rounds=rem_rounds, started_at_round=self.state.round_counter
        )
        if bound_choices:
            inst.variables.update({f"choice.{k}": v for k, v in bound_choices.items()})

        # Ops (with scaling/crit) -> logs already from damage/resources/conditions
        op_logs = self.execute_operations(list(ed.operations or []), source, target,
                                          parent_instance_id=inst.instance_id, logs=[],
                                          damage_scale=outcome.damage_scale, crit_mult=outcome.crit_mult)
        logs += op_logs
        trace.extend(op_logs)

        if dur_type == "instantaneous":
            msg = f"[Effects] {ed.name} (instantaneous) applied to {target.name}"
            logs.append(msg)
            trace.add(msg)
            # After/stats diff (instantaneous conditions/resources may have changed display stats too)
            after_stats = self.modifiers.resolved_stats(target) if self.modifiers else None
            if before_stats and after_stats and self.modifiers:
                trace.extend(self.modifiers.diff_stats(before_stats, after_stats))
            self.state.last_trace = trace.dump()
            return logs

        # Retain & register hooks
        self.state.active_effects.setdefault(target.id, []).append(inst)
        if self.hooks:
            self.hooks.register_for_effect(ed, inst.instance_id, target.id)
        if self.zones:
            logs += self.zones.update_suppression_for_entity(target.id)

        msg = f"[Effects] {ed.name} attached ({dur_type}{f' {rem_rounds} rounds' if rem_rounds is not None else ''})"
        logs.append(msg)
        trace.add(msg)

        # After resolved stats and diffs + (optional) per-path stacking explain
        after_stats = self.modifiers.resolved_stats(target) if self.modifiers else None
        if before_stats and after_stats and self.modifiers:
            trace.extend(self.modifiers.diff_stats(before_stats, after_stats))
            # Optional: explain key paths that changed
            key_paths = ["ac.natural","ac.deflection","ac.dodge","attack.melee.bonus","attack.ranged.bonus","save.fort","save.ref","save.will","speed.land"]
            trace.extend(self.modifiers.explain_paths(target, key_paths))

        self.state.last_trace = trace.dump()
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
