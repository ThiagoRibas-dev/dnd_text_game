from __future__ import annotations
import random
from typing import Dict, List

STANDARD_ARRAYS = {
    "classic": [15,14,13,12,10,8],
    "balanced": [16,14,13,12,10,8],
}

def roll_4d6_drop_lowest(rng: random.Random) -> int:
    rolls = sorted([rng.randint(1,6) for _ in range(4)], reverse=True)
    return sum(rolls[:3])

def generate_4d6(rng: random.Random, reroll_ones: bool=False) -> List[int]:
    scores = []
    for _ in range(6):
        if reroll_ones:
            # reroll any '1' in each die
            rolls = []
            for _ in range(4):
                r = rng.randint(1,6)
                while r == 1:
                    r = rng.randint(1,6)
                rolls.append(r)
            rolls.sort(reverse=True)
            scores.append(sum(rolls[:3]))
        else:
            scores.append(roll_4d6_drop_lowest(rng))
    return sorted(scores, reverse=True)

def assign_scores_to_abilities(scores: List[int], order: List[str]) -> Dict[str, int]:
    # order is a list like ["str","dex","con","int","wis","cha"] chosen by the user
    return {ab: scores[i] for i, ab in enumerate(order)}
