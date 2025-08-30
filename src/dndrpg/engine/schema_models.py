from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, AliasChoices

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

# Operations (generic; keep open-ended)
class Operation(BaseModel):
    op: str
    params: Dict[str, Any] = Field(default_factory=dict)

# Rule Hooks (generic: match + actions)
HookScope = Literal["targeting", "incoming.effect", "incoming.condition", "incoming.damage",
                    "on.save", "on.attack", "on.damageDealt", "on.damageTaken", "on.crit",
                    "on.maneuverGrant", "scheduler", "suppression", "resource"]

class RuleHook(BaseModel):
    scope: HookScope
    match: Dict[str, Any] = Field(default_factory=dict)
    action: List[Dict[str, Any]] = Field(default_factory=list)
    priority: Optional[int] = None
    duration: Optional[Dict[str, Any]] = None

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
    dcExpression: str = Field(validation_alias=AliasChoices("dc", "dcExpression"))
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