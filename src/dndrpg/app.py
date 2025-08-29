from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input
from textual.containers import Horizontal
from .engine.engine import GameEngine
from .ui.panels import StatsPanel, LogPanel, InventoryPanel, CommandBar

class DnDApp(App):
    CSS = """
    Screen { layout: vertical; }
    .main { layout: horizontal; height: 1fr; }
    .col { width: 1fr; border: solid gray; }
    .left  { width: 30%; }
    .center{ width: 40%; }
    .right { width: 30%; }
    .log { overflow: auto; }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.engine = GameEngine()
        self.state = self.engine.state

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="main"):
            self.stats_panel = StatsPanel(classes="col left")
            self.log_panel = LogPanel(classes="col center log")
            self.inv_panel = InventoryPanel(classes="col right")
            yield self.stats_panel
            yield self.log_panel
            yield self.inv_panel
        self.cmd_bar = CommandBar(placeholder="Type commands (help, status, attack goblin, cast divine power, travel east 10m, rest 8h) and press Enter")
        yield self.cmd_bar
        yield Footer()

    def on_mount(self):
        self.refresh_all("Welcome to D&D 3.5e (Text) — type 'help' to begin.")

    def refresh_all(self, msg: str | None = None):
        if msg:
            self.log_panel.push(msg)
        self.stats_panel.update_state(self.engine.state)
        p = self.engine.state.player
        self.inv_panel.update_inventory(p.inventory, self.engine.state.resources_summary())

    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        self.cmd_bar.value = ""
        if not text:
            return
        out_lines = self.engine.execute(text)
        for line in out_lines:
            self.log_panel.push(line)
        self.refresh_all()

def run_app():
    DnDApp().run()