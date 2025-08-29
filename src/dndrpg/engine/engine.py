from pathlib import Path
from .state import GameState, default_state
from .loader import load_content, ContentIndex

class GameEngine:
    def __init__(self):
        # Locate the bundled content directory
        self.content_dir = Path(__file__).resolve().parent.parent / "content"
        self.content: ContentIndex = load_content(self.content_dir)
        self.state: GameState = default_state(self.content)

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
        else:
            out.append(f"Unknown command: {cmd}")
        return out