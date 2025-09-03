from __future__ import annotations
from textual.widgets import Button, Input, Label, Static
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual import on # Import on decorator
from textual import events # Import events for focus handling

from dndrpg.engine.skills import skill_points_at_level1, max_ranks, CLASS_SKILLS

from .base import StepBase
from .step_feats import StepFeats

class StepSkills(StepBase):
    def compose(self):
        yield Vertical(
            Label("Skills"),
            Static("Skill Points Available: 0", id="skill_points_display"),
            Static("Remaining: 0", id="skill_points_remaining"),
            Label("", id="skill_message_label", classes="error"), # Added message label
            ScrollableContainer(
                Horizontal(
                    Vertical(
                        Label("Appraise:"), Input(placeholder="0", id="skill_appraise", classes="skill_input"),
                        Label("Autohypnosis:"), Input(placeholder="0", id="skill_autohypnosis", classes="skill_input"),
                        Label("Balance:"), Input(placeholder="0", id="skill_balance", classes="skill_input"),
                        Label("Bluff:"), Input(placeholder="0", id="skill_bluff", classes="skill_input"),
                        Label("Climb:"), Input(placeholder="0", id="skill_climb", classes="skill_input"),
                        Label("Concentration:"), Input(placeholder="0", id="skill_concentration", classes="skill_input"),
                        Label("Control Shape:"), Input(placeholder="0", id="skill_control_shape", classes="skill_input"),
                        Label("Craft:"), Input(placeholder="0", id="skill_craft", classes="skill_input"),
                        Label("Decipher Script:"), Input(placeholder="0", id="skill_decipher_script", classes="skill_input"),
                        Label("Diplomacy:"), Input(placeholder="0", id="skill_diplomacy", classes="skill_input"),
                        Label("Disable Device:"), Input(placeholder="0", id="skill_disable_device", classes="skill_input"),
                        Label("Disguise:"), Input(placeholder="0", id="skill_disguise", classes="skill_input"),
                        Label("Escape Artist:"), Input(placeholder="0", id="skill_escape_artist", classes="skill_input"),
                        Label("Forgery:"), Input(placeholder="0", id="skill_forgery", classes="skill_input"),
                        Label("Gather Information:"), Input(placeholder="0", id="skill_gather_information", classes="skill_input"),
                        Label("Handle Animal:"), Input(placeholder="0", id="skill_handle_animal", classes="skill_input"),
                        Label("Heal:"), Input(placeholder="0", id="skill_heal", classes="skill_input"),
                        Label("Hide:"), Input(placeholder="0", id="skill_hide", classes="skill_input"),
                        Label("Intimidate:"), Input(placeholder="0", id="skill_intimidate", classes="skill_input"),
                        Label("Jump:"), Input(placeholder="0", id="skill_jump", classes="skill_input"),
                        Label("Knowledge:"), Input(placeholder="0", id="skill_knowledge", classes="skill_input"),
                        Label("Listen:"), Input(placeholder="0", id="skill_listen", classes="skill_input"),
                        Label("Martial Lore:"), Input(placeholder="0", id="skill_martial_lore", classes="skill_input"),
                    ),
                    Vertical(
                        Label("Move Silently:"), Input(placeholder="0", id="skill_move_silently", classes="skill_input"),
                        Label("Open Lock:"), Input(placeholder="0", id="skill_open_lock", classes="skill_input"),
                        Label("Perform:"), Input(placeholder="0", id="skill_perform", classes="skill_input"),
                        Label("Profession:"), Input(placeholder="0", id="skill_profession", classes="skill_input"),
                        Label("Psicraft:"), Input(placeholder="0", id="skill_psicraft", classes="skill_input"),
                        Label("Ride:"), Input(placeholder="0", id="skill_ride", classes="skill_input"),
                        Label("Search:"), Input(placeholder="0", id="skill_search", classes="skill_input"),
                        Label("Sense Motive:"), Input(placeholder="0", id="skill_sense_motive", classes="skill_input"),
                        Label("Sleight of Hand:"), Input(placeholder="0", id="skill_sleight_of_hand", classes="skill_input"),
                        Label("Speak Language:"), Input(placeholder="0", id="skill_speak_language", classes="skill_input"),
                        Label("Spellcraft:"), Input(placeholder="0", id="skill_spellcraft", classes="skill_input"),
                        Label("Spot:"), Input(placeholder="0", id="skill_spot", classes="skill_input"),
                        Label("Survival:"), Input(placeholder="0", id="skill_survival", classes="skill_input"),
                        Label("Swim:"), Input(placeholder="0", id="skill_swim", classes="skill_input"),
                        Label("Truespeak:"), Input(placeholder="0", id="skill_truespeak", classes="skill_input"),
                        Label("Tumble:"), Input(placeholder="0", id="skill_tumble", classes="skill_input"),
                        Label("Use Magic Device:"), Input(placeholder="0", id="skill_use_magic_device", classes="skill_input"),
                        Label("Use Psionic Device:"), Input(placeholder="0", id="skill_use_psionic_device", classes="skill_input"),
                        Label("Use Rope:"), Input(placeholder="0", id="skill_use_rope", classes="skill_input"),
                    )
                ),
                classes="skill_scroll_container" # Added class for CSS
            ),
            Button("Next", id="next"), Button("Back", id="back")
        )

    def on_mount(self):
        self._update_skill_points()

    @on(Input.Changed, ".skill_input")
    def on_skill_input_changed(self, event: Input.Changed):
        # Clear previous messages
        self.query_one("#skill_message_label", Label).update("")
        self.game_log(f"[CharGen] Skill input changed: {event.control.id} value: {event.value}")
        self._update_skill_points()

    def _update_skill_points(self):
        picks = self.app_ref.cg_state.picks
        # For initial calculation, we need a dummy entity to get INT mod
        # This is a simplification; a proper solution would pass the current ability scores
        # or calculate them based on picks.abilities
        temp_int_score = picks.abilities.get("int", 10) # Default to 10 if not set yet
        temp_int_mod = (temp_int_score - 10) // 2

        total_skill_points = skill_points_at_level1(picks.clazz, temp_int_mod, picks.race == "human")
        self.query_one("#skill_points_display", Static).update(f"Skill Points Available: {total_skill_points}")

        allocated_points = 0
        current_skills = {}
        for skill_input in self.query(".skill_input"):
            skill_name = skill_input.id.replace("skill_", "")
            try:
                ranks = int(skill_input.value or 0)
                if ranks < 0:
                    ranks = 0
                    skill_input.value = "0" # Reset invalid input
                    self.game_log(f"[CharGen] {skill_name.title()} ranks cannot be negative. Reset to 0.")
                
                # Validate max ranks
                is_class_skill = skill_name in CLASS_SKILLS.get(picks.clazz, [])
                max_allowed_ranks = max_ranks(1, is_class_skill) # Assuming level 1

                if ranks > max_allowed_ranks:
                    self.game_log(f"[CharGen] {skill_name.title()} ranks cannot exceed {max_allowed_ranks}. Reset to {max_allowed_ranks}.")
                    ranks = max_allowed_ranks
                    skill_input.value = str(ranks) # Correct invalid input

                current_skills[skill_name] = ranks
                allocated_points += ranks
            except ValueError:
                self.game_log(f"[CharGen] Invalid input for {skill_name.title()} ranks. Please enter a number. Reset to 0.")
                skill_input.value = "0" # Reset invalid input
                current_skills[skill_name] = 0

        picks.skills = current_skills
        remaining_points = total_skill_points - allocated_points
        self.query_one("#skill_points_remaining", Static).update(f"Remaining: {remaining_points}")

        if remaining_points < 0:
            self.query_one("#skill_points_remaining", Static).add_class("error")
            self.game_log(f"[CharGen] You have allocated {abs(remaining_points)} too many skill points!")
        else:
            self.query_one("#skill_points_remaining", Static).remove_class("error")
            # Clear message if everything is valid
            if not self.query_one("#skill_message_label", Label).has_class("error"): # Only clear if no other error is present
                self.query_one("#skill_message_label", Label).update("")

    def on_button_pressed(self, ev):
        if ev.button.id == "next":
            # Clear previous messages
            self.query_one("#skill_message_label", Label).update("")

            # Final validation before proceeding
            picks = self.app_ref.cg_state.picks
            temp_int_score = picks.abilities.get("int", 10)
            temp_int_mod = (temp_int_score - 10) // 2
            total_skill_points = skill_points_at_level1(picks.clazz, temp_int_mod, picks.race == "human")

            allocated_points = sum(picks.skills.values())
            if allocated_points > total_skill_points:
                self.game_log(f"[CharGen] You have allocated {allocated_points - total_skill_points} too many skill points. Please adjust.")
                return
            
            # Proceed to next step (StepFeats)
            self.app_ref.push_screen(StepFeats(self.app_ref))
        elif ev.button.id == "back":
            self.app_ref.pop_screen()

    @on(events.Focus)
    def on_skill_input_focus(self, event: events.Focus) -> None:
        """Scroll the container to the focused input."""
        if isinstance(event.widget, Input) and "skill_input" in event.widget.classes:
            self.query_one(".skill_scroll_container", ScrollableContainer).scroll_to_widget(event.widget)
