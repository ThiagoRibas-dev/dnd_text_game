from textual.widgets import Input, Static
from textual.reactive import reactive
from rich.table import Table
from ..engine.state import GameState
from ..engine.models import Item

class StatsPanel(Static):
    state: GameState | None = None
    def update_state(self, state: GameState):
        self.state = state
        if not state:
            self.update("No state")
            return
        p = state.player
        table = Table(title="Stats", pad_edge=False, show_header=False)
        table.add_row("HP", f"{p.hp_current}/{p.hp_max}")
        table.add_row("AC", f"{p.ac_total} (T {p.ac_touch} / FF {p.ac_ff})")
        table.add_row("Initiative", f"+{p.initiative_bonus}")
        table.add_row("Melee", f"+{p.attack_melee_bonus}")
        table.add_row("Ranged", f"+{p.attack_ranged_bonus}")
        table.add_row("Saves", f"F+{p.save_fort} R+{p.save_ref} W+{p.save_will}")
        self.update(table)

class InventoryPanel(Static):
    def update_inventory(self, items: list[Item], resources: dict[str, int]):
        table = Table(title="Inventory / Resources", pad_edge=False, show_header=False)
        if items:
            table.add_row("Items", ", ".join(it.name for it in items))
        if resources:
            for k, v in resources.items():
                table.add_row(k, str(v))
        self.update(table)

class LogPanel(Static):
    log_lines: list[str] = reactive([])

    def push(self, line: str):
        self.log_lines.append(line)
        self.update("\n".join(self.log_lines[-200:]))

class CommandBar(Input):
    pass
