from __future__ import annotations
from textual.widgets import Button, Label, Static
from textual.containers import Vertical

from dndrpg.engine.chargen import build_entity_from_state, validate_character_picks

from .base import StepBase

class StepSummary(StepBase):
    def compose(self):
        picks = self.app_ref.cg_state.picks
        yield Vertical(
            Label("Summary (preview)"),
            Static(f"Name: {picks.name}  Race: {picks.race}  Class: {picks.clazz}  Align: {picks.alignment}"),
            Static(f"Abilities: {picks.abilities}"),
            Static(f"Skills: {picks.skills}"),
            Static(f"Feats: {sorted(picks.feats)}"),
            Static(f"Domains: {picks.domains}"),
            Static(f"Gear: {picks.gear_ids}"),
            Button("Confirm", id="confirm"), Button("Back", id="back")
        )
    def on_button_pressed(self, ev):
        if ev.button.id == "back":
            self.app_ref.pop_screen()
        if ev.button.id == "confirm":
            # Explicitly validate character picks before building the entity
            campaign_id = self.app_ref.engine.campaign.id if self.app_ref.engine.campaign else ""
            is_valid, validation_message = validate_character_picks(
                self.app_ref.engine.content, self.app_ref.cg_state.picks, campaign_id
            )
            if not is_valid:
                self.app_ref.log_panel.push(f"[CharGen Validation Error] {validation_message}")
                return

            build_entity_from_state(self.app_ref.engine.content, self.app_ref.engine.state, self.app_ref.cg_state.picks, campaign_id,
                                    self.app_ref.engine.effects, self.app_ref.engine.resources,
                                    self.app_ref.engine.conditions, self.app_ref.engine.hooks)
            self.app_ref.engine.state.mode = "exploration"
            self.app_ref.log_panel.push("Character created. Entering exploration.")
            self.app_ref.pop_screen()
            self.app_ref.refresh_all()
