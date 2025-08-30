import random
from typing import Tuple

from .state import GameState

def roll_dice(num_dice: int, die_type: int, game_state: GameState) -> Tuple[int, list[int]]:
    """Rolls a specified number of dice of a given type and returns the total and individual rolls.

    Args:
        num_dice: The number of dice to roll.
        die_type: The type of die to roll (e.g., 4 for d4, 6 for d6, 20 for d20).
        game_state: The current GameState object, used to manage the RNG state.

    Returns:
        A tuple containing the total result of the roll and a list of individual roll results.
    """
    game_state.initialize_rng()
    rolls = [random.randint(1, die_type) for _ in range(num_dice)]
    total = sum(rolls)
    game_state.update_rng_state()
    return total, rolls
