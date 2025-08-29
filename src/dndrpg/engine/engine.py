from .state import GameState, default_state

class GameEngine:
    def __init__(self):
        self.state: GameState = default_state()

    def execute(self, cmd: str) -> list[str]:
        # VERY TEMPORARY: route to stubs, return printable lines
        c = cmd.lower()
        out: list[str] = []
        if c in ("help", "?"):
            out.append("Commands: status, attack <target>, cast <spell>, rest 8h, travel <dir> <minutes>, inventory")
        elif c.startswith("status"):
            p = self.state.player
            out.append(f"{p.name} | HP {p.hp_current}/{p.hp_max} AC {p.ac_total} (T{p.ac_touch}/FF{p.ac_ff}) | Melee +{p.attack_melee_bonus}")
        elif c.startswith("inventory"):
            out.append("Inventory: " + ", ".join(self.state.player.inventory))
        elif c.startswith("attack"):
            out.append("You attack the goblin. (stub) Roll to hit, apply DR/resist, etc.")
        elif c.startswith("cast divine power"):
            out.append("You cast Divine Power. +6 STR (enhancement), BAB min=level, +1 temp HP/CL. (stub)")
        elif c.startswith("cast grease"):
            out.append("You cast Grease (10-ft square). Creatures must save or fall prone. (stub)")
        elif c.startswith("rest"):
            out.append("You rest. (stub) Rest windows and refresh to be implemented.")
        elif c.startswith("travel"):
            out.append("You travel through the wilderness. (stub) Will trigger random encounters later.")
        else:
            out.append(f"Unknown command: {cmd}")
        return out
