from __future__ import annotations
from textual.widgets import Button, Input, Label, Select
from textual.containers import Vertical

from .base import StepBase
from .step_ability import StepAbility

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
