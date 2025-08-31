from __future__ import annotations
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select
from textual.containers import Vertical, Horizontal
from textual import on
from dndrpg.engine.chargen import CharBuildState, build_entity_from_state

class CharGenState:
    def __init__(self):
        self.picks = CharBuildState()

class StepBase(Screen):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref  # DnDApp

class StepNameAlignment(StepBase):
    def compose(self):
        yield Vertical(
            Label("Name & Alignment"),
            Input(placeholder="Name", id="name"),
            Select(options=[(a,a) for a in ("lawful good","neutral good","chaotic good","lawful neutral","neutral","chaotic neutral","lawful evil","neutral evil","chaotic evil")], id="alignment"),
            Button("Next", id="next")
        )
    def on_button_pressed(self, ev):
        if ev.button.id == "next":
            name = self.query_one("#name", Input).value or "Hero"
            alig = self.query_one("#alignment", Select).value or "neutral"
            self.app_ref.cg_state.picks.name = name
            self.app_ref.cg_state.picks.alignment = alig
            self.app_ref.push_screen(StepAbility(self.app_ref))

class StepAbility(StepBase):
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
        campaign_pb_limit = self.app_ref.engine.campaign.houserules.point_buy # Access from engine.campaign
        if total > campaign_pb_limit:
            return (False, f"Point-buy exceeds {campaign_pb_limit} (used {total}).")
        return (True, f"Point-buy OK (used {total}/{campaign_pb_limit}).")

    def compose(self):
        yield Vertical(
            Label("Point-Buy"),
            Label("Current: 0/28 points used", id="pb_feedback"), # New label for feedback
            Horizontal(Input(placeholder="STR", id="str"), Input(placeholder="DEX", id="dex"), Input(placeholder="CON", id="con")),
            Horizontal(Input(placeholder="INT", id="int"), Input(placeholder="WIS", id="wis"), Input(placeholder="CHA", id="cha")),
            Button("Next", id="next"), Button("Back", id="back")
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
        campaign_pb_limit = self.app_ref.engine.campaign.houserules.point_buy # Access from engine.campaign
        
        if ok:
            pb_label.update(f"Current: {current_total}/{campaign_pb_limit} points used. {msg}")
            pb_label.set_class(False, "error") # Remove error class if present
        else:
            pb_label.update(f"Current: {current_total}/{campaign_pb_limit} points used. [red]{msg}[/red]")
            pb_label.set_class(True, "error") # Add error class for styling

    def on_button_pressed(self, ev):
        if ev.button.id == "next":
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
                self.app_ref.log_panel.push(f"[CharGen] {msg}")
                return
            
            self.app_ref.cg_state.picks.abilities = {k:int(v) for k,v in vals.items()}
            self.app_ref.push_screen(StepRaceClass(self.app_ref))
        elif ev.button.id == "back":
            self.app_ref.pop_screen()

class StepRaceClass(StepBase):
    def compose(self):
        yield Vertical(
            Label("Race & Class"),
            Select(options=[("Human","human"),("Dwarf","dwarf"),("Elf","elf")], id="race"),
            Select(options=[("Fighter","fighter"),("Cleric","cleric"),("Sorcerer","sorcerer"),("Monk","monk")], id="class"),
            Button("Next", id="next"), Button("Back", id="back")
        )
    def on_button_pressed(self, ev):
        if ev.button.id == "next":
            race = self.query_one("#race", Select).value or "human"
            clazz = self.query_one("#class", Select).value or "fighter"
            self.app_ref.cg_state.picks.race = race
            self.app_ref.cg_state.picks.clazz = clazz
            self.app_ref.push_screen(StepKits(self.app_ref))
        elif ev.button.id == "back":
            self.app_ref.pop_screen()

class StepKits(StepBase):
    def compose(self):
        # show class kits from campaign
        camp = self.app_ref.engine.campaign
        kits = camp.starting_equipment_packs.get(self.app_ref.cg_state.picks.clazz, [])
        opts = [(k, k) for k in kits] if kits else [("None","none")]
        yield Vertical(
            Label("Starting Kit"),
            Select(options=opts, id="kit"),
            Button("Finish", id="finish"), Button("Back", id="back")
        )
    def on_button_pressed(self, ev):
        if ev.button.id == "finish":
            sel = self.query_one("#kit", Select).value
            if sel and sel != "none":
                kit = self.app_ref.engine.content.kits[sel]
                self.app_ref.cg_state.picks.gear_ids = list(kit.items)
            # Build entity
            build_entity_from_state(self.app_ref.engine.content, self.app_ref.engine.state, self.app_ref.cg_state.picks,
                                    self.app_ref.engine.effects, self.app_ref.engine.resources, self.app_ref.engine.conditions, self.app_ref.engine.hooks)
            
            # Start new game with the built entity
            self.app_ref.engine.start_new_game(
                self.app_ref.engine.campaign.id, 
                self.app_ref.engine.state.player, # The entity is already set in state.player by build_entity_from_state
                slot_id="slot1" # Or allow user to pick slot
            )

            self.app_ref.log_panel.push("Character created. Entering exploration.") # Use log_panel
            
            # Pop all screens to return to the main game UI
            # Pop all screens to return to the main game UI
            self.app_ref.pop_screen()  # Pop StepKits
            self.app_ref.pop_screen()  # Pop StepRaceClass
            self.app_ref.pop_screen()  # Pop StepAbility
            self.app_ref.pop_screen()  # Pop StepNameAlignment
            self.app_ref.pop_screen()  # Pop CampaignSelectScreen
            self.app_ref.pop_screen()  # Pop TitleScreen (NEW)
            
            self.app_ref.refresh_all() # Refresh main game UI
        elif ev.button.id == "back":
            self.app_ref.pop_screen()
