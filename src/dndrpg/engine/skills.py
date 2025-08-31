CLASS_SKILLS = {
    "fighter": {"Climb","Craft","Handle Animal","Intimidate","Jump","Ride","Swim"},
    "cleric": {"Concentration","Craft","Diplomacy","Heal","Knowledge (arcana)","Knowledge (history)","Knowledge (religion)","Knowledge (the planes)","Profession","Spellcraft"},
    "sorcerer":{"Bluff","Concentration","Craft","Profession","Knowledge (arcana)","Spellcraft"},
    "monk": {"Balance","Climb","Concentration","Craft","Diplomacy","Escape Artist","Hide","Jump","Knowledge (arcana)","Knowledge (religion)","Listen","Move Silently","Perform","Profession","Sense Motive","Spot","Swim","Tumble"},
}
def max_ranks(level: int, class_skill: bool) -> int:
    return (level + 3) if class_skill else ((level + 3)//2)
def skill_points_at_level1(clazz: str, int_mod: int, human: bool) -> int:
    base = {"fighter":2,"cleric":2,"sorcerer":2,"monk":4}.get(clazz, 2)
    total = (base + max(1, int_mod)) * 4
    if human:
        total += 4
    return total
