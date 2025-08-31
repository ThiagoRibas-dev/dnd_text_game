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
    # ——— Core helpers ———
    _parser.functions["min"] = min
    _parser.functions["max"]

    # Ensure floor/ceil are present (py-expression-eval has them, but be explicit)
    import math
    _parser.functions.update({"floor": math.floor, "ceil": math.ceil})

    # ——— D&D values (pre-evaluated for convenience) ———
    if actor:
        context["level"] = int(getattr(actor, "level", 0) or 0)
        context["hd"] = int(getattr(actor, "hd", None) or getattr(actor, "level", 0) or 0)
        # Add ability scores as variables (e.g., str, dex, con)
        for ab_name_key, _ in actor.abilities.model_fields.items():
            ab_score = getattr(actor.abilities, ab_name_key)
            ab_name = ab_name_key.replace("_", "") # remove trailing underscore from str_ and int_
            context[ab_name] = ab_score.score()
            context[f"{ab_name}_mod"] = ab_score.mod()
        # Add class levels as variables (e.g., fighter_level, cleric_level)
        for cls_name, cls_level in actor.classes.items():
            context[f"{cls_name.lower()}_level"] = cls_level
        # Add caster levels
        if actor.caster_levels:
            for cl_name, cl_val in actor.caster_levels.items():
                context[f"{cl_name.lower()}_cl"] = cl_val
            context["caster_level"] = int(max(actor.caster_levels.values()))
        else:
            context["caster_level"] = context["level"] # fallback
        # Initiator level
        il_override = context.get("initiator_level_override")
        if isinstance(il_override, int):
            context["initiator_level"] = il_override
        elif actor.classes:
            adepts = {"crusader", "warblade", "swordsage"}
            adept_levels = sum(v for k, v in actor.classes.items() if k in adepts)
            non_adept_levels = sum(v for k, v in actor.classes.items() if k not in adepts)
            context["initiator_level"] = int(adept_levels + (non_adept_levels // 2))
        else:
            context["initiator_level"] = context["level"]

    if target:
        context["target_level"] = int(getattr(target, "level", 0) or 0)
        context["target_hd"] = int(getattr(target, "hd", None) or getattr(target, "level", 0) or 0)
        for ab_name_key, _ in target.abilities.model_fields.items():
            ab_score = getattr(target.abilities, ab_name_key)
            ab_name = ab_name_key.replace("_", "") # remove trailing underscore from str_ and int_
            context[f"target_{ab_name}"] = ab_score.score()
            context[f"target_{ab_name}_mod"] = ab_score.mod()
        for cls_name, cls_level in target.classes.items():
            context[f"target_{cls_name.lower()}_level"] = cls_level
        if target.caster_levels:
            for cl_name, cl_val in target.caster_levels.items():
                context[f"target_{cl_name.lower()}_cl"] = cl_val
            context["target_caster_level"] = int(max(target.caster_levels.values()))
        else:
            context["target_caster_level"] = context["target_level"]
        il_override = context.get("target_initiator_level_override")
        if isinstance(il_override, int):
            context["target_initiator_level"] = il_override
        elif target.classes:
            adepts = {"crusader", "warblade", "swordsage"}
            adept_levels = sum(v for k, v in target.classes.items() if k in adepts)
            non_adept_levels = sum(v for k, v in target.classes.items() if k not in adepts)
            context["target_initiator_level"] = int(adept_levels + (non_adept_levels // 2))
        else:
            context["target_initiator_level"] = context["target_level"]

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