from __future__ import annotations
from typing import Dict

CLERIC_SPELLS_PER_DAY = {
    # level: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    1: [3, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    # ... add more levels as needed
}

def bonus_slots_from_mod(mod: int, max_level: int = 1) -> Dict[int, int]:
    # RAW table simplified for levels 0–1 (0 has no bonus; 1 has +1 at Wis/Cha 12+)
    bonus = {0: 0, 1: 0}
    if mod >= 1:
        bonus[1] = 1
    return bonus

def sorcerer_spells_known_from_cha(level: int, cha_mod: int) -> Dict[int, int]:
    # Simplified Sorcerer Spells Known (D&D 3.5e PHB p. 177)
    # This is a basic approximation for level 1
    # Actual rules are more complex, involving class level and CHA modifier
    spells_known = {0: 4, 1: 2} # Base for level 1 Sorcerer

    # Bonus spells known from high CHA (only for spell levels they can cast)
    # For level 1, only 1st level spells get bonus from CHA
    if cha_mod >= 1:
        spells_known[1] += 1 # +1 for 1st level spells if CHA mod >= 1

    return spells_known
