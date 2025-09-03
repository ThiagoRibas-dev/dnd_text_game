from __future__ import annotations
from typing import TYPE_CHECKING
from textual.app import ComposeResult
from textual.widgets import Header, Footer, Input, Static
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Select
from textual import on
from ..engine.save import list_saves, delete_save
from .panels import StatsPanel, LogPanel, InventoryPanel, CommandBar
from .chargen import StepNameAlignment # Import new chargen screens
from .ids import (
    STATS_PANEL, LOG_PANEL, INVENTORY_PANEL, COMMAND_BAR,
    TITLE_LABEL, NEW_GAME_BUTTON, CONTINUE_BUTTON, LOAD_GAME_BUTTON, QUIT_BUTTON,
    CAMPAIGN_SELECT, NEXT_BUTTON, BACK_BUTTON,
    SLOT_INPUT, LOAD_BUTTON, DELETE_BUTTON
)

if TYPE_CHECKING:
    from ..app import DnDApp

class TitleScreen(Screen):
    app: DnDApp
    BINDINGS = [("escape", "app.quit", "Quit")]
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("D&D 3.5e — Text RPG", id=TITLE_LABEL),
            Button("New Game", id=NEW_GAME_BUTTON),
            Button("Continue", id=CONTINUE_BUTTON),
            Button("Load Game", id=LOAD_GAME_BUTTON),
            Button("Quit", id=QUIT_BUTTON),
            classes="centered"
        )
    @on(Button.Pressed, f"#{NEW_GAME_BUTTON}")
    def _new(self) -> None:
        self.app.push_screen(CampaignSelectScreen()) # Start with campaign selection
    @on(Button.Pressed, f"#{CONTINUE_BUTTON}")
    def _cont(self) -> None:
        lines = self.app.engine.continue_latest()
        for ln in lines:
            self.app.game_log(ln)
        # After loading, ensure GameScreen is the active screen
        self.app.switch_screen(GameScreen())
        self.app.refresh_all("Continue loaded.")
    @on(Button.Pressed, f"#{LOAD_GAME_BUTTON}")
    def _load(self) -> None:
        self.app.push_screen(LoadScreen())
    @on(Button.Pressed, f"#{QUIT_BUTTON}")
    def _quit(self) -> None:
        self.app.exit()

class CampaignSelectScreen(Screen):
    app: DnDApp
    def compose(self) -> ComposeResult:
        opts = [(c.name, cid) for cid, c in self.app.engine.content.campaigns.items()]
        yield Vertical(Label("Select Campaign"), Select(options=opts, id=CAMPAIGN_SELECT), Button("Next", id=NEXT_BUTTON), Button("Back", id="BACK_BUTTON"))
    @on(Button.Pressed, f"#{BACK_BUTTON}")
    def _back(self) -> None:
        self.app.pop_screen()
    @on(Button.Pressed, f"#{NEXT_BUTTON}")
    def _next(self) -> None:
        sel = self.query_one(f"#{CAMPAIGN_SELECT}", Select).value
        if not sel:
            return
        self.app.engine.campaign = self.app.engine.content.campaigns[sel] # Set the campaign in the engine
        self.app.push_screen(StepNameAlignment(self.app)) # Start chargen after campaign selection

class LoadScreen(Screen):
    app: DnDApp
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
        yield Vertical(Label("Select a slot id and type it below:"), Static(table), Input(placeholder="slot id", id=SLOT_INPUT), Button("Load", id=LOAD_BUTTON), Button("Delete", id=DELETE_BUTTON), Button("Back", id="BACK_BUTTON"))
    @on(Button.Pressed, f"#{BACK_BUTTON}")
    def _back(self) -> None: self.app.pop_screen()
    @on(Button.Pressed, f"#{LOAD_BUTTON}")
    def _load(self) -> None:
        slot = self.query_one(f"#{SLOT_INPUT}", Input).value.strip()
        if not slot:
            return
        lines = self.app.engine.load_slot(slot)
        for ln in lines:
            self.app.game_log(ln)
        # Check if the load was successful before popping screens
        if not any("Error:" in line for line in lines):
            # Switch to GameScreen after successful load
            self.app.switch_screen(GameScreen())
            self.app.refresh_all("Save loaded.")
        else:
            # If there was an error, stay on the LoadScreen and show the error
            pass
    @on(Button.Pressed, f"#{DELETE_BUTTON}")
    def _del(self) -> None:
        slot = self.query_one(f"#{SLOT_INPUT}", Input).value.strip()
        if not slot:
            return
        delete_save(slot)
        self.app.game_log(f"Deleted save: {slot}")
        self.app.pop_screen()
        self.app.push_screen(LoadScreen())

class GameScreen(Screen):
    app: DnDApp
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="main"):
            stats_panel_widget = StatsPanel(classes="col left", id=STATS_PANEL)
            yield stats_panel_widget
            stats_panel_widget.bind_engine(self.app.engine)
            log_panel_widget = LogPanel(classes="col center log", id=LOG_PANEL) # Capture the widget
            yield log_panel_widget
            yield InventoryPanel(classes="col right", id=INVENTORY_PANEL)
        yield CommandBar(placeholder="Type commands (help, status, attack goblin, cast divine power, travel east 10m, rest 8h) and press Enter", id=COMMAND_BAR)
        yield Footer()

    def on_mount(self) -> None:
        self.call_after_refresh(self.app.refresh_all)