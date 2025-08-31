from __future__ import annotations
from typing import Optional, Literal, TYPE_CHECKING
from uuid import uuid4
from pydantic import BaseModel, Field
from dndrpg.engine.schema_models import ResourceDefinition, ResourceRefresh, AbsorptionSpec
from dndrpg.engine.expr import eval_for_actor
from dndrpg.engine.models import Entity
from dndrpg.engine.loader import ContentIndex

if TYPE_CHECKING:
    from .state import GameState

OwnerScope = Literal["entity", "effect-instance", "item", "zone"]

class ResourceState(BaseModel):
    state_id: str = Field(default_factory=lambda: uuid4().hex)
    definition_id: Optional[str] = None
    name: Optional[str] = None

    owner_scope: OwnerScope = "entity"
    owner_entity_id: Optional[str] = None
    owner_effect_instance_id: Optional[str] = None
    owner_item_id: Optional[str] = None
    owner_zone_id: Optional[str] = None

    current: int = 0
    max_computed: int = 0

    capacity_computeAt: Literal["attach","refresh","query"] = "attach"
    freezeOnAttach: bool = False

    refresh: Optional[ResourceRefresh] = None
    absorption: Optional[AbsorptionSpec] = None
    visibility: Optional[Literal["public","private","hidden"]] = "public"

    suppressed: bool = False
    # bookkeeping (simple round-based for now; extend later)
    last_refreshed_round: int = 0

class ResourceEngine:
    def __init__(self, content: ContentIndex, state: "GameState"):
        self.content = content
        self.state = state

    def _owner_key(self, scope: OwnerScope, entity_id: Optional[str], effect_id: Optional[str], item_id: Optional[str], zone_id: Optional[str]) -> str:
        if scope == "entity" and entity_id:
            return f"entity:{entity_id}"
        if scope == "effect-instance" and effect_id:
            return f"effect:{effect_id}"
        if scope == "item" and item_id:
            return f"item:{item_id}"
        if scope == "zone" and zone_id:
            return f"zone:{zone_id}"
        # default bucket (shouldn't happen)
        return "misc"

    def _attach_state(self, rs: ResourceState):
        key = self._owner_key(rs.owner_scope, rs.owner_entity_id, rs.owner_effect_instance_id, rs.owner_item_id, rs.owner_zone_id)
        self.state.resources.setdefault(key, []).append(rs)

    def _find_owner_entity(self, entity_id: Optional[str]) -> Optional[Entity]:
        if not entity_id:
            return None
        # For now only player; later track NPCs
        if self.state.player.id == entity_id:
            return self.state.player
        return None

    def _compute_capacity(self, rd: ResourceDefinition, owner: Entity) -> int:
        cap_expr = rd.capacity.formula
        val = eval_for_actor(str(cap_expr), owner)
        try:
            cap = int(val)
        except Exception:
            cap = 0
        if rd.capacity.cap is not None:
            cap = min(cap, rd.capacity.cap)
        return max(0, cap)

    def create_from_definition(
        self,
        def_id: str,
        *,
        owner_scope: Optional[OwnerScope] = None,
        owner_entity_id: Optional[str] = None,
        owner_effect_instance_id: Optional[str] = None,
        initial_current: Optional[int | str] = None
    ) -> tuple[ResourceState, list[str]]:
        logs: list[str] = []
        if def_id not in self.content.resources:
            return (None, [f"[Res] Unknown resource id: {def_id}"])  # type: ignore

        rd = self.content.resources[def_id]
        scope = owner_scope or rd.scope
        owner_ent = self._find_owner_entity(owner_entity_id)
        rs = ResourceState(
            definition_id=rd.id,
            name=rd.name or rd.id,
            owner_scope=scope,
            owner_entity_id=owner_entity_id if scope == "entity" else None,
            owner_effect_instance_id=owner_effect_instance_id if scope == "effect-instance" else None,
            capacity_computeAt=rd.capacity.get("computeAt", "attach"),  # type: ignore
            freezeOnAttach=bool(rd.freezeOnAttach),
            refresh=rd.refresh,
            absorption=rd.absorption,
            visibility=rd.visibility
        )
        # capacity
        if owner_ent:
            rs.max_computed = self._compute_capacity(rd, owner_ent)
        else:
            rs.max_computed = 0

        # set current
        if isinstance(initial_current, (int,)):
            rs.current = int(initial_current)
        elif isinstance(initial_current, str) and owner_ent:
            val = eval_for_actor(initial_current, owner_ent)
            rs.current = max(0, int(val)) if isinstance(val, (int,float)) else 0
        elif rd.initial_current is not None and owner_ent:
            if isinstance(rd.initial_current, (int, float)):
                rs.current = max(0, int(rd.initial_current))
            else:
                val = eval_for_actor(str(rd.initial_current), owner_ent)
                rs.current = max(0, int(val)) if isinstance(val, (int,float)) else 0
        else:
            rs.current = rs.max_computed

        self._attach_state(rs)
        logs.append(f"[Res] Created {rs.name} ({rs.current}/{rs.max_computed}) for {owner_ent.name if owner_ent else '?'}")
        return (rs, logs)

    def grant_temp_hp(self, owner_entity_id: str, amount_expr: str | int, *, effect_instance_id: Optional[str] = None) -> list[str]:
        # Use content res if present; else construct an ad-hoc effect-instance pool
        logs: list[str] = []
        rid = "res.temp_hp"
        owner = self._find_owner_entity(owner_entity_id)
        if not owner:
            return ["[Res] temp hp: unknown owner"]

        if rid in self.content.resources:
            rs, logs2 = self.create_from_definition(
                rid,
                owner_scope="effect-instance",
                owner_entity_id=owner_entity_id,
                owner_effect_instance_id=effect_instance_id,
                initial_current=amount_expr
            )
            logs += logs2
            return logs

        # Fallback ad-hoc resource state
        amount = int(eval_for_actor(str(amount_expr), owner)) if not isinstance(amount_expr, int) else int(amount_expr)
        rs = ResourceState(
            definition_id=None,
            name="Temporary Hit Points",
            owner_scope="effect-instance",
            owner_entity_id=owner_entity_id,
            owner_effect_instance_id=effect_instance_id,
            current=max(0, amount),
            max_computed=max(0, amount),
            capacity_computeAt="attach",
            freezeOnAttach=True,
            visibility="public"
        )
        self._attach_state(rs)
        logs.append(f"[Res] Granted Temp HP {rs.current} to {owner.name}")
        return logs

    def spend(self, owner_entity_id: str, resource_id: str, amount: int) -> bool:
        # simplistic: spend from first matching pool for this owner
        key = f"entity:{owner_entity_id}"
        # try entity scope first
        for rs in self.state.resources.get(key, []):
            if rs.definition_id == resource_id:
                if rs.current >= amount:
                    rs.current -= amount
                    return True
        # then any effect-instance owned by this entity
        for k, lst in self.state.resources.items():
            if not k.startswith("effect:"):
                continue
            for rs in lst:
                if rs.owner_entity_id == owner_entity_id and rs.definition_id == resource_id and rs.current >= amount:
                    rs.current -= amount
                    return True
        return False

    def restore(self, owner_entity_id: str, resource_id: str, amount: Optional[int] = None, to_max: bool = False):
        # Restore to entity-scoped first
        key = f"entity:{owner_entity_id}"
        for rs in self.state.resources.get(key, []):
            if rs.definition_id == resource_id:
                if to_max:
                    rs.current = rs.max_computed
                elif amount is not None:
                    rs.current = min(rs.max_computed, rs.current + int(amount))
                return True
        return False

    def set_current(self, owner_entity_id: str, resource_id: str, current: int) -> bool:
        key = f"entity:{owner_entity_id}"
        for rs in self.state.resources.get(key, []):
            if rs.definition_id == resource_id:
                rs.current = max(0, min(rs.max_computed, int(current)))
                return True
        return False

    def recompute_capacity(self, owner_entity_id: str, resource_id: str) -> bool:
        owner = self._find_owner_entity(owner_entity_id)
        if not owner:
            return False
        key = f"entity:{owner_entity_id}"
        for rs in self.state.resources.get(key, []):
            if rs.definition_id == resource_id:
                if rs.freezeOnAttach:
                    return False
                rd = self.content.resources.get(resource_id)
                if not rd:
                    return False
                rs.max_computed = self._compute_capacity(rd, owner)
                rs.current = min(rs.current, rs.max_computed)
                return True
        return False

    def refresh_cadence(self, cadence: str):
        # Simple: handle per_round for now (hook your scheduler later)
        if cadence != "per_round":
            return
        for key, lst in self.state.resources.items():
            for rs in lst:
                if not rs.refresh or rs.refresh.cadence != "per_round":
                    continue
                beh = rs.refresh.behavior
                if beh == "reset_to_max":
                    rs.current = rs.max_computed
                elif beh == "increment_by":
                    if rs.refresh.increment_by is not None and rs.owner_entity_id:
                        owner = self._find_owner_entity(rs.owner_entity_id)
                        inc = 0
                        if owner:
                            val = eval_for_actor(str(rs.refresh.increment_by), owner)
                            inc = int(val) if isinstance(val, (int,float)) else 0
                        rs.current = min(rs.max_computed, rs.current + max(0, inc))
                # no_change → nothing