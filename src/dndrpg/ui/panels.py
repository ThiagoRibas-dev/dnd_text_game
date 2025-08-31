from textual.widgets import Input, Static
from textual.reactive import reactive
from rich.table import Table
from ..engine.state import GameState
from ..engine.models import Item
from ..engine.engine import GameEngine

class StatsPanel(Static):
    engine: GameEngine | None = None

    def bind_engine(self, engine: GameEngine):
        self.engine = engine

    def update_state(self, state: GameState):
        if not state or not self.engine:
            self.update("No state")
            return
        p = state.player
        resolved = self.engine.modifiers.resolved_stats(p)

        table = Table(title="Stats (resolved)", pad_edge=False, show_header=False)
        table.add_row("HP", f"{p.hp_current}/{p.hp_max}")
        table.add_row("AC", f"{resolved['ac_total']} (T {resolved['ac_touch']} / FF {resolved['ac_ff']})")
        table.add_row("Initiative", f"+{p.initiative_bonus}")  # init modifiers can be added later
        table.add_row("Melee", f"+{resolved['attack_melee_bonus']}")
        table.add_row("Ranged", f"+{resolved['attack_ranged_bonus']}")
        table.add_row("Saves", f"F+{resolved['save_fort']} R+{resolved['save_ref']} W+{resolved['save_will']}")
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
