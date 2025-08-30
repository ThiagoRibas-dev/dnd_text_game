from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union, Tuple
from typing_extensions import Annotated
from pydantic import BaseModel, Field, AliasChoices, model_validator

# Common aliases
Expr = Union[str, int, float]  # expressions or numeric literals

# Enums
AbilityType = Literal["Ex", "Su", "Sp", "Spell"]
SourceType = Literal["feat", "class", "spell", "power", "maneuver", "stance",
                     "soulmeld", "binding", "race", "item", "condition", "zone", "other"]
ActionType = Literal["passive", "free", "swift", "immediate", "reaction", "move", "standard", "full-round", "special"]
SaveType = Literal["Fort", "Ref", "Will"]
AttackMode = Literal["none", "melee", "ranged", "melee_touch", "ranged_touch", "ray", "special"]
RangeType = Literal["personal", "touch", "close", "medium", "long", "fixed-ft", "sight", "special"]
AreaShape = Literal["none", "line", "cone", "burst", "spread", "emanation", "cylinder", "wall", "sphere", "cube", "square"]
DurationType = Literal["instantaneous", "rounds", "minutes", "hours", "days", "permanent", "concentration", "special"]
Cadence = Literal["per_round", "per_encounter", "per_rest", "per_day", "per_week", "special"]
ScopeType = Literal["entity", "effect-instance", "item", "zone"]
ComputeAt = Literal["attach", "refresh", "query"]
Visibility = Literal["public", "private", "hidden"]
GateBranch = Literal["negates", "half", "partial", "none"]

# Modifiers
ModifierOperator = Literal["add", "subtract", "multiply", "divide", "set", "min", "max",
                           "replace", "replaceFormula", "cap", "clamp", "grantTag", "removeTag", "convertType"]
BonusType = Literal["enhancement", "morale", "luck", "insight", "competence", "sacred", "profane",
                    "resistance", "deflection", "dodge", "size", "natural_armor", "natural_armor_enhancement",
                    "circumstance", "alchemical", "unnamed"]

class Modifier(BaseModel):
    targetPath: str
    operator: ModifierOperator
    value: Expr | Dict[str, Any] = 0
    bonusType: Optional[BonusType] = None
    sourceKey: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    durationOverride: Optional[Dict[str, Any]] = None
    flags: Optional[Dict[str, Any]] = None

# -----------------------------
# Operation Kinds (stricter)
# -----------------------------

DamageKind = Literal[
    "physical.bludgeoning", "physical.piercing", "physical.slashing",
    "fire", "cold", "acid", "electricity", "sonic", "force",
    "negative", "positive", "nonlethal", "bleed", "typeless"
]

class OpDamage(BaseModel):
    op: Literal["damage"] = "damage"
    amount: Expr
    damage_type: DamageKind = "typeless"
    counts_as_magic: Optional[bool] = None
    counts_as_material: Optional[List[Literal["adamantine", "silver", "cold-iron"]]] = None
    counts_as_alignment: Optional[List[Literal["good", "evil", "law", "chaos"]]] = None
    nonlethal: Optional[bool] = None  # legacy convenience

    @model_validator(mode="after")
    def _validate(self):
        # Require amount present (Expr type ensures this).
        # Legacy: if nonlethal flag is true and damage_type wasn\'t explicitly set, coerce.
        if self.nonlethal and self.damage_type == "typeless":
            object.__setattr__(self, "damage_type", "nonlethal")
        return self

class OpHealHP(BaseModel):
    op: Literal["heal_hp"] = "heal_hp"
    amount: Expr
    nonlethal_only: bool = False

class OpTempHP(BaseModel):
    op: Literal["temp_hp"] = "temp_hp"
    amount: Expr

class OpConditionApply(BaseModel):
    op: Literal["condition.apply"] = "condition.apply"
    id: str
    duration: Optional["DurationSpec"] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    stacks: Optional[bool] = None

class OpConditionRemove(BaseModel):
    op: Literal["condition.remove"] = "condition.remove"
    id: str

class OpResourceCreate(BaseModel):
    op: Literal["resource.create"] = "resource.create"
    resource_id: str
    owner_scope: Optional[ScopeType] = None
    initial_current: Optional[Expr] = None

class OpResourceSpend(BaseModel):
    op: Literal["resource.spend"] = "resource.spend"
    resource_id: str
    amount: Expr

class OpResourceRestore(BaseModel):
    op: Literal["resource.restore"] = "resource.restore"
    resource_id: str
    amount: Optional[Expr] = None
    to_max: bool = False

    @model_validator(mode="after")
    def _require_amount_or_to_max(self):
        if self.amount is None and not self.to_max:
            raise ValueError("resource.restore requires either amount or to_max=true")
        return self

class OpResourceSet(BaseModel):
    op: Literal["resource.set"] = "resource.set"
    resource_id: str
    current: Expr

class OpZoneCreate(BaseModel):
    op: Literal["zone.create"] = "zone.create"
    zone_id: Optional[str] = None
    name: Optional[str] = None
    shape: Optional["AreaSpec"] = None
    duration: Optional["DurationSpec"] = None
    hooks: Optional[List["RuleHook"]] = None

    @model_validator(mode="after")
    def _require_id_or_inline(self):
        # Either: zone_id, or inline with at least name + shape
        if not self.zone_id:
            if not (self.name and self.shape):
                raise ValueError("zone.create requires zone_id OR inline name+shape")
        return self

class OpZoneDestroy(BaseModel):
    op: Literal["zone.destroy"] = "zone.destroy"
    zone_instance_id: Optional[str] = None
    zone_id: Optional[str] = None

    @model_validator(mode="after")
    def _require_target(self):
        if not self.zone_instance_id and not self.zone_id:
            raise ValueError("zone.destroy requires zone_instance_id or zone_id")
        return self

class OpSave(BaseModel):
    op: Literal["save"] = "save"
    type: "SaveType"
    dc: Expr = Field(validation_alias=AliasChoices("dc", "dcExpression")),
    on_success: List["Operation"] = Field(default_factory=list, validation_alias=AliasChoices("on_success", "onSuccess")),
    on_fail: List["Operation"] = Field(default_factory=list, validation_alias=AliasChoices("on_fail", "onFail")),

    @model_validator(mode="after")
    def _require_branch(self):
        if not self.on_success and not self.on_fail:
            raise ValueError("save requires at least one branch: on_success or on_fail")
        return self

class OpAttachEffect(BaseModel):
    op: Literal["attach"] = "attach"
    effect_id: str
    target: Optional[Literal["self", "target"]] = None

class OpDetachEffect(BaseModel):
    op: Literal["detach"] = "detach"
    effect_id: str
    all_instances: bool = False

class OpMove(BaseModel):
    op: Literal["move"] = "move"
    dx: Optional[int] = None
    dy: Optional[int] = None
    to: Optional[Tuple[int, int]] = None
    forced: bool = False

    @model_validator(mode="after")
    def _require_delta_or_to(self):
        has_delta = (self.dx is not None) or (self.dy is not None)
        has_to = self.to is not None
        if (has_delta and has_to) or (not has_delta and not has_to):
            raise ValueError("move requires either dx/dy OR to, but not both")
        return self

class OpTeleport(BaseModel):
    op: Literal["teleport"] = "teleport"
    to: Tuple[int, int]

class OpTransform(BaseModel):
    op: Literal["transform"] = "transform"
    form_id: Optional[str] = None
    size: Optional[str] = None
    set_stats: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _require_some_change(self):
        if not (self.form_id or self.size or self.set_stats):
            raise ValueError("transform requires form_id or size or set_stats")
        return self

class OpDispel(BaseModel):
    op: Literal["dispel"] = "dispel"
    effect_id: Optional[str] = None
    max_cl: Optional[Expr] = None

class OpSuppress(BaseModel):
    op: Literal["suppress"] = "suppress"
    target: Literal["effect", "item", "zone"]
    duration: "DurationSpec"

class OpUnsuppress(BaseModel):
    op: Literal["unsuppress"] = "unsuppress"
    target: Literal["effect", "item", "zone"]

class OpSchedule(BaseModel):
    op: Literal["schedule"] = "schedule"
    after: Optional["DurationSpec"] = None
    delay_rounds: Optional[int] = None
    actions: List["Operation"] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_timing_and_actions(self):
        if not self.actions:
            raise ValueError("schedule requires non-empty actions")
        if self.after is None and self.delay_rounds is None:
            raise ValueError("schedule requires after (DurationSpec) or delay_rounds")
        return self

# Discriminated union stays the same
Operation = Annotated[
    Union[
        OpDamage, OpHealHP, OpTempHP,
        OpConditionApply, OpConditionRemove,
        OpResourceCreate, OpResourceSpend, OpResourceRestore, OpResourceSet,
        OpZoneCreate, OpZoneDestroy,
        OpSave, OpAttachEffect, OpDetachEffect,
        OpMove, OpTeleport, OpTransform,
        OpDispel, OpSuppress, OpUnsuppress,
        OpSchedule
    ],
    Field(discriminator="op")
]

class ActModify(BaseModel):
    op: Literal["modify"] = "modify"
    targetPath: str
    operator: ModifierOperator  # "add" | "set" | "multiply" | ...
    value: Expr
    bonusType: Optional[BonusType] = None  # optional; mostly for clarity in logs

class ActReroll(BaseModel):
    op: Literal["reroll"] = "reroll"
    what: Literal["attack_roll", "miss_chance", "save", "crit_confirm", "skill_check"]
    keep: Literal["best", "success"] = "best"  # success = keep successful result if either succeeds

class ActCap(BaseModel):
    op: Literal["cap"] = "cap"
    target: Literal["incoming_damage", "outgoing_damage", "attack_roll", "damage_roll"]
    amount: Expr  # maximum allowed

class ActMultiply(BaseModel):
    op: Literal["multiply"] = "multiply"
    target: Literal["incoming_damage", "outgoing_damage", "attack_roll", "damage_roll"]
    factor: Expr  # e.g., 0.5 for resistance-like, 1.5 for vulnerability-like

class ActReflect(BaseModel):
    op: Literal["reflect"] = "reflect"
    what: Literal["damage", "effect"] = "damage"
    percent: int = 100  # 0–100
    to: Literal["source", "self"] = "source"  # simple routing

class ActRedirect(BaseModel):
    op: Literal["redirect"] = "redirect"
    what: Literal["damage", "effect"] = "damage"
    to: Literal["source", "self"] = "source"

class ActAbsorbIntoPool(BaseModel):
    op: Literal["absorbIntoPool"] = "absorbIntoPool"
    resource_id: str
    up_to: Expr                       # max amount to absorb
    damage_types: Optional[List[DamageKind]] = None  # if absent, absorb any

class ActSetOutcome(BaseModel):
    op: Literal["setOutcome"] = "setOutcome"
    kind: Literal[
        "block", "allow",          # targeting / incoming.effect / resource hooks
        "negate",                  # incoming.damage -> set to 0
        "hit", "miss",             # on.attack
        "success", "failure",      # on.save / on.crit (confirm)
        "suppress", "unsuppress"   # suppression
    ]
    note: Optional[str] = None

# HookAction union = hook-specific actions + a subset of Operation union you want to allow in hooks
HookAction = Annotated[
    Union[
        ActModify, ActReroll, ActCap, ActMultiply, ActReflect, ActRedirect, ActAbsorbIntoPool, ActSetOutcome,
        # Reuse operation types that make sense in hooks:
        OpSave, OpConditionApply, OpConditionRemove,
        OpResourceCreate, OpResourceSpend, OpResourceRestore, OpResourceSet,
        OpSchedule, OpDispel, OpSuppress, OpUnsuppress
    ],
    Field(discriminator="op")
]

# Rule Hooks (generic: match + actions)
HookScope = Literal["targeting", "incoming.effect", "incoming.condition", "incoming.damage",
                    "on.save", "on.attack", "on.damageDealt", "on.damageTaken", "on.crit",
                    "on.maneuverGrant", "scheduler", "suppression", "resource"]

class RuleHook(BaseModel):
    scope: HookScope
    match: Dict[str, Any] = Field(default_factory=dict)
    action: List[HookAction] = Field(default_factory=list)
    priority: Optional[int] = None
    duration: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _validate_actions_for_scope(self):
        # Map scopes to allowed op names
        allowed: Dict[str, List[str]] = {
            "targeting": ["setOutcome"],
            "incoming.effect": ["setOutcome", "save", "condition.apply", "condition.remove",
                                "resource.create", "resource.spend", "resource.restore", "resource.set",
                                "schedule", "dispel", "suppress", "unsuppress"],
            "incoming.damage": ["cap", "multiply", "reflect", "redirect", "absorbIntoPool",
                                "setOutcome", "resource.restore", "resource.spend", "schedule"],
            "on.save": ["reroll", "setOutcome", "resource.spend", "resource.restore",
                        "schedule", "condition.apply", "condition.remove"],
            "on.attack": ["modify", "reroll", "setOutcome", "resource.spend", "resource.restore", "schedule"],
            "on.damageDealt": ["cap", "multiply", "reflect", "resource.spend", "resource.restore",
                               "schedule", "condition.apply", "condition.remove"],
            "on.damageTaken": ["cap", "multiply", "reflect", "absorbIntoPool",
                               "resource.spend", "resource.restore", "schedule", "condition.apply", "condition.remove"],
            "on.crit": ["reroll", "setOutcome", "modify", "resource.spend", "resource.restore", "schedule"],
            "on.maneuverGrant": ["setOutcome", "resource.spend", "resource.restore", "schedule"],
            "scheduler": ["save", "condition.apply", "condition.remove", "resource.spend", "resource.restore", "schedule"],
            "suppression": ["setOutcome", "suppress", "unsuppress", "dispel", "schedule"],
            "resource": ["setOutcome", "resource.spend", "resource.restore", "schedule"],
        }
        # Allowed set for this hook
        allow = set(allowed.get(self.scope, []))

        # Helper for setOutcome kind per scope
        kind_allowed: Dict[str, List[str]] = {
            "targeting": ["block", "allow"],
            "incoming.effect": ["block", "allow", "suppress"],
            "incoming.damage": ["negate"],
            "on.save": ["success", "failure"],
            "on.attack": ["hit", "miss"],
            "on.crit": ["success", "failure"],
            "suppression": ["suppress", "unsuppress"],
            "resource": ["block", "allow"],
        }

        errs: List[str] = []
        for a in self.action:
            opname = getattr(a, "op", "")
            if opname not in allow:
                errs.append(f"Action '{opname}' not allowed in scope '{self.scope}'")
            # Additional check for setOutcome kinds
            if opname == "setOutcome":
                kinds = set(kind_allowed.get(self.scope, []))
                if kinds and getattr(a, "kind", None) not in kinds:
                    errs.append(f"setOutcome.kind '{getattr(a, 'kind', None)}' invalid for scope '{self.scope}' (allowed: {sorted(kinds)})")
        if errs:
            raise ValueError("; ".join(errs))
        return self


# Duration/Range/Area/Targeting
class DurationSpec(BaseModel):
    type: DurationType
    value: Optional[int] = None
    formula: Optional[str] = None
    end_conditions: Optional[List[str]] = None

class ActivationSpec(BaseModel):
    action: ActionType = "standard"
    provokesAoO: Optional[bool] = None
    costs: Optional[List[str]] = None
    concentration: Optional[bool] = None
    cooldown: Optional[int] = None

class RangeSpec(BaseModel):
    type: RangeType = "personal"
    distance_ft: Optional[int] = None

class AreaSpec(BaseModel):
    shape: AreaShape = "none"
    size_ft: Optional[int] = None
    length_ft: Optional[int] = None
    width_ft: Optional[int] = None
    radius_ft: Optional[int] = None

class TargetFilter(BaseModel):
    self: Optional[bool] = None
    ally: Optional[bool] = None
    enemy: Optional[bool] = None
    creature: Optional[bool] = None
    object: Optional[bool] = None
    type: Optional[List[str]] = None
    subtype: Optional[List[str]] = None
    alignment: Optional[List[str]] = None
    size: Optional[List[str]] = None
    HD_cap: Optional[int] = None
    count_cap: Optional[int] = None
    LoS: Optional[bool] = None
    LoE: Optional[bool] = None

# Gates
class SRGate(BaseModel):
    applies: bool = True

class SaveGate(BaseModel):
    type: SaveType
    dcExpression: str = Field(validation_alias=AliasChoices("dc", "dcExpression")),
    effect: GateBranch = "negates"

class AttackGate(BaseModel):
    mode: AttackMode = "none"
    ac_type: Optional[Literal["normal", "touch", "flat-footed"]] = None
    crit_behavior: Optional[str] = None

class Gates(BaseModel):
    sr: Optional[SRGate] = None
    save: Optional[SaveGate] = None
    attack: Optional[AttackGate] = None

# EffectDefinition
class EffectDefinition(BaseModel):
    id: str
    name: str
    source: SourceType = "spell"
    abilityType: AbilityType = "Spell"
    school: Optional[str] = None
    descriptors: List[str] = Field(default_factory=list)
    casterLevel: Optional[Expr] = None
    prerequisites: Optional[str] = None
    stacking: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

    activation: Optional[ActivationSpec] = None
    range: Optional[RangeSpec] = None
    targetFilter: Optional[TargetFilter] = None
    area: Optional[AreaSpec] = None

    when: Optional[str] = None  # "on activation" | "continuous" | "on trigger"
    duration: Optional[DurationSpec] = None
    triggers: Optional[List[Dict[str, Any]]] = None
    recurring: Optional[Dict[str, Any]] = None
    ongoing_save: Optional[Dict[str, Any]] = None

    gates: Optional[Gates] = None

    operations: List[Operation] = Field(default_factory=list)
    modifiers: List[Modifier] = Field(default_factory=list)
    ruleHooks: List[RuleHook] = Field(default_factory=list)

    resourceDefinitions: Optional[List[Dict[str, Any]]] = None
    choices: Optional[List[Dict[str, Any]]] = None

    srApplies: Optional[bool] = None
    antimagic: Optional[bool] = None
    dispellable: Optional[bool] = None

# ConditionDefinition
class ConditionDefinition(BaseModel):
    id: str
    name: str
    tags: List[str] = Field(default_factory=list)
    precedence: Optional[int] = None
    default_duration: Optional[DurationSpec] = None
    modifiers: List[Modifier] = Field(default_factory=list)
    ruleHooks: List[RuleHook] = Field(default_factory=list)
    notes: Optional[str] = None

# ResourceDefinition
class ResourceRefresh(BaseModel):
    cadence: Cadence
    behavior: Literal["reset_to_max", "increment_by", "no_change"] = "reset_to_max"
    increment_by: Optional[Expr] = None
    triggers: Optional[List[str]] = None

class ResourceDefinition(BaseModel):
    id: str
    name: Optional[str] = None
    scope: ScopeType = "entity"
    capacity: Dict[str, Any]  # { formula: str, cap?: int, computeAt?: 'attach'|'refresh'|'query' }
    initial_current: Optional[Expr] = None
    refresh: Optional[ResourceRefresh] = None
    expiry: Optional[Dict[str, Any]] = None
    absorption: Optional[Dict[str, Any]] = None  # absorbTypes, perHit, order
    visibility: Optional[Visibility] = "public"
    stacking: Optional[Dict[str, Any]] = None
    recomputeOn: Optional[List[str]] = None
    freezeOnAttach: Optional[bool] = None
    notes: Optional[str] = None

# TaskDefinition (Downtime/Exploration tasks)
class TaskDefinition(BaseModel):
    id: str
    name: str
    timeUnit: Literal["minutes", "hours", "days", "weeks"]
    step: int  # tick size in timeUnit
    inputs: Optional[List[str]] = None
    costs: Optional[List[Dict[str, Any]]] = None
    hooks: List[RuleHook] = Field(default_factory=list)  # scheduler hooks like "eachStep"
    progress: Optional[Dict[str, Any]] = None
    completion: Optional[Dict[str, Any]] = None
    interrupts: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

# ZoneDefinition
class ZoneDefinition(BaseModel):
    id: str
    name: str
    shape: AreaSpec
    duration: Optional[DurationSpec] = None
    hooks: List[RuleHook] = Field(default_factory=list)  # on-enter/on-leave/startOfTurn
    stacking: Optional[Dict[str, Any]] = None
    suppression: Optional[Dict[str, Any]] = None
    owner_tags: Optional[List[str]] = None
    notes: Optional[str] = None

ActModify.model_rebuild()
ActReroll.model_rebuild()
ActCap.model_rebuild()
ActMultiply.model_rebuild()
ActReflect.model_rebuild()
ActRedirect.model_rebuild()
ActAbsorbIntoPool.model_rebuild()
ActSetOutcome.model_rebuild()
HookAction.__args__  # no-op to keep linters quiet
RuleHook.model_rebuild()
