CLASS_SKILLS = {
    "fighter": {"climb","craft","handle_animal","intimidate","jump","ride","swim"},
    "cleric": {"concentration","craft","diplomacy","heal","knowledge","profession","spellcraft"},
    "sorcerer":{"bluff","concentration","craft","profession","knowledge","spellcraft"},
    "monk": {"balance","climb","concentration","craft","diplomacy","escape_artist","hide","jump","knowledge","listen","move_silently","perform","profession","sense_motive","spot","swim","tumble"},
}
def max_ranks(level: int, class_skill: bool) -> int:
    return (level + 3) if class_skill else ((level + 3)//2)

def skill_points_at_level1(clazz: str, int_mod: int, human: bool) -> int:
    base = {"fighter":2,"cleric":2,"sorcerer":2,"monk":4}.get(clazz, 2)
    per_level = max(1, base + int_mod)
    total = per_level * 4
    if human:
        total += 4
    return total
