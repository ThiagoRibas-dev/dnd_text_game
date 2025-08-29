from pydantic import BaseModel, Field

class Entity(BaseModel):
    name: str
    level: int = 1
    hp_max: int = 10
    hp_current: int = 10
    ac_total: int = 15
    ac_touch: int = 12
    ac_ff: int = 13
    initiative_bonus: int = 2
    attack_melee_bonus: int = 3
    attack_ranged_bonus: int = 2
    save_fort: int = 2
    save_ref: int = 2
    save_will: int = 2
    inventory: list[str] = Field(default_factory=list)
    tags: set[str] = Field(default_factory=set)

class GameState(BaseModel):
    player: Entity
    log: list[str] = Field(default_factory=list)

    def resources_summary(self) -> dict[str, int]:
        return {"Spell Slots (1st)": 2, "Turn Attempts": 3}

def default_state() -> GameState:
    player = Entity(
        name="Aria (Human Cleric 1)",
        level=1,
        hp_max=10,
        hp_current=10,
        ac_total=16, ac_touch=12, ac_ff=14,
        initiative_bonus=1, attack_melee_bonus=2, attack_ranged_bonus=1,
        save_fort=4, save_ref=0, save_will=2,
        inventory=["Mace", "Chain Shirt", "Holy Symbol", "Rations x5"]
    )
    return GameState(player=player)