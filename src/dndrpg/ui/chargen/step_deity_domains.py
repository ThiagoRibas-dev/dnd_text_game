from __future__ import annotations
import copy # Import the copy module
from textual.widgets import Button, Label, Select
from textual.containers import Vertical

from dndrpg.engine.chargen import validate_character_picks # Import the validation function
from .base import StepBase
from .step_skills import StepSkills

class StepDeityDomains(StepBase):
    def compose(self):
        picks = self.app_ref.cg_state.picks
        if picks.clazz != "cleric":
            # skip for non-cleric
            self.app_ref.push_screen(StepSkills(self.app_ref))
            return
        
        # Get available deities and format for Select widget
        deity_options = [("None", None)]
        deity_options.extend(sorted([(d.name, d.id) for d in self.app_ref.engine.content.deities.values()], key=lambda x: x[0]))

        # Simplify: list domains from content effects with id prefix "domain."
        domains = [eid for eid, eff in self.app_ref.engine.content.effects.items() if eid.startswith("domain.")]
        domain_options = [(d.split(".")[1].title(), d) for d in domains]  # name only, but value is full ID
        yield Vertical(
            Label("Deity (optional):"), Select(options=deity_options, id="deity_select", value=None),
            Label("Pick two domains:"), Select(options=domain_options, id="dom1"), Select(options=domain_options, id="dom2"),
            Label("", id="message_label", classes="error"), # Added message label
            Button("Next", id="next"), Button("Back", id="back")
        )
    def on_button_pressed(self, ev):
        if ev.button.id == "back":
            self.app_ref.pop_screen()
        if ev.button.id == "next":
            # Clear previous messages
            self.query_one("#message_label", Label).update("")

            deity_id = self.query_one("#deity_select", Select).value
            self.app_ref.cg_state.picks.deity = deity_id

            d1 = self.query_one("#dom1", Select).value
            d2 = self.query_one("#dom2", Select).value

            if self.app_ref.cg_state.picks.clazz == "cleric":
                if not deity_id:
                    self.query_one("#message_label", Label).update("[CharGen] Clerics must select a deity.")
                    return
                if not d1 or not d2 or d1 == d2:
                    self.query_one("#message_label", Label).update("[CharGen] Pick two distinct domains.")
                    return
                
                # Perform validation using the engine's function
                temp_picks = copy.deepcopy(self.app_ref.cg_state.picks) # Create a deep copy to test validation
                temp_picks.deity = deity_id
                temp_picks.domains = [d1, d2]

                is_valid, validation_message = validate_character_picks(self.app_ref.engine.content, temp_picks)
                
                if not is_valid:
                    self.query_one("#message_label", Label).update(f"[CharGen] {validation_message}")
                    return
            
            self.app_ref.cg_state.picks.domains = [d1, d2]
            self.app_ref.push_screen(StepSkills(self.app_ref))
