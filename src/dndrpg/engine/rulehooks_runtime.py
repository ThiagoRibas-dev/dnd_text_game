from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Literal
from uuid import uuid4
from pydantic import BaseModel, Field

from dndrpg.engine.schema_models import RuleHook, EffectDefinition, ConditionDefinition, HookAction, ZoneDefinition
from dndrpg.engine.models import Entity
from dndrpg.engine.loader import ContentIndex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dndrpg.engine.effects_runtime import EffectsEngine
    from dndrpg.engine.conditions_runtime import ConditionsEngine
    from dndrpg.engine.resources_runtime import ResourceEngine
    from .state import GameState

# ------------------------------
# Runtime types
# ------------------------------

@dataclass
class HookDecision:
    # For incoming.effect: allow or block (default allow); suppress would suppress if engine supported
    allow: bool = True
    suppress: bool = False
    notes: List[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []

class RegisteredHook(BaseModel):
    hook_id: str = Field(default_factory=lambda: uuid4().hex)
    scope: str
    match: Dict[str, Any] = Field(default_factory=dict)
    actions: List[HookAction] = Field(default_factory=list)
    priority: int = 0

    source_kind: Literal["effect","condition","zone"] = "effect"

class RuleHooksRegistry:
    """
    Maintains registered hooks per target entity and scope, and provides dispatch APIs.
    This registry is used by EffectsEngine and ConditionsEngine to register hooks at attach/apply time,
    and to remove them on detach/expire.
    """

    def __init__(self, content: ContentIndex, state: "GameState",
                 effects: EffectsEngine, conditions: ConditionsEngine, resources: ResourceEngine):
        self.content = content
        self.state = state
        self.effects = effects
        self.conditions = conditions
        self.resources = resources

        # scope -> target_entity_id -> list of RegisteredHook (sorted by priority)
        self._by_scope: Dict[str, Dict[str, List[RegisteredHook]]] = {}

        # reverse map for cleanup: parent_instance_id -> list of (scope, target_id, hook_id)
        self._parent_index: Dict[str, List[Tuple[str, str, str]]] = {}

    # -------- Register / unregister --------

    def register_for_effect(self, ed: EffectDefinition, parent_instance_id: str, target_entity_id: str):
        for h in ed.ruleHooks or []:
            self._register(h, source_kind="effect", source_id=ed.id, source_name=ed.name,
                           parent_instance_id=parent_instance_id, target_entity_id=target_entity_id)

    def register_for_condition(self, cd: ConditionDefinition, parent_instance_id: str, target_entity_id: str):
        for h in cd.ruleHooks or []:
            self._register(h, source_kind="condition", source_id=cd.id, source_name=cd.name,
                           parent_instance_id=parent_instance_id, target_entity_id=target_entity_id)

    def register_for_zone(self, zd: ZoneDefinition, zone_instance_id: str, target_entity_id: str):
        for h in zd.hooks or []:
            self._register(h, source_kind="zone", source_id=zd.id, source_name=zd.name,
                           parent_instance_id=zone_instance_id, target_entity_id=target_entity_id)

    def _register(self, hook_def: RuleHook, *, source_kind: str, source_id: str, source_name: str,
                  parent_instance_id: str, target_entity_id: str):
        rh = RegisteredHook(
            scope=hook_def.scope,
            match=hook_def.match or {},
            actions=list(hook_def.action or []),
            priority=int(hook_def.priority or 0),
            source_kind=source_kind,
            source_id=source_id,
            source_name=source_name,
            parent_instance_id=parent_instance_id,
            target_entity_id=target_entity_id
        )
        bucket = self._by_scope.setdefault(rh.scope, {}).setdefault(target_entity_id, [])
        bucket.append(rh)
        bucket.sort(key=lambda r: r.priority)  # low number first
        self._parent_index.setdefault(parent_instance_id, []).append((rh.scope, target_entity_id, rh.hook_id))

    def unregister_by_parent(self, parent_instance_id: str):
        entries = self._parent_index.pop(parent_instance_id, [])
        for scope, target_id, hook_id in entries:
            lst = self._by_scope.get(scope, {}).get(target_id, [])
            self._by_scope[scope][target_id] = [h for h in lst if h.hook_id != hook_id]

    # -------- Dispatch helpers --------

    def _entity_by_id(self, ent_id: str) -> Optional[Entity]:
        if self.state.player.id == ent_id:
            return self.state.player
        return None

    def _match(self, rh: RegisteredHook, context: Dict[str, Any]) -> bool:
        # Very simple deep match: all keys in rh.match must exist in context and equal
        # For 'event' we allow exact or startswith for 'startOfTurn(...)'
        for k, v in (rh.match or {}).items():
            if k == "event":
                ev = context.get("event")
                if isinstance(v, str):
                    if not isinstance(ev, str) or (ev != v and not ev.startswith(v)):
                        return False
                else:
                    return False
            else:
                if context.get(k) != v:
                    return False
        return True

    def _exec_action(self, action: HookAction, *, actor: Optional[Entity], target: Optional[Entity], logs: List[str]):
        """
        Execute a subset of actions inline. We delegate Operation union kinds to EffectsEngine's executor (save/condition/resource ops).
        Special HookAction kinds we handle here: setOutcome (by putting a flag into logs/context), multiply/cap/reflect etc.
        For now, we only use setOutcome for decisions; other transforms are returned by dispatchers that need them.
        """
        # These operation types we let EffectsEngine handle through a small executor
        op_name = getattr(action, "op", None)
        if op_name in ("save", "condition.apply", "condition.remove",
                       "resource.create", "resource.spend", "resource.restore", "resource.set"):
            # Reuse EffectsEngine executor util (create a thin wrapper method)
            self.effects.execute_operations([action], actor, target, parent_instance_id=None, logs=logs)
            return

        if op_name == "schedule":
            delay = getattr(action, "delay_rounds", None)
            if delay is not None and target:
                # schedule actions (action.actions is a list[Operation])
                self.effects.scheduler.schedule_in_rounds(target.id, int(delay), list(getattr(action, "actions", [])))
                logs.append(f"[Hooks] scheduled {len(getattr(action, 'actions', []))} action(s) in {delay} round(s)")
            return

        # HookAction-specific (modify/reroll/cap/multiply/reflect/redirect/absorbIntoPool/setOutcome)
        if op_name == "setOutcome":
            # setOutcome is handled in the dispatchers (they inspect actions and set decisions)
            # No immediate effect here
            return

        # Other transforms (modify/reroll, multiply/cap/reflect etc.) handled by respective dispatchers (attack/save/damage)
        return

    # -------- Incoming effect decision --------

    def incoming_effect(self, target_entity_id: str, *, effect_def: EffectDefinition, actor_entity_id: Optional[str] = None) -> HookDecision:
        dec = HookDecision()
        hooks = list(self._by_scope.get("incoming.effect", {}).get(target_entity_id, []))
        if not hooks:
            return dec
        actor = self._entity_by_id(actor_entity_id) if actor_entity_id else None
        target = self._entity_by_id(target_entity_id)
        ctx = {
            "abilityType": effect_def.abilityType,
            "source": effect_def.source,
            "event": "incoming.effect"
        }
        logs: List[str] = []
        for rh in hooks:
            if self._is_parent_suppressed(rh):
                continue
            if not self._match(rh, ctx):
                continue
            for act in rh.actions:
                if getattr(act, "op", None) == "setOutcome":
                    kind = getattr(act, "kind", None)
                    if kind == "block":
                        dec.allow = False
                        dec.notes.append(f"Blocked by {rh.source_name}")
                    elif kind == "allow":
                        dec.allow = True
                        dec.notes.append(f"Allowed by {rh.source_name}")
                    elif kind == "suppress":
                        dec.suppress = True
                        dec.notes.append(f"Suppressed by {rh.source_name}")
                else:
                    # Execute operations embedded in hooks if any (e.g., log, resource change)
                    self._exec_action(act, actor=actor, target=target, logs=logs)
        if logs:
            dec.notes.extend(logs)
        return dec

    # -------- Scheduler events --------

    def scheduler_event(self, target_entity_id: str, event: str, *, actor_entity_id: Optional[str] = None) -> List[str]:
        """
        Dispatch scheduler hooks with match.event matching the event string.
        Example events: "startOfTurn", "endOfTurn", "eachRound", "onStart", "eachStep", "onComplete"
        """
        out: List[str] = []
        hooks = list(self._by_scope.get("scheduler", {}).get(target_entity_id, []))
        if not hooks:
            return out
        actor = self._entity_by_id(actor_entity_id) if actor_entity_id else None
        target = self._entity_by_id(target_entity_id)
        ctx = {"event": event}
        for rh in hooks:
            if self._is_parent_suppressed(rh):
                continue
            if not self._match(rh, ctx):
                continue
            for act in rh.actions:
                self._exec_action(act, actor=actor, target=target, logs=out)
        return out

    # -------- Attack / Save / Damage entry points (stubs for now) --------

    def on_attack(self, target_entity_id: str, phase: Literal["pre","post"], attack_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder for attack hook processing. Returns a dict of flags or transforms:
          { "setOutcome": "hit/miss", "reroll": { "what":"miss_chance","keep":"success"}, "modify": [ ... ], "cap": X, "multiply": Y, ... }
        For now, we just scan for setOutcome and return it; others can be added later when you implement attack resolution.
        """
        result: Dict[str, Any] = {}
        hooks = list(self._by_scope.get("on.attack", {}).get(target_entity_id, []))
        if not hooks:
            return result
        ctx = {"event": f"on.attack.{phase}"}
        for rh in hooks:
            if self._is_parent_suppressed(rh):
                continue
            if not self._match(rh, ctx):
                continue
            for act in rh.actions:
                if getattr(act, "op", None) == "setOutcome":
                    result["setOutcome"] = getattr(act, "kind", None)
        return result

    def on_save(self, target_entity_id: str, phase: Literal["pre","post"], save_context: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        hooks = list(self._by_scope.get("on.save", {}).get(target_entity_id, []))
        if not hooks:
            return result
        ctx = {"event": f"on.save.{phase}"}
        for rh in hooks:
            if self._is_parent_suppressed(rh):
                continue
            if not self._match(rh, ctx):
                continue
            for act in rh.actions:
                if getattr(act, "op", None) == "setOutcome":
                    result["setOutcome"] = getattr(act, "kind", None)
        return result

    def incoming_damage(self, target_entity_id: str, damage_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder for damage hook transforms.
        Returns a dict like {"multiply": 0.5, "cap": 10, "absorbIntoPool": {...}, "reflect": 50}
        """
        result: Dict[str, Any] = {}
        hooks = list(self._by_scope.get("incoming.damage", {}).get(target_entity_id, []))
        if not hooks:
            return result
        ctx = {"event": "incoming.damage"}
        for rh in hooks:
            if self._is_parent_suppressed(rh):
                continue
            if not self._match(rh, ctx):
                continue
            for act in rh.actions:
                op = getattr(act, "op", None)
                if op == "multiply":
                    result["multiply"] = getattr(act, "factor", 1.0)
                elif op == "cap":
                    result["cap"] = getattr(act, "amount", None)
                elif op == "absorbIntoPool":
                    result["absorbIntoPool"] = {"resource_id": getattr(act, "resource_id", None),
                                                "up_to": getattr(act, "up_to", 0),
                                                "damage_types": getattr(act, "damage_types", None)}
                elif op == "reflect":
                    result["reflect"] = getattr(act, "percent", 100)
        return result