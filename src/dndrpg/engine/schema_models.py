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

# Canonical condition tags (from 3.5e Conditions section)
ConditionTag = Literal[
    "blinded","blown_away","checked","confused","cowering","dazed","dazzled",
    "dead","deafened","disabled","dying","energy_drained","entangled","exhausted",
    "fascinated","fatigued","flat_footed","frightened","grappling","helpless",
    "incorporeal","invisible","knocked_down","nauseated","panicked","paralyzed",
    "petrified","pinned","prone","shaken","sickened","stable","staggered","stunned",
    "turned","unconscious"
]

# Modifiers
ModifierOperator = Literal[
    "add","subtract","multiply","divide","set","min","max","replace","replaceFormula","cap","clamp","grantTag","removeTag","convertType"
]
BonusType = Literal[
    "enhancement","morale","luck","insight","competence","sacred","profane",
    "resistance","deflection","dodge","size","natural_armor","natural_armor_enhancement",
    "circumstance","alchemical","unnamed"
]

_ALLOWED_PREFIXES = {
    # as requested
    "abilities","ac","save","resist","dr","speed","senses","tags","resources",
    # practical additions so existing and common content doesn’t break
    "attack","bab"
}

_NUMERIC_OPS = {"add","subtract","multiply","divide","set","min","max","cap","clamp","replace"}  # replace used as set/overwrite

class Modifier(BaseModel):
    targetPath: str
    operator: ModifierOperator
    value: Expr | Dict[str, Any] = 0
    bonusType: Optional[BonusType] = None
    sourceKey: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    durationOverride: Optional[Dict[str, Any]] = None
    flags: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _validate(self):
        errs: list[str] = []

        # 1) Prefix allowlist
        prefix = self.targetPath.split(".", 1)[0]
        if prefix not in _ALLOWED_PREFIXES:
            errs.append(
                f"targetPath prefix '{prefix}' not allowed; allowed: "
                f"{sorted(_ALLOWED_PREFIXES)}"
            )

        # 2) Deprecate replaceFormula
        if self.operator == "replaceFormula":
            errs.append("operator 'replaceFormula' is deprecated; use 'set' or 'replace'")

        # 3) value required for numeric operators
        if self.operator in _NUMERIC_OPS and self.value is None:
            errs.append(f"modifier.value is required for operator '{self.operator}'")

        # 4) Operator+target combos and bonusType requirements
        if prefix == "tags":
            if self.operator not in {"grantTag","removeTag"}:
                errs.append("tags.* supports only 'grantTag' or 'removeTag'")
        elif prefix == "speed":
            if self.operator not in {"add","set","multiply","min","max","cap","clamp"}:
                errs.append("speed.* allows only add/set/multiply/min/max/cap/clamp")
        elif prefix == "senses":
            if self.operator not in {"add","set","min","max"}:
                errs.append("senses.* allows only add/set/min/max")
        elif prefix in {"resist","dr"}:
            if self.operator in {"multiply","divide"}:
                errs.append(f"{prefix}.* does not support '{self.operator}' (use add/set/max)")
        elif prefix == "resources":
            if self.operator not in {"add","set","min","max","cap","clamp"}:
                errs.append("resources.* allows only add/set/min/max/cap/clamp")
        elif prefix in {"ac","save","abilities","attack","bab"}:
            # Disallow weird math on core combat stats
            if self.operator in {"multiply","divide"} and prefix in {"ac","save","abilities"}:
                errs.append(f"{prefix}.* does not support '{self.operator}'")
            # For additive bonuses on typed-stacking stats, require a bonusType
            if self.operator in {"add","subtract"}:
                if self.bonusType is None:
                    errs.append(
                        f"{prefix} additive modifiers require bonusType "
                        f"(use 'unnamed' if truly untyped; beware stacking)"
                    )
        # 5) convertType belongs in rules/hook actions, not generic modifiers
        if self.operator == "convertType":
            errs.append("operator 'convertType' is not valid as a generic Modifier; use a RuleHook action")

        if errs:
            raise ValueError("; ".join(errs))
        return self

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

    @model_validator(mode="after")
    def _validate(self):
        if self.type == "fixed-ft":
            if self.distance_ft is None or self.distance_ft <= 0:
                raise ValueError("range.type 'fixed-ft' requires positive distance_ft")
        return self

class AreaSpec(BaseModel):
    shape: AreaShape = "none"
    size_ft: Optional[int] = None
    length_ft: Optional[int] = None
    width_ft: Optional[int] = None
    radius_ft: Optional[int] = None

    @model_validator(mode="after")
    def _validate(self):
        s = self.shape
        if s in ("none",):
            return self
        if s in ("square", "cube"):
            if not self.size_ft or self.size_ft <= 0:
                raise ValueError(f"area.shape '{s}' requires size_ft > 0")
        elif s in ("burst", "sphere", "emanation"):
            if not self.radius_ft or self.radius_ft <= 0:
                raise ValueError(f"area.shape '{s}' requires radius_ft > 0")
        elif s == "cone":
            if not self.length_ft or self.length_ft <= 0:
                raise ValueError("area.shape 'cone' requires length_ft > 0")
        elif s == "line":
            if not self.length_ft or self.length_ft <= 0:
                raise ValueError("area.shape 'line' requires length_ft > 0")
            # default width to 5 if omitted
            if self.width_ft is None:
                object.__setattr__(self, "width_ft", 5)
        elif s == "cylinder":
            if not self.radius_ft or self.radius_ft <= 0 or not self.length_ft or self.length_ft <= 0:
                raise ValueError("area.shape 'cylinder' requires radius_ft > 0 and length_ft > 0")
        elif s == "wall":
            if not self.length_ft or self.length_ft <= 0:
                raise ValueError("area.shape 'wall' requires length_ft > 0")
            # width_ft optional; default to 5 if omitted
            if self.width_ft is None:
                object.__setattr__(self, "width_ft", 5)
        return self

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

    @model_validator(mode="after")
    def _validate(self):
        if self.mode in ("melee_touch", "ranged_touch", "ray"):
            if self.ac_type != "touch":
                raise ValueError(f"attackGate.mode '{self.mode}' requires ac_type='touch'")
        if self.ac_type == "flat-footed" and self.mode not in ("melee", "ranged"):
            raise ValueError("ac_type='flat-footed' allowed only with mode melee or ranged")
        return self

class Gates(BaseModel):
    sr: Optional[SRGate] = None
    save: Optional[SaveGate] = None
    attack: Optional[AttackGate] = None

class StackingPolicy(BaseModel):
    # 1) Named (effect-level) exclusivity within a “named key”
    # - no_stack_highest: keep the instance with highest magnitude (see magnitudeExpr or fallback)
    # - no_stack_latest: keep the newest instance; older instances suppressed
    # - stack: allow multiple instances to coexist (rare at effect-level)
    named: Optional[Literal["no_stack_highest", "no_stack_latest", "stack"]] = None

    # Which key defines “same named effect”
    # - "id" (default) → treat same effect id as same named
    # - "name" → same display name
    # - "group:<key>" → uses entries in familyKeys to build groups (see below)
    # - "tag:<tag>" → engines can precompute a tag membership set
    namedKey: Optional[str] = None

    # How to compare for no_stack_highest
    # - "magnitudeExpr" is an expression evaluated per effect instance (actor context)
    # - If omitted, engine falls back to a heuristic (see runtime notes)
    magnitudeExpr: Optional[str] = None

    # 2) Family/exclusion groups (for “not cumulative with similar effects” across different effect ids)
    # all effects sharing any of these keys are mutually exclusive
    familyKeys: Optional[List[str]] = None
    familyPolicy: Optional[Literal["exclusive_highest", "exclusive_latest"]] = None

    # 3) Same-source rule (primarily for untyped)
    # - no_stack: ignore additive untyped modifiers with identical sourceKey
    # - stack: allow (default is no_stack to match common “same source” clause)
    sameSource: Optional[Literal["no_stack", "stack"]] = None

    # 4) Per-bonus-type override of the global typed-stacking defaults
    # - defaultTyped is applied when a type isn’t explicitly listed
    # - Values: "stack" or "no_stack_highest"
    bonusTypePolicy: Optional[Dict[
        Literal[
            "enhancement","morale","luck","insight","competence","sacred","profane",
            "resistance","deflection","dodge","size","natural_armor","natural_armor_enhancement",
            "circumstance","alchemical","untyped","defaultTyped"
        ],
        Literal["stack","no_stack_highest"]
    ]] = None

    # 5) Tie-breaker (when magnitudes equal or magnitudeExpr missing)
    tieBreaker: Optional[Literal["latest", "highestCL", "highestLevel", "sourcePriority"]] = None

    @model_validator(mode="after")
    def _validate(self):
        errs: list[str] = []
        if self.familyPolicy and not self.familyKeys:
            errs.append("familyPolicy requires non-empty familyKeys")
        if self.named in ("no_stack_highest",) and not (self.magnitudeExpr or self.tieBreaker):
            # Not strictly required, but warn authors toward deterministic behavior
            pass
        if "dodge" in (self.bonusTypePolicy or {}) and self.bonusTypePolicy["dodge"] != "stack":
            errs.append("bonusTypePolicy for 'dodge' must be 'stack' (RAW)")
        # If defaultTyped omitted, engine will use canonical default (no_stack_highest)
        if errs:
            raise ValueError("; ".join(errs))
        return self

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
    stacking: Optional[StackingPolicy] = None
    notes: Optional[str] = None

    activation: Optional[ActivationSpec] = None
    range: Optional[RangeSpec] = None
    targetFilter: Optional[TargetFilter] = None
    area: Optional[AreaSpec] = None

    when: Optional[str] = None   # "on activation" | "continuous" | "on trigger"
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

    @model_validator(mode="after")
    def _validate_effect(self):
        errs: list[str] = []

        # 1) Duration rules accurate to RAW
        has_instancey_bits = bool(self.modifiers or self.ruleHooks or self.operations)

        is_passive = (
            (self.activation and self.activation.action == "passive")
            or (self.when is not None and self.when.lower().startswith("continuous"))
        )

        if self.abilityType in ("Spell", "Sp"):
            # All spells/SLAs must declare a duration (even instantaneous)
            if self.duration is None:
                errs.append("Spell/Sp requires duration (use {type:'instantaneous'} if appropriate)")
            else:
                if self.duration.type == "concentration":
                    if not (self.activation and self.activation.concentration):
                        errs.append("duration.type 'concentration' requires activation.concentration=true for Spell/Sp")
        else:
            # Non-spell effects
            if is_passive:
                # Continuous passives may omit duration; recommended to use duration: permanent for clarity.
                pass
            else:
                # Activated or triggered non-spell effects that attach anything should either:
                # - declare duration (including 'instantaneous'), OR
                # - mark when:'continuous'
                if has_instancey_bits and self.duration is None and not self.when:
                    errs.append("Activated/triggered non-spell effect with modifiers/hooks/ops must declare duration "
                                "(including 'instantaneous') or set when:'continuous'")

        # 2) SR consistency: only Spell/Sp can have SR gate applying
        if self.gates and self.gates.sr and self.gates.sr.applies:
            if self.abilityType not in ("Spell", "Sp"):
                errs.append("gates.sr.applies=true is invalid unless abilityType is Spell or Sp")

        if errs:
            raise ValueError("; ".join(errs))
        return self

# ConditionDefinition
class ConditionDefinition(BaseModel):
    id: str
    name: str
    # Only canonical tags allowed; optional but constrained
    tags: List[ConditionTag] = Field(default_factory=list)
    # Higher number = higher precedence (engine will document the ordering policy)
    precedence: Optional[int] = None

    # Optional default duration; used when an effect applies the condition with no explicit duration
    default_duration: Optional["DurationSpec"] = None

    modifiers: List["Modifier"] = Field(default_factory=list)
    ruleHooks: List["RuleHook"] = Field(default_factory=list)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate_default_duration(self):
        dd = self.default_duration
        if dd is None:
            return self
        # Disallow concentration for conditions’ defaults (it’s a property of effects, not conditions)
        if dd.type == "concentration":
            raise ValueError("Condition default_duration cannot be 'concentration'; model concentration on the applying effect")

        # Instantaneous: no explicit duration value/formula required (and should not be provided)
        if dd.type == "instantaneous":
            if dd.value is not None or dd.formula is not None:
                raise ValueError("default_duration 'instantaneous' must not specify value or formula")
            return self

        # Permanent: no numeric duration
        if dd.type == "permanent":
            if dd.value is not None or dd.formula is not None:
                raise ValueError("default_duration 'permanent' must not specify value or formula")
            return self

        # Timed durations: require either a value (>0) or a formula
        if dd.type in ("rounds", "minutes", "hours", "days"):
            if dd.value is None and dd.formula is None:
                raise ValueError(f"default_duration '{dd.type}' requires value or formula")
            if dd.value is not None and dd.value <= 0:
                raise ValueError(f"default_duration '{dd.type}' value must be > 0 when provided")
            return self

        # 'special' is allowed, but strongly prefer effects to manage special end conditions
        # (No extra checks here; leave to runtime/authoring guidelines)
        return self

# ResourceDefinition
# Absorbable packet types (align with your damage kinds, add aggregate "physical")
AbsorbType = Literal[
    "any",
    "physical",
    "physical.bludgeoning", "physical.piercing", "physical.slashing",
    "acid", "cold", "electricity", "fire", "sonic", "force",
    "negative", "positive", "nonlethal", "bleed", "typeless"
]

class CapacitySpec(BaseModel):
    formula: Expr  # REQUIRED
    cap: Optional[int] = None
    computeAt: Optional[ComputeAt] = "attach"

    @model_validator(mode="after")
    def _validate(self):
        # formula presence implicitly enforced by type; ensure cap non-negative
        if self.cap is not None and self.cap < 0:
            raise ValueError("capacity.cap must be >= 0")
        return self

class ResourceRefresh(BaseModel):
    cadence: Cadence
    behavior: Literal["reset_to_max", "increment_by", "no_change"] = "reset_to_max"
    increment_by: Optional[Expr] = None
    triggers: Optional[List[str]] = None

    @model_validator(mode="after")
    def _validate(self):
        if self.behavior == "increment_by" and self.increment_by is None:
            raise ValueError("refresh.behavior 'increment_by' requires increment_by")
        return self

# Absorption policy for ablative pools
class AbsorptionSpec(BaseModel):
    absorbTypes: List[AbsorbType] = Field(default_factory=list)
    absorbPerHit: Optional[int] = None         # max absorbed per attack/hit
    absorbOrder: Optional[Literal[
        # Engine default is resist -> DR -> pool; use one of these to override:
        "before_resist",               # apply pool before resist/DR
        "after_resist_before_dr",      # after resist, before DR
        "after_dr",                    # after DR (default if overriding)
        "final"                        # last step (after everything else)
    ]] = None

    @model_validator(mode="after")
    def _validate(self):
        if not self.absorbTypes:
            raise ValueError("absorption.absorbTypes must be a non-empty list")
        if self.absorbPerHit is not None and self.absorbPerHit < 0:
            raise ValueError("absorption.absorbPerHit must be >= 0")
        # Normalize: if 'any' present, it must be the only entry
        if "any" in self.absorbTypes and len(self.absorbTypes) > 1:
            raise ValueError("absorption.absorbTypes: 'any' must not be combined with other types")
        # If 'physical' present, don't combine with specific physical.*
        if "physical" in self.absorbTypes:
            if any(t.startswith("physical.") for t in self.absorbTypes if t != "physical"):
                raise ValueError("absorption.absorbTypes: 'physical' must not be combined with specific physical.* kinds")
        return self

class ResourceDefinition(BaseModel):
    id: str
    name: Optional[str] = None
    scope: ScopeType = "entity"                # enforced by enum
    capacity: CapacitySpec                     # REQUIRED
    initial_current: Optional[Expr] = None
    refresh: Optional[ResourceRefresh] = None
    expiry: Optional[Dict[str, Union[str, int]]] = None
    absorption: Optional[AbsorptionSpec] = None
    visibility: Optional[Visibility] = "public"
    stacking: Optional[Dict[str, Union[str, int]]] = None
    recomputeOn: Optional[List[str]] = None
    freezeOnAttach: Optional[bool] = None      # will enforce boolean

    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate(self):
        # freezeOnAttach must be boolean if provided (pydantic type already enforces)
        # Optional: default to False if omitted (engine-level default)
        return self


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
ConditionDefinition.model_rebuild()
ResourceDefinition.model_rebuild()
ResourceRefresh.model_rebuild()
AbsorptionSpec.model_rebuild()
CapacitySpec.model_rebuild()
