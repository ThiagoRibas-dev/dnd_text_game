from pathlib import Path
from .state import GameState, default_state
from .loader import load_content, ContentIndex
from .campaigns import CampaignDefinition
from .models import Entity, Abilities, AbilityScore, Size
from .save import save_game, load_game, list_saves, latest_save

ENGINE_VERSION = "0.1.0"

CLASS_TABLE = {
    "fighter": {"hd": 10, "bab": "full", "fort": "good", "ref": "poor", "will": "poor"},
    "cleric": {"hd": 8, "bab": "three_quarter", "fort": "good", "ref": "poor", "will": "good"},
    "sorcerer": {"hd": 4, "bab": "half", "fort": "poor", "ref": "poor", "will": "good"},
    "monk": {"hd": 8, "bab": "three_quarter", "fort": "good", "ref": "good", "will": "good"},
}

def bab_from_prog(prog: str, level: int) -> int:
    if prog == "full":
        return level
    if prog == "three_quarter":
        return int(level * 3 / 4)
    if prog == "half":
        return level // 2
    return 0

def base_save(is_good: str, level: int) -> int:
    # Good: 2 at 1st; Poor: 0 at 1st (simplified)
    return 2 if is_good == "good" else 0

class GameEngine:
    def __init__(self):
        self.content_dir = Path(__file__).resolve().parent.parent / "content"
        self.content: ContentIndex = load_content(self.content_dir)
        self.campaign: CampaignDefinition | None = None
        self.state: GameState = default_state(self.content)  # placeholder until New Game
        self.slot_id: str | None = None

    # — New Game flow helpers —
    def build_entity_lvl1(self, name: str, race: str, cls: str, abilities: dict[str, int], kit_ids: list[str]) -> Entity:
        # Build abilities
        ab = Abilities(
            str_=AbilityScore(base=abilities["str"]),
            dex=AbilityScore(base=abilities["dex"]),
            con=AbilityScore(base=abilities["con"]),
            int_=AbilityScore(base=abilities["int"]),
            wis=AbilityScore(base=abilities["wis"]),
            cha=AbilityScore(base=abilities["cha"]),
        )
        # Class bases
        ct = CLASS_TABLE[cls]
        bab = bab_from_prog(ct["bab"], 1)
        fort = base_save(ct["fort"], 1)
        ref = base_save(ct["ref"], 1)
        will = base_save(ct["will"], 1)
        hd = ct["hd"]
        hp_max = hd + ab.con.mod()  # hp first level max (houserule default)
        ent = Entity(
            id="pc.hero", name=f"{name} ({race.title()} {cls.title()} 1)", level=1, size=Size.MEDIUM,
            abilities=ab, base_attack_bonus=bab, base_fort=fort, base_ref=ref, base_will=will,
            hp_max=max(1, hp_max), hp_current=max(1, hp_max),
        )
        # Apply kits
        for kit_id in kit_ids:
            kit = self.content.kits[kit_id]
            for iid in kit.items:
                ent.inventory.append(self.content.clone_item(iid))
            for slot, iid in kit.auto_equip.items():
                ent.equipment[slot] = iid
        return ent

    def start_new_game(self, camp_id: str, entity: Entity, slot_id: str = "slot1") -> list[str]:
        self.campaign = self.content.campaigns[camp_id]
        self.state = GameState(player=entity)
        self.slot_id = slot_id
        save_game(slot_id, self.campaign.id, ENGINE_VERSION, self.state, description=entity.name)
        return [f"New game started in campaign: {self.campaign.name}", f"Character: {entity.name}"]

    def continue_latest(self) -> list[str]:
        meta = latest_save()
        if not meta:
            return ["No saves found."]
        self.slot_id = meta.slot_id
        self.state = load_game(meta.slot_id, GameState)
        self.campaign = self.content.campaigns.get(meta.campaign_id)
        return [f"Loaded latest save: {meta.slot_id} ({meta.description})"]

    def load_slot(self, slot_id: str) -> list[str]:
        self.state = load_game(slot_id, GameState)
        md = [m for m in list_saves() if m.slot_id == slot_id][0]
        self.campaign = self.content.campaigns.get(md.campaign_id)
        self.slot_id = slot_id
        return [f"Loaded save: {slot_id}"]

    def save_current(self) -> list[str]:
        if not self.slot_id or not self.campaign:
            return ["No active slot/campaign."]
        save_game(self.slot_id, self.campaign.id, ENGINE_VERSION, self.state, description=self.state.player.name)
        return ["Game saved."]

    def execute(self, cmd: str) -> list[str]:
        c = cmd.lower().strip()
        out: list[str] = []
        if c in ("help","?"):
            out.append("Commands: status, inventory, attack <target>, cast <spell>, rest 8h, travel <dir> <minutes>")
        elif c.startswith("status"):
            p = self.state.player
            out.append(f"{p.name} | HP {p.hp_current}/{p.hp_max} AC {p.ac_total} (T{p.ac_touch}/FF{p.ac_ff}) | Melee +{p.attack_melee_bonus}")
        elif c.startswith("inventory"):
            names = [it.name for it in self.state.player.inventory]
            out.append("Inventory: " + (", ".join(names) if names else "(empty)"))
        elif c.startswith("attack"):
            out.append("You attack the goblin. (stub) Roll to hit, apply DR/resist, etc.")
        elif c.startswith("cast divine power"):
            out.append("You cast Divine Power. (stub)")
        elif c.startswith("cast grease"):
            out.append("You cast Grease (10-ft square). (stub)")
        elif c.startswith("rest"):
            out.append("You rest. (stub)")
        elif c.startswith("travel"):
            out.append("You travel. (stub)")
        elif c.startswith("save"):
            out.append(self.save_current()[0])
        else:
            out.append(f"Unknown command: {cmd}")
        return out