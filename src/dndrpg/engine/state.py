import random
from pydantic import BaseModel, Field
from .models import Entity, Abilities, AbilityScore, Size, Item
from .loader import ContentIndex

class GameState(BaseModel):
    player: Entity
    log: list[str] = Field(default_factory=list)
    seed: int = Field(default_factory=lambda: random.randint(0, 2**32 - 1))
    rng_state: tuple = Field(default_factory=lambda: random.getstate())

    def resources_summary(self) -> dict[str, int]:
        return {"Spell Slots (1st)": 2, "Turn Attempts": 3}

    def initialize_rng(self):
        random.setstate(self.rng_state)

    def update_rng_state(self):
        self.rng_state = random.getstate()


def default_cleric_lvl1(content: ContentIndex) -> Entity:
    abilities = Abilities(
        str_=AbilityScore(base=14), dex=AbilityScore(base=12), con=AbilityScore(base=12),
        int_=AbilityScore(base=10), wis=AbilityScore(base=14), cha=AbilityScore(base=10),
    )
    # Clone items from content
    mace = content.clone_item("wp.mace.heavy")
    chain_shirt = content.clone_item("ar.chain_shirt")
    heavy_wooden_shield = content.clone_item("sh.heavy_wooden")
    holy_symbol = content.clone_item("it.holy_symbol")
    rations = content.clone_item("it.rations.5")

    inv: list[Item] = [mace, chain_shirt, heavy_wooden_shield, holy_symbol, rations]

    ent = Entity(
        id="pc.aria", name="Aria (Human Cleric 1)", level=1, size=Size.MEDIUM, abilities=abilities,
        base_attack_bonus=0, base_fort=2, base_ref=0, base_will=2,
        hp_max=9, hp_current=9, speed_land=30, inventory=inv,
        equipment={"armor": chain_shirt.id, "shield": heavy_wooden_shield.id, "main_hand": mace.id},
        classes={"cleric": 1},
        caster_levels={"cleric": 1},
        hd=1
    )
    return ent

def default_state(content: ContentIndex) -> GameState:
    game_state = GameState(player=default_cleric_lvl1(content))
    random.seed(game_state.seed)
    game_state.update_rng_state()
    return game_state
