from __future__ import annotations
from typing import Optional, Dict, List, TYPE_CHECKING
from uuid import uuid4
import random
from pydantic import BaseModel, Field
from .schema_models import Operation
from .expr import eval_for_actor
from .models import Entity
from .loader import ContentIndex
from dndrpg.engine.resources_runtime import ResourceEngine
from dndrpg.engine.conditions_runtime import ConditionsEngine
from .damage_runtime import DamageEngine, DamagePacket, AttackContext
from .zones_runtime import ZoneEngine
from .gates_runtime import GatesEngine, GateOutcome
from .modifiers_runtime import ModifiersEngine

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
                 hooks: RuleHooksRegistry | None = None,
                 damage: DamageEngine | None = None,
                 zones: ZoneEngine | None = None,
                 modifiers: ModifiersEngine | None = None,
                 rng: Optional[random.Random] = None):
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
            opname = getattr(op, "op", None)
            if opname == "damage":
                amt = getattr(op, "amount", 0)
                base = amt if isinstance(amt, (int, float)) else eval_for_actor(str(amt), actor) if actor else 0
                final = int(round(float(base) * max(0.0, damage_scale) * max(1, crit_mult)))
                dtype = getattr(op, "damage_type", "typeless")
                pkt = DamagePacket(
                    amount=max(0, int(final)),
                    dkind=dtype,
                    counts_as_magic=bool(getattr(op, "counts_as_magic", False)),
                    counts_as_material=getattr(op, "counts_as_material", None),
                    counts_as_alignment=getattr(op, "counts_as_alignment", None),
                )
                buffered_packets.append(pkt)
                continue
            else:
                # If we encounter a non-damage op, flush any accumulated packets first
                flush_packets()
                # ... handle other ops as before ...

        # End: flush any remaining packets
        flush_packets()
        # NOTE: The original function returned `out`, but the new one doesn't explicitly. Assuming it should.
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

    def attach(self, effect_id: str, source: Entity, target: Entity) -> list[str]:
        logs: list[str] = []
        if effect_id not in self.content.effects:
            return [f"[Effects] Unknown effect id: {effect_id}"]
        ed = self.content.effects[effect_id]

        # Antimagic / incoming.effect handled earlier (unchanged) ...
        if self.zones and ed.abilityType in ("Su","Sp","Spell"):
            if self.zones.is_entity_under_antimagic(target.id):
                logs.append(f"[Effects] {ed.name} suppressed by antimagic; no effect")
                return logs
        if self.hooks:
            dec = self.hooks.incoming_effect(target.id, effect_def=ed, actor_entity_id=source.id)
            if not dec.allow:
                logs.append(f"[Effects] {ed.name} blocked ({'; '.join(dec.notes)})")
                return logs

        # Gates: SR -> Save -> Attack
        if self.gates:
            outcome, glogs = self.gates.evaluate(ed, source, target)
            logs += glogs
            if not outcome.allowed:
                logs.append(f"[Effects] {ed.name} did not take effect")
                return logs
        else:
            outcome = GateOutcome(True, None, None, None, 1.0, False, 1)  # type: ignore

        dur_type, rem_rounds = self._snapshot_duration_rounds(ed, source, target)
        inst = EffectInstance(
            definition_id=ed.id, name=ed.name, abilityType=ed.abilityType,
            source_entity_id=source.id, target_entity_id=target.id,
            duration_type=dur_type, remaining_rounds=rem_rounds, started_at_round=self.state.round_counter
        )

        # Execute operations with gate scaling/crit
        self.execute_operations(list(ed.operations or []), source, target,
                                parent_instance_id=inst.instance_id, logs=logs,
                                damage_scale=outcome.damage_scale, crit_mult=outcome.crit_mult)

        if dur_type == "instantaneous":
            logs.append(f"[Effects] {ed.name} (instantaneous) applied to {target.name}")
            return logs

        self.state.active_effects.setdefault(target.id, []).append(inst)
        if self.hooks:
            self.hooks.register_for_effect(ed, inst.instance_id, target.id)
        if self.zones:
            logs += self.zones.update_suppression_for_entity(target.id)
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
