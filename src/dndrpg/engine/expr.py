# Wrapper you can extend with custom funcs like ability_mod()
from py_expression_eval import Parser
import math

def ability_mod(score: int) -> int:
    return (score - 10) // 2

def level(entity) -> int:
    return entity.level

def class_level(entity, cls_name: str) -> int:
    # Assuming entity.classes is a dict like {'fighter': 5, 'wizard': 3}
    return entity.classes.get(cls_name, 0)

def caster_level(entity, spell_type: str) -> int:
    # Placeholder: actual CL calculation is complex and depends on class, feats, etc.
    # For now, return entity level or class level if specific spell_type is known.
    if spell_type == "divine":
        return entity.level # Simplified
    if spell_type == "arcane":
        return entity.level # Simplified
    return entity.level # Default to total level

def initiator_level(entity) -> int:
    # Placeholder: actual IL calculation is complex
    return entity.level # Simplified

def hd(entity) -> int:
    # Placeholder: actual HD calculation is complex
    return entity.level # Simplified

_parser = Parser({
    "ability_mod": ability_mod,
    "level": level,
    "class_level": class_level,
    "caster_level": caster_level,
    "initiator_level": initiator_level,
    "hd": hd,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
})

def eval_expr(expr: str, env: dict) -> int | float:
    return _parser.parse(expr).evaluate(env)
