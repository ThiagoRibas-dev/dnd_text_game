from __future__ import annotations
from typing import Optional, Literal, List, Dict, Set
from enum import Enum
from pydantic import BaseModel, Field, computed_field

class Size(str, Enum):
    FINE = "Fine"
    DIMINUTIVE = "Diminutive"
    TINY = "Tiny"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    HUGE = "Huge"
    GARGANTUAN = "Gargantuan"
    COLOSSAL = "Colossal"

SIZE_TO_MOD = {
    Size.FINE:+8, Size.DIMINUTIVE:+4, Size.TINY:+2, Size.SMALL:+1, Size.MEDIUM:0,
    Size.LARGE:-1, Size.HUGE:-2, Size.GARGANTUAN:-4, Size.COLOSSAL:-8,
}

class WeaponCategory(str, Enum):
    SIMPLE="simple"
    MARTIAL="martial"
    EXOTIC="exotic"
class WeaponKind(str, Enum):
    MELEE="melee"
    RANGED="ranged"
    THROWN="thrown"
class Handedness(str, Enum):
    LIGHT="light"
    ONE_HANDED="one-handed"
    TWO_HANDED="two-handed"
DamageType = Literal["bludgeoning","piercing","slashing"]

class Item(BaseModel):
    id: str
    name: str
    type: Literal["item"] = "item"
    weight_lb: float = 0.0
    cost_gp: float = 0.0
    tags: Set[str] = Field(default_factory=set)

class Weapon(Item):
    type: Literal["weapon"] = "weapon"
    category: WeaponCategory = WeaponCategory.SIMPLE
    kind: WeaponKind = WeaponKind.MELEE
    handed: Handedness = Handedness.ONE_HANDED
    damage_dice_m: str = "1d6"
    crit_range: int = 20
    crit_mult: int = 2
    damage_types: List[DamageType] = Field(default_factory=list)
    range_increment_ft: Optional[int] = None
    enhancement_bonus: int = 0
    counts_as_material: Set[str] = Field(default_factory=set)
    counts_as_alignment: Set[str] = Field(default_factory=set)

    @computed_field
    @property
    def counts_as_magic(self) -> bool:
        return self.enhancement_bonus > 0 or ("magic" in self.tags)

class Armor(Item):
    type: Literal["armor"] = "armor"
    armor_type: Literal["light","medium","heavy"] = "light"
    armor_bonus: int = 0
    max_dex_bonus: Optional[int] = None
    armor_check_penalty: int = 0
    arcane_spell_failure_pct: int = 0
    enhancement_bonus: int = 0
    speed30_in_armor: Optional[int] = None
    speed20_in_armor: Optional[int] = None

    @computed_field
    @property
    def effective_armor_bonus(self) -> int:
        return self.armor_bonus + self.enhancement_bonus

class Shield(Item):
    type: Literal["shield"] = "shield"
    shield_bonus: int = 0
    armor_check_penalty: int = 0
    arcane_spell_failure_pct: int = 0
    enhancement_bonus: int = 0
    is_tower: bool = False

    @computed_field
    @property
    def effective_shield_bonus(self) -> int:
        return self.shield_bonus + self.enhancement_bonus

class AbilityScore(BaseModel):
    base: int = 10
    temp: int = 0
    damage: int = 0
    drain: int = 0
    def score(self) -> int: return max(0, self.base + self.temp - self.damage - self.drain)
    def mod(self) -> int: return (self.score() - 10) // 2

class Abilities(BaseModel):
    str_: AbilityScore = Field(default_factory=AbilityScore)
    dex: AbilityScore = Field(default_factory=AbilityScore)
    con: AbilityScore = Field(default_factory=AbilityScore)
    int_: AbilityScore = Field(default_factory=AbilityScore)
    wis: AbilityScore = Field(default_factory=AbilityScore)
    cha: AbilityScore = Field(default_factory=AbilityScore)
    def get(self, name: str) -> AbilityScore:
        key = "str_" if name == "str" else ("int_" if name == "int" else name)
        return getattr(self, key)

class Entity(BaseModel):
    id: str
    name: str
    level: int = 1
    size: Size = Size.MEDIUM
    abilities: Abilities = Field(default_factory=Abilities)
    hp_max: int = 8
    hp_current: int = 8
    nonlethal_damage: int = 0
    base_attack_bonus: int = 0
    bab_misc: int = 0
    base_fort: int = 0
    base_ref: int = 0
    base_will: int = 0
    save_misc_fort: int = 0
    save_misc_ref: int = 0
    save_misc_will: int = 0
    natural_armor: int = 0
    deflection_bonus: int = 0
    dodge_bonus: int = 0
    ac_misc: int = 0
    init_misc: int = 0
    speed_land: int = 30
    inventory: List[Item] = Field(default_factory=list)
    equipment: Dict[str, str] = Field(default_factory=dict)  # "armor","shield","main_hand","off_hand","ranged"
    classes: Dict[str, int] = Field(default_factory=dict)         # e.g., {"cleric": 1}
    caster_levels: Dict[str, int] = Field(default_factory=dict)    # e.g., {"cleric": 1}
    hd: Optional[int] = None  # total HD; if None, expressions use level

    def get_equipped(self, slot: str) -> Optional[Item]:
        iid = self.equipment.get(slot)
        if not iid:
            return None
        for it in self.inventory:
            if it.id == iid:
                return it
        return None

    def equipped_armor(self) -> Optional[Armor]:
        it = self.get_equipped("armor")
        return it if isinstance(it, Armor) else None

    def equipped_shield(self) -> Optional[Shield]:
        it = self.get_equipped("shield")
        return it if isinstance(it, Shield) else None

    def equipped_main_weapon(self) -> Optional[Weapon]:
        it = self.get_equipped("main_hand")
        return it if isinstance(it, Weapon) else None

    def equipped_ranged_weapon(self) -> Optional[Weapon]:
        it = self.get_equipped("ranged")
        return it if isinstance(it, Weapon) else None

    @computed_field
    @property
    def initiative_bonus(self) -> int:
        return self.abilities.dex.mod() + self.init_misc

    @computed_field
    @property
    def save_fort(self) -> int:
        return self.base_fort + self.abilities.con.mod() + self.save_misc_fort

    @computed_field
    @property
    def save_ref(self) -> int:
        return self.base_ref + self.abilities.dex.mod() + self.save_misc_ref

    @computed_field
    @property
    def save_will(self) -> int:
        return self.base_will + self.abilities.wis.mod() + self.save_misc_will

    def _armor_dex_cap(self) -> int:
        armor = self.equipped_armor()
        if armor and armor.max_dex_bonus is not None:
            return armor.max_dex_bonus
        return 99

    def _armor_bonus(self) -> int:
        armor = self.equipped_armor()
        return armor.effective_armor_bonus if armor else 0

    def _shield_bonus(self) -> int:
        shield = self.equipped_shield()
        return shield.effective_shield_bonus if shield else 0

    def _size_mod(self) -> int:
        return SIZE_TO_MOD.get(self.size, 0)

    @computed_field
    @property
    def ac_total(self) -> int:
        dex = min(self.abilities.dex.mod(), self._armor_dex_cap())
        return (
            10 + self._armor_bonus() + self._shield_bonus() + dex + self._size_mod()
            + self.natural_armor + self.deflection_bonus + self.dodge_bonus + self.ac_misc
        )

    @computed_field
    @property
    def ac_touch(self) -> int:
        dex = min(self.abilities.dex.mod(), self._armor_dex_cap())
        return 10 + dex + self._size_mod() + self.deflection_bonus + self.dodge_bonus + self.ac_misc

    @computed_field
    @property
    def ac_ff(self) -> int:
        return 10 + self._armor_bonus() + self._shield_bonus() + self._size_mod() + self.natural_armor + self.deflection_bonus + self.ac_misc

    def _weapon_attack_enhancement(self, w: Optional[Weapon]) -> int:
        return w.enhancement_bonus if w else 0

    @computed_field
    @property
    def attack_melee_bonus(self) -> int:
        w = self.equipped_main_weapon()
        enh = self._weapon_attack_enhancement(w)
        return self.base_attack_bonus + self.bab_misc + self.abilities.str_.mod() + self._size_mod() + enh

    @computed_field
    @property
    def attack_ranged_bonus(self) -> int:
        w = self.equipped_ranged_weapon()
        enh = self._weapon_attack_enhancement(w)
        return self.base_attack_bonus + self.bab_misc + self.abilities.dex.mod() + self._size_mod() + enh