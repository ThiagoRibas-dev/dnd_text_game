from textual.app import App, ComposeResult
from textual.widgets import Input
from .engine.engine import GameEngine
from .ui.panels import LogPanel, StatsPanel, InventoryPanel, CommandBar
from .ui.chargen import CharGenState
from .ui.screens import TitleScreen, GameScreen # Import GameScreen
from .ui.ids import STATS_PANEL, LOG_PANEL, INVENTORY_PANEL, COMMAND_BAR

class DnDApp(App):
    CSS = """
    Screen { layout: vertical; }
    .main { layout: horizontal; height: 1fr; }
    .col { width: 1fr; border: solid gray; }
    .left  { width: 30%; }
    .center{ width: 40%; }
    .right { width: 30%; }
    .log { overflow: auto; }
    .centered { align: center middle; }
    #title { text-align: center; margin-bottom: 2; }
    Button { width: 30%; margin: 1; }
    Input { width: 30%; margin: 1; }
    Select { width: 30%; margin: 1; }
    .error { color: red; }
    .skill_scroll_container {
        height: 20; /* Take up available vertical space */
        overflow-y: scroll; /* Enable vertical scrolling */
        border: solid green; /* For debugging, remove later */
    }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.engine = GameEngine()
        self.state = self.engine.state
        self.cg_state = CharGenState() # Initialize CharGenState

    def compose(self) -> ComposeResult:
        # Main UI is now in GameScreen
        yield TitleScreen() # Start with the TitleScreen

    def on_mount(self) -> None:
        # Start at title screen
        self.push_screen(TitleScreen())

    def refresh_all(self, msg: str | None = None):
        # Query panels from the currently active screen (GameScreen)
        if msg:
            self.game_log(msg)

        stats_panel = self.screen.query_one(f"#{STATS_PANEL}", StatsPanel)
        inv_panel = self.screen.query_one(f"#{INVENTORY_PANEL}", InventoryPanel)

        stats_panel.update_state(self.engine.state)
        p = self.engine.state.player
        inv_panel.update_inventory(p.inventory, self.engine.state.resources_summary())

    async def on_input_submitted(self, event: Input.Submitted):
        cmd_bar = self.screen.query_one(f"#{COMMAND_BAR}", CommandBar)
        text = event.value.strip()
        cmd_bar.value = ""
        if not text:
            return
        out_lines = self.engine.execute(text)
        for line in out_lines:
            self.game_log(line)
        self.refresh_all()
        if self.engine.should_quit:
            self.exit()

    def game_log(self, msg: str):
        if isinstance(self.screen, GameScreen):
            log_panel = self.screen.query_one(f"#{LOG_PANEL}", LogPanel)
            log_panel.push(msg)
        else:
            print(f"[DEBUG LOG]: {msg}") # Print to console during chargen

    def return_to_title_screen(self) -> None:
        """Pops all screens until the TitleScreen is reached."""
        while not isinstance(self.screen, TitleScreen):
            self.pop_screen()

def run_app():
    try:
        app = DnDApp()
        app.run()
    except Exception as e:
        print(f"Error running app: {e}")
