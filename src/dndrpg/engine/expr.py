from __future__ import annotations
from typing import Any, Optional, Dict
from functools import lru_cache
import threading
import math # Moved to top

from py_expression_eval import Parser
from .models import Entity

# Thread-local evaluation context so function implementations can read actor/target dynamically
class _EvalTLS(threading.local):
    def __init__(self):
        self.actor: Optional[Entity] = None
        self.target: Optional[Entity] = None
        self.extra: Dict[str, Any] = {}

_TLS = _EvalTLS()

# Single global parser with function table bound to dynamic, context-aware implementations
_parser = Parser()

def _get_actor() -> Optional[Entity]:
    return _TLS.actor
def _get_target() -> Optional[Entity]:
    return _TLS.target
def _get_extra() -> Dict[str, Any]:
    return _TLS.extra

# Allowed math helpers
_parser.functions["min"] = min
_parser.functions["max"] = max
_parser.functions["floor"] = math.floor
_parser.functions["ceil"] = math.ceil

# D&D functions (look up actor/target each call from thread-local)
def _ability_name(name: Any) -> str:
    s = str(name).lower()
    aliases = {"strength": "str", "dexterity": "dex", "constitution": "con",
               "intelligence": "int", "wisdom": "wis", "charisma": "cha"}
    return aliases.get(s, s)

def _ability_mod(name: Any, who: str = "actor") -> int:
    ent = _get_actor() if who == "actor" else _get_target()
    if not isinstance(ent, Entity):
        return 0
    ab = _ability_name(name)
    return ent.abilities.get(ab).mod()

def _level(who: str = "actor") -> int:
    ent = _get_actor() if who == "actor" else _get_target()
    if not isinstance(ent, Entity):
        return 0
    return int(getattr(ent, "level", 0) or 0)

def _class_level(cls_name: Any, who: str = "actor") -> int:
    ent = _get_actor() if who == "actor" else _get_target()
    if not isinstance(ent, Entity):
        return 0
    return int(ent.classes.get(str(cls_name).lower(), 0))

def _caster_level(key: Any | None = None, who: str = "actor") -> int:
    ent = _get_actor() if who == "actor" else _get_target()
    if not isinstance(ent, Entity):
        return 0
    if key is None:
        return max(ent.caster_levels.values()) if ent.caster_levels else int(getattr(ent, "level", 0) or 0)
    return int(ent.caster_levels.get(str(key).lower(), 0))

def _initiator_level(who: str = "actor") -> int:
    ent = _get_actor() if who == "actor" else _get_target()
    if not isinstance(ent, Entity):
        return 0
    # Optional override in extra
    il_override = _get_extra().get("initiator_level_override")
    if isinstance(il_override, int):
        return il_override
    if ent.classes:
        adepts = {"crusader", "warblade", "swordsage"}
        adept_levels = sum(v for k, v in ent.classes.items() if k in adepts)
        non_adept_levels = sum(v for k, v in ent.classes.items() if k not in adepts)
        return int(adept_levels + (non_adept_levels // 2))
    return int(getattr(ent, "level", 0) or 0)

def _hd(who: str = "actor") -> int:
    ent = _get_actor() if who == "actor" else _get_target()
    if not isinstance(ent, Entity):
        return 0
    return int(getattr(ent, "hd", None) or getattr(ent, "level", 0) or 0)

# Register dynamic functions
_parser.functions["ability_mod"] = _ability_mod
_parser.functions["level"] = _level
_parser.functions["class_level"] = _class_level
_parser.functions["caster_level"] = _caster_level
_parser.functions["initiator_level"] = _initiator_level
_parser.functions["hd"] = _hd

# LRU-compiled AST cache
@lru_cache(maxsize=8192)
def _compile_expr(expr: str):
    # Parse once; compiled expression captures function names (dispatched to _parser.functions)
    return _parser.parse(expr)

def eval_expr(expr: str | int | float,
              actor: Optional[Entity] = None,
              target: Optional[Entity] = None,
              extra: Optional[Dict[str, Any]] = None) -> int | float:
    """
    Evaluate an expression string (or numeric literal) using the compiled cache and thread-local context.
    """
    if isinstance(expr, (int, float)):
        return expr
    # Set thread-local context for dynamic functions
    prev_actor, prev_target, prev_extra = _TLS.actor, _TLS.target, _TLS.extra
    _TLS.actor, _TLS.target, _TLS.extra = actor, target, (extra or {})
    try:
        ast = _compile_expr(expr)
        value = ast.evaluate(_TLS.extra)  # constants/vars available via extra
    finally:
        _TLS.actor, _TLS.target, _TLS.extra = prev_actor, prev_target, prev_extra

    # Normalize ints
    try:
        f = float(value)
        return int(f) if f.is_integer() else f
    except Exception:
        return value

# Backward-compat wrappers (used across engine)
def eval_for_actor(expr: str | int | float, actor: Entity, extra: Optional[Dict[str, Any]] = None):
    return eval_expr(expr, actor=actor, target=None, extra=extra)

def eval_for_actor_vs_target(expr: str | int | float, actor: Entity, target: Entity, extra: Optional[Dict[str, Any]] = None):
    return eval_expr(expr, actor=actor, target=target, extra=extra)

# Optional: quick stats
def expr_cache_info() -> str:
    info = _compile_expr.cache_info()
    return f"expr-cache: hits={info.hits}, misses={info.misses}, size={info.currsize}/{info.maxsize}"