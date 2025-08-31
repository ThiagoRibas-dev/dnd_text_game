from __future__ import annotations
from typing import Optional, List, Tuple, TYPE_CHECKING
from uuid import uuid4
from pydantic import BaseModel, Field
from dndrpg.engine.schema_models import ZoneDefinition, AreaSpec, DurationSpec, RuleHook
from dndrpg.engine.loader import ContentIndex
from dndrpg.engine.rulehooks_runtime import RuleHooksRegistry
if TYPE_CHECKING:
    from .state import GameState

class ZoneInstance(BaseModel):
    instance_id: str = Field(default_factory=lambda: uuid4().hex)
    definition_id: Optional[str] = None
    name: str
    owner_entity_id: Optional[str] = None

    shape: AreaSpec
    duration_type: str = "instantaneous"
    remaining_rounds: Optional[int] = None
    active: bool = True
    notes: Optional[str] = None

class ZoneEngine:
    """
    Minimal zone manager:
     - create_from_definition() or create_inline()
     - registers hooks on the owner's entity via RuleHooksRegistry
     - tick_round() reduces remaining rounds and unregisters hooks on expiry
    """

    def __init__(self, content: ContentIndex, state: "GameState", hooks: RuleHooksRegistry):
        self.content = content
        self.state = state
        self.hooks = hooks

    def _snapshot_duration(self, zd: ZoneDefinition) -> Tuple[str, Optional[int]]:
        ds = zd.duration
        if ds is None:
            return ("permanent", None)
        if ds.type == "rounds":
            if ds.value is not None:
                return ("rounds", max(0, int(ds.value)))
            return ("rounds", None)
        return (ds.type, None)

    def create_from_definition(self, zone_id: str, owner_entity_id: str) -> Tuple[Optional[ZoneInstance], List[str]]:
        logs: List[str] = []
        zd = self.content.zones.get(zone_id)
        if not zd:
            logs.append(f"[Zone] unknown zone id: {zone_id}")
            return (None, logs)
        dur_type, rem = self._snapshot_duration(zd)
        zi = ZoneInstance(
            definition_id=zd.id,
            name=zd.name,
            owner_entity_id=owner_entity_id,
            shape=zd.shape,
            duration_type=dur_type,
            remaining_rounds=rem
        )
        self.state.active_zones.setdefault(owner_entity_id, []).append(zi)
        # Register hooks on owner's entity
        for h in zd.hooks or []:
            self.hooks._register(h, source_kind="zone", source_id=zd.id, source_name=zd.name,
                                 parent_instance_id=zi.instance_id, target_entity_id=owner_entity_id)
        logs.append(f"[Zone] Created {zd.name} ({dur_type}{f' {rem} rounds' if rem is not None else ''}) on {owner_entity_id}")
        return (zi, logs)

    def create_inline(self, name: str, shape: AreaSpec, duration: DurationSpec, hooks: List[RuleHook], owner_entity_id: str) -> Tuple[ZoneInstance, List[str]]:
        logs: List[str] = []
        zi = ZoneInstance(
            definition_id=None,
            name=name,
            owner_entity_id=owner_entity_id,
            shape=shape,
            duration_type=duration.type,
            remaining_rounds=duration.value if duration.type == "rounds" else None
        )
        self.state.active_zones.setdefault(owner_entity_id, []).append(zi)
        for h in hooks or []:
            self.hooks._register(h, source_kind="zone", source_id=f"zone:{name}", source_name=name,
                                 parent_instance_id=zi.instance_id, target_entity_id=owner_entity_id)
        logs.append(f"[Zone] Created {name} ({duration.type}{f' {zi.remaining_rounds} rounds' if zi.remaining_rounds is not None else ''}) on {owner_entity_id}")
        return (zi, logs)

    def destroy(self, owner_entity_id: str, *, zone_definition_id: Optional[str] = None, zone_instance_id: Optional[str] = None) -> List[str]:
        logs: List[str] = []
        lst = self.state.active_zones.get(owner_entity_id, [])
        keep: List[ZoneInstance] = []
        for zi in lst:
            match = (zone_instance_id and zi.instance_id == zone_instance_id) or (zone_definition_id and zi.definition_id == zone_definition_id)
            if match:
                self.hooks.unregister_by_parent(zi.instance_id)
                logs.append(f"[Zone] Destroyed {zi.name}")
            else:
                keep.append(zi)
        self.state.active_zones[owner_entity_id] = keep
        return logs

    def tick_round(self) -> List[str]:
        logs: List[str] = []
        for owner_id, lst in list(self.state.active_zones.items()):
            keep: List[ZoneInstance] = []
            for zi in lst:
                if zi.duration_type == "rounds" and zi.remaining_rounds is not None:
                    if zi.remaining_rounds > 0:
                        zi.remaining_rounds -= 1
                    if zi.remaining_rounds <= 0:
                        self.hooks.unregister_by_parent(zi.instance_id)
                        logs.append(f"[Zone] {zi.name} expired")
                        continue
                keep.append(zi)
            self.state.active_zones[owner_id] = keep
        return logs