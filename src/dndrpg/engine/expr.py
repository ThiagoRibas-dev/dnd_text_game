from __future__ import annotations
from typing import Any, Optional
from py_expression_eval import Parser
from .models import Entity

_parser = Parser()

def _ability_name(arg: Any) -> str:
    # Accept "str", 'STR', str without quotes, etc.
    if isinstance(arg, str):
        s = arg.lower()
    else:
        s = str(arg).lower()
    aliases = {"strength": "str", "dexterity": "dex", "constitution": "con",
               "intelligence": "int", "wisdom": "wis", "charisma": "cha"}
    return aliases.get(s, s)

def _register_functions(context: dict[str, Any]) -> None:
    """
    Register or overwrite functions on the global parser for this evaluation.
    This mutates the parser's function table (OK for single-threaded CLI/TUI).
    """

    actor: Optional[Entity] = context.get("actor")  # optional
    target: Optional[Entity] = context.get("target")

    # ——— Core helpers ———
    _parser.functions["min"] = min
    _parser.functions["max"] = max

    # Ensure floor/ceil are present (py-expression-eval has them, but be explicit)
    import math
    _parser.functions.update({"floor": math.floor, "ceil": math.ceil})

    # ——— D&D functions ———

    def ability_mod_func(name: Any, who: str = "actor") -> int:
        ent = actor if who == "actor" else target
        if not isinstance(ent, Entity):
            return 0
        ab = _ability_name(name)
        sc = ent.abilities.get(ab).mod()
        return sc

    def level_func(who: str = "actor") -> int:
        ent = actor if who == "actor" else target
        return int(getattr(ent, "level", 0) or 0) if isinstance(ent, Entity) else 0

    def class_level_func(cls_name: Any, who: str = "actor") -> int:
        ent = actor if who == "actor" else target
        if not isinstance(ent, Entity):
            return 0
        key = str(cls_name).lower()
        return int(ent.classes.get(key, 0))

    def caster_level_func(key: Any | None = None, who: str = "actor") -> int:
        """
        caster_level() with no key returns a generic CL:
          - If caster_levels map exists and non-empty: highest CL in map
          - Else fallback to level
        caster_level("cleric") returns the class-specific CL if present, else 0
        """
        ent = actor if who == "actor" else target
        if not isinstance(ent, Entity):
            return 0
        if key is None:
            if ent.caster_levels:
                return int(max(ent.caster_levels.values()))
            return int(getattr(ent, "level", 0) or 0)
        k = str(key).lower()
        return int(ent.caster_levels.get(k, 0))

    def initiator_level_func(who: str = "actor") -> int:
        """
        Minimal IL approximation:
          - If the entity has 'initiator_level' attribute in extra context, return it
          - Else if classes exist: IL = sum(adept classes) + floor(sum(other classes) / 2)
          - Else fallback to level
        Adept classes: crusader, warblade, swordsage
        """
        ent = actor if who == "actor" else target
        if not isinstance(ent, Entity):
            return 0
        # If context provided an explicit IL, prefer it
        il_override = context.get("initiator_level_override")
        if isinstance(il_override, int):
            return il_override
        if ent.classes:
            adepts = {"crusader", "warblade", "swordsage"}
            adept_levels = sum(v for k, v in ent.classes.items() if k in adepts)
            non_adept_levels = sum(v for k, v in ent.classes.items() if k not in adepts)
            return int(adept_levels + (non_adept_levels // 2))
        return int(getattr(ent, "level", 0) or 0)

    def hd_func(who: str = "actor") -> int:
        ent = actor if who == "actor" else target
        if not isinstance(ent, Entity):
            return 0
        # If entity has explicit hd, use it, else fallback to level
        return int(getattr(ent, "hd", None) or getattr(ent, "level", 0) or 0)

    _parser.functions.update({
        "ability_mod": ability_mod_func,
        "level": level_func,
        "class_level": class_level_func,
        "caster_level": caster_level_func,
        "initiator_level": initiator_level_func,
        "hd": hd_func
    })

def make_env(actor: Optional[Entity] = None,
             target: Optional[Entity] = None,
             extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Build an evaluation environment. Numbers and constants can be added via 'extra'.
    Example:
      env = make_env(actor=pc, extra={"spell_level": 4})
      eval_expr("10 + spell_level + ability_mod('wis')", env)
    """
    env: dict[str, Any] = {}
    if extra:
        env.update(extra)
    if actor:
        env["actor"] = actor
    if target:
        env["target"] = target
    return env

def eval_expr(expr: str, env: dict[str, Any] | None = None) -> int | float:
    """
    Evaluate an expression with the registered functions and variables in env.
    Returns int when result is an integer value, else float.
    """
    env = env or {}
    _register_functions(env)
    value = _parser.parse(expr).evaluate(env)

    # Normalize ints (avoid 5.0)
    try:
        if float(value).is_integer():
            return int(value)
    except Exception:
        pass
    return value

# Convenience aliases commonly used in content
def eval_for_actor(expr: str, actor: Entity, extra: Optional[dict[str, Any]] = None) -> int | float:
    return eval_expr(expr, make_env(actor=actor, extra=extra or {}))

def eval_for_actor_vs_target(expr: str, actor: Entity, target: Entity, extra: Optional[dict[str, Any]] = None) -> int | float:
    return eval_expr(expr, make_env(actor=actor, target=target, extra=extra or {}))