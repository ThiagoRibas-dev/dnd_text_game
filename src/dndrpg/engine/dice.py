from __future__ import annotations
import random

def d20(rng: random.Random) -> int:
    return rng.randint(1, 20)

def d100(rng: random.Random) -> int:
    return rng.randint(1, 100)