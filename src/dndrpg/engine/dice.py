from __future__ import annotations
import random

def d20(rng: random.Random) -> int:
    return rng.randint(1, 20)

def d100(rng: random.Random) -> int:
    return rng.randint(1, 100)

def roll_dice_str(rng: random.Random, s: str) -> int:  # e.g., "1d8+2"
    import re
    m = re.fullmatch(r"\s*(\d+)d(\d+)([+-]\d+)?\s*", s)
    if not m:
        return 0
    n, d = int(m.group(1)), int(m.group(2))
    bonus = int(m.group(3) or 0)
    return sum(rng.randint(1, d) for _ in range(n)) + bonus
