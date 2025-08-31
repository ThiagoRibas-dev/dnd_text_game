from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Select
from textual import on
from .engine.save import list_saves, delete_save
from .engine.engine import GameEngine
from .ui.panels import StatsPanel, LogPanel, InventoryPanel, CommandBar

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
        self.app.push_screen(CampaignSelectScreen())
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
        self.app.push_screen(CharGenScreen(campaign_id=sel))

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
        self.app.pop_screen()
        self.app.refresh_all("Save loaded.")
    @on(Button.Pressed, "#del")
    def _del(self) -> None:
        slot = self.query_one("#slot", Input).value.strip()
        if not slot:
            return
        delete_save(slot)
        self.app.log_panel.push(f"Deleted save: {slot}")
        self.app.pop_screen()
        self.app.push_screen(LoadScreen())

class CharGenScreen(Screen):
    def __init__(self, campaign_id: str):
        super().__init__()
        self.campaign_id = campaign_id
    def _point_cost(self, score: int) -> int:
        # 3.5 point-buy costs (8=0, 9=1, 10=2, 11=3, 12=4, 13=5, 14=6, 15=8, 16=10, 17=13, 18=16)
        table = {8:0,9:1,10:2,11:3,12:4,13:5,14:6,15:8,16:10,17:13,18:16}
        # If score is outside the valid range (8-18), treat its cost as 0 for calculation purposes
        # The _validate_pb will still catch the invalid score range.
        if score < 8 or score > 18:
            return 0
        return table.get(score, 0) # Return 0 if score not in table (shouldn't happen with valid range check)
    def _validate_pb(self, vals: dict) -> tuple[bool, str]:
        try:
            scores = {k:int(v) for k,v in vals.items()}
        except Exception:
            return (False, "All abilities must be integers.")
        if min(scores.values()) < 8 or max(scores.values()) > 18:
            return (False, "Scores must be between 8 and 18.")
        total = sum(self._point_cost(s) for s in scores.values())
        campaign_pb_limit = self.app.engine.content.campaigns[self.campaign_id].houserules.get("point_buy", 28)
        if total > campaign_pb_limit:
            return (False, f"Point-buy exceeds {campaign_pb_limit} (used {total}).")
        return (True, f"Point-buy OK (used {total}/{campaign_pb_limit}).")
    def compose(self) -> ComposeResult:
        classes = ["fighter","cleric","sorcerer","monk"]
        yield Vertical(
            Label("Character Creation"),
            Input(placeholder="Name", id="name"),
            Select(options=[(c.title(), c) for c in classes], id="class"),
            Label("Point-Buy. Enter scores 8–18:"),
            Label("Current: 0/32 points used", id="pb_feedback"), # New label for feedback
            Horizontal(Input(placeholder="STR", id="str"), Input(placeholder="DEX", id="dex"), Input(placeholder="CON", id="con")),
            Horizontal(Input(placeholder="INT", id="int"), Input(placeholder="WIS", id="wis"), Input(placeholder="CHA", id="cha")),
            Label("Race (basic)"), Select(options=[("Human","human"),("Dwarf","dwarf"),("Elf","elf")], id="race"),
            Button("Create", id="create"), Button("Back", id="back")
        )
    def on_mount(self) -> None:
        self._update_point_buy_feedback() # Initial update

    @on(Input.Changed, "#str,#dex,#con,#int,#wis,#cha")
    def _on_ability_input_changed(self) -> None:
        self._update_point_buy_feedback()

    def _update_point_buy_feedback(self) -> None:
        vals = {
            "str": self.query_one("#str", Input).value or "0", # Use "0" for empty to avoid int conversion errors
            "dex": self.query_one("#dex", Input).value or "0",
            "con": self.query_one("#con", Input).value or "0",
            "int": self.query_one("#int", Input).value or "0",
            "wis": self.query_one("#wis", Input).value or "0",
            "cha": self.query_one("#cha", Input).value or "0",
        }
        
        # Calculate current total points used
        current_total = 0
        try:
            scores = {k:int(v) for k,v in vals.items()}
            current_total = sum(self._point_cost(s) for s in scores.values())
        except ValueError:
            # Handle non-integer input gracefully
            pass

        ok, msg = self._validate_pb(vals)
        
        pb_label = self.query_one("#pb_feedback", Label)
        campaign_pb_limit = self.app.engine.content.campaigns[self.campaign_id].houserules.get("point_buy", 28)
        
        if ok:
            pb_label.update(f"Current: {current_total}/{campaign_pb_limit} points used. {msg}")
            pb_label.set_class(False, "error") # Remove error class if present
        else:
            pb_label.update(f"Current: {current_total}/{campaign_pb_limit} points used. [red]{msg}[/red]")
            pb_label.set_class(True, "error") # Add error class for styling

    @on(Button.Pressed, "#back")
    def _back(self) -> None:
        self.app.pop_screen()
    @on(Button.Pressed, "#create")
    def _create(self) -> None:
        name = self.query_one("#name", Input).value.strip() or "Hero"
        cls = self.query_one("#class", Select).value or "fighter"
        race = self.query_one("#race", Select).value or "human"
        vals = {
            "str": self.query_one("#str", Input).value or "15",
            "dex": self.query_one("#dex", Input).value or "12",
            "con": self.query_one("#con", Input).value or "14",
            "int": self.query_one("#int", Input).value or "10",
            "wis": self.query_one("#wis", Input).value or "12",
            "cha": self.query_one("#cha", Input).value or "8",
        }
        ok, msg = self._validate_pb(vals)
        if not ok:
            self.app.log_panel.push(f"[CharGen] {msg}")
            return
        abilities = {k:int(v) for k,v in vals.items()}
        # Choose kits from campaign by class
        camp = self.app.engine.content.campaigns[self.campaign_id]
        kit_ids = camp.starting_equipment_packs.get(cls, [])
        if not kit_ids:
            self.app.log_panel.push("No kit found for class; creating with empty inventory.")
        ent = self.app.engine.build_entity_lvl1(name=name, race=race, cls=cls, abilities=abilities, kit_ids=kit_ids)
        lines = self.app.engine.start_new_game(self.campaign_id, ent, slot_id="slot1")
        for ln in lines:
            self.app.log_panel.push(ln)
        self.app.pop_screen()
        self.app.pop_screen()
        self.app.pop_screen() # Pops TitleScreen
        self.app.refresh_all("New game created.")

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

def run_app():
    DnDApp().run()