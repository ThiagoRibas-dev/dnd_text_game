import random

CLASS_WEALTH_DICE = {
    "fighter": (6, 4),   # 6d4 × 10 gp
    "cleric":  (5, 4),
    "sorcerer":(3, 4),
    "monk":    (5, 4),   # (monk uses gp differently; keep simple)
}

def roll_class_gold(clazz: str, rng: random.Random) -> int:
    n, die = CLASS_WEALTH_DICE.get(clazz, (3, 4))
    return sum(rng.randint(1, die) for _ in range(n)) * 10
