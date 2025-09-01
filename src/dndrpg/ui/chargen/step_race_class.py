from __future__ import annotations
from textual.widgets import Button, Label, Select
from textual.containers import Vertical

from .base import StepBase
from .step_deity_domains import StepDeityDomains
from .step_skills import StepSkills

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
            if clazz == "cleric":
                self.app_ref.push_screen(StepDeityDomains(self.app_ref))
            else:
                self.app_ref.push_screen(StepSkills(self.app_ref))
        elif ev.button.id == "back":
            self.app_ref.pop_screen()
