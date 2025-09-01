from __future__ import annotations
from textual.widgets import Button, Label, Select
from textual.containers import Vertical

from dndrpg.engine.chargen import build_entity_from_state

from .base import StepBase

class StepKits(StepBase):
    def compose(self):
        # show class kits from campaign
        kits = self.app_ref.engine.campaign.starting_equipment_packs.get(self.app_ref.cg_state.picks.clazz, [])
        opts = [(k, k) for k in kits] if kits else [("None","none")]
        yield Vertical(
            Label("Starting Kit"),
            Select(options=opts, id="kit"),
            Label("", id="message_label", classes="error"), # Added message label
            Button("Finish", id="finish"), Button("Back", id="back")
        )
    def on_button_pressed(self, ev):
        if ev.button.id == "finish":
            sel = self.query_one("#kit", Select).value
            if sel and sel != "none":
                kit = self.app_ref.engine.content.kits[sel]
                self.app_ref.cg_state.picks.gear_ids = list(kit.items)
            
            # Clear previous messages
            self.query_one("#message_label", Label).update("")

            # Build entity
            entity, error_message = build_entity_from_state(self.app_ref.engine.content, self.app_ref.engine.state, self.app_ref.cg_state.picks,
                                    self.app_ref.engine.effects, self.app_ref.engine.resources,
                                    self.app_ref.engine.conditions, self.app_ref.engine.hooks)
            
            if entity is None:
                self.query_one("#message_label", Label).update(f"[CharGen] {error_message}")
                return

            # Start new game with the built entity
            self.app_ref.engine.start_new_game(
                self.app_ref.engine.content.campaigns[next(iter(self.app_ref.engine.content.campaigns))].id, # Use the first campaign ID
                self.app_ref.engine.state.player, # The entity is already set in state.player by build_entity_from_state
                slot_id="slot1" # Or allow user to pick slot
            )

            self.app_ref.log_panel.push("Character created. Entering exploration.") # Use log_panel
            
            # Pop all chargen screens to return to the main game UI
            num_chargen_screens = 0
            for screen in reversed(self.app_ref._screen_stack):
                if isinstance(screen, StepBase):
                    num_chargen_screens += 1
            
            for _ in range(num_chargen_screens):
                self.app_ref.pop_screen()
            
            # Also pop CampaignSelectScreen and TitleScreen
            self.app_ref.pop_screen()
            self.app_ref.pop_screen()
            
            self.app_ref.refresh_all() # Refresh main game UI
        elif ev.button.id == "back":
            self.app_ref.pop_screen()
