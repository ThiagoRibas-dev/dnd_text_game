from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Select
from textual import on
from .engine.save import list_saves, delete_save
from .engine.engine import GameEngine
from .ui.panels import StatsPanel, LogPanel, InventoryPanel, CommandBar
from .ui.chargen import CharGenState, StepNameAlignment # Import new chargen screens

class TitleScreen(Screen):
    BINDINGS = [("escape", "app.quit", "Quit")]
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("D&D 3.5e — Text RPG", id="title"),
            Button("New Game", id="new"),
            Button("Continue", id="cont"),
            Button("Load Game", id="load"),
            Button("Quit", id="quit"),
            classes="centered"
        )
    @on(Button.Pressed, "#new")
    def _new(self) -> None:
        self.app.push_screen(CampaignSelectScreen()) # Start with campaign selection
    @on(Button.Pressed, "#cont")
    def _cont(self) -> None:
        lines = self.app.engine.continue_latest()
        for ln in lines:
            self.app.log_panel.push(ln)
        self.app.pop_screen()  # return to game UI
        self.app.refresh_all("Continue loaded.")
    @on(Button.Pressed, "#load")
    def _load(self) -> None:
        self.app.push_screen(LoadScreen())
    @on(Button.Pressed, "#quit")
    def _quit(self) -> None:
        self.app.exit()

class CampaignSelectScreen(Screen):
    def compose(self) -> ComposeResult:
        opts = [(c.name, cid) for cid, c in self.app.engine.content.campaigns.items()]
        yield Vertical(Label("Select Campaign"), Select(options=opts, id="camp"), Button("Next", id="next"), Button("Back", id="back"))
    @on(Button.Pressed, "#back")
    def _back(self) -> None:
        self.app.pop_screen()
    @on(Button.Pressed, "#next")
    def _next(self) -> None:
        sel = self.query_one("#camp", Select).value
        if not sel:
            return
        self.app.engine.campaign = self.app.engine.content.campaigns[sel] # Set the campaign in the engine
        self.app.push_screen(StepNameAlignment(self.app)) # Start chargen after campaign selection

class LoadScreen(Screen):
    def compose(self) -> ComposeResult:
        from rich.table import Table
        table = Table(title="Saves", show_header=True, header_style="bold")
        table.add_column("Slot")
        table.add_column("Campaign")
        table.add_column("When")
        table.add_column("Desc")
        self.saves = list_saves()
        for m in self.saves:
            from datetime import datetime
            when = datetime.fromtimestamp(m.last_played_ts).strftime("%Y-%m-%d %H:%M")
            table.add_row(m.slot_id, m.campaign_id, when, m.description)
        yield Vertical(Label("Select a slot id and type it below:"), Static(table), Input(placeholder="slot id", id="slot"), Button("Load", id="load"), Button("Delete", id="del"), Button("Back", id="back"))
    @on(Button.Pressed, "#back")
    def _back(self) -> None: self.app.pop_screen()
    @on(Button.Pressed, "#load")
    def _load(self) -> None:
        slot = self.query_one("#slot", Input).value.strip()
        if not slot:
            return
        lines = self.app.engine.load_slot(slot)
        for ln in lines:
            self.app.log_panel.push(ln)
        # Check if the load was successful before popping screens
        if not any("Error:" in line for line in lines):
            # Pop LoadScreen and TitleScreen to reveal the main game UI
            self.app.pop_screen() # Pop LoadScreen
            self.app.pop_screen() # Pop TitleScreen
            self.app.refresh_all("Save loaded.")
        else:
            # If there was an error, stay on the LoadScreen and show the error
            pass
    @on(Button.Pressed, "#del")
    def _del(self) -> None:
        slot = self.query_one("#slot", Input).value.strip()
        if not slot:
            return
        delete_save(slot)
        self.app.log_panel.push(f"Deleted save: {slot}")
        self.app.pop_screen()
        self.app.push_screen(LoadScreen())

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

    def on_mount(self) -> None:
        # Start at title screen
        self.push_screen(TitleScreen())
        self.stats_panel.bind_engine(self.engine)
        self.refresh_all("Welcome! Use the title screen to start or load a game.")

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
        if self.engine.should_quit:
            self.exit()

def run_app():
    try:
        app = DnDApp()
        app.run()
    except Exception as e:
        print(f"Error running app: {e}")