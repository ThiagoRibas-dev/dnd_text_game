from __future__ import annotations
from textual.widgets import Button, Input, Label, Static
from textual.containers import Vertical
from textual import on

from dndrpg.engine.spells import bonus_slots_from_mod, sorcerer_spells_known_from_cha

from .base import StepBase
from .step_kits import StepKits
from .step_wealth_shop import StepWealthShop

class StepSpells(StepBase):
    def compose(self):
        picks = self.app_ref.cg_state.picks
        clazz = picks.clazz
        
        if clazz == "cleric":
            yield Vertical(
                Label("Cleric Spells Preparation"),
                Label("Prepared Spells (Level 0):"),
                Input(placeholder="spell.light, spell.detect_magic", id="spells_0", classes="spell_input"),
                Label("Prepared Spells (Level 1):"),
                Input(placeholder="spell.cure_light_wounds, spell.bless", id="spells_1", classes="spell_input"),
                Static("", id="cleric_slots_display"),
                Button("Next", id="next"), Button("Back", id="back")
            )
        elif clazz == "sorcerer":
            yield Vertical(
                Label("Sorcerer Spells Known"),
                Label("Spells Known (comma-separated IDs):"),
                Input(placeholder="spell.magic_missile, spell.shield", id="spells_known_input"),
                Static("", id="sorcerer_slots_display"),
                Button("Next", id="next"), Button("Back", id="back")
            )
        else:
            yield Vertical(
                Label("No spells for this class."),
                Button("Next", id="next"), Button("Back", id="back")
            )

    def on_mount(self):
        self._update_spell_slots_display()

    @on(Input.Changed, ".spell_input")
    @on(Input.Changed, "#spells_known_input")
    def on_spell_input_changed(self, event: Input.Changed):
        self._update_spell_slots_display()

    def _update_spell_slots_display(self):
        picks = self.app_ref.cg_state.picks
        clazz = picks.clazz
        
        if clazz == "cleric":
            wis_mod = (picks.abilities.get("wis", 10) - 10) // 2
            expected_slots = bonus_slots_from_mod(wis_mod, max_level=picks.level)
            
            display_text = "Available Slots:\n"
            for level, count in expected_slots.items():
                display_text += f"Level {level}: {count} slots\n"
            
            self.query_one("#cleric_slots_display", Static).update(display_text)

        elif clazz == "sorcerer":
            cha_mod = (picks.abilities.get("cha", 10) - 10) // 2
            expected_known = sorcerer_spells_known_from_cha(picks.level, cha_mod)
            
            display_text = "Spells Known (Max):\n"
            for level, count in expected_known.items():
                display_text += f"Level {level}: {count} spells\n"
            
            self.query_one("#sorcerer_slots_display", Static).update(display_text)

    def on_button_pressed(self, ev):
        if ev.button.id == "back":
            self.app_ref.pop_screen()
        elif ev.button.id == "next":
            picks = self.app_ref.cg_state.picks
            clazz = picks.clazz

            if clazz == "cleric":
                prepared_spells = {}
                for level in range(2): # Levels 0 and 1 for now
                    input_id = f"#spells_{level}"
                    spells_str = self.query_one(input_id, Input).value or ""
                    spells_list = [s.strip() for s in spells_str.split(",") if s.strip()]
                    prepared_spells[level] = spells_list
                picks.spells_prepared = prepared_spells

                # Basic validation for cleric prepared spells
                wis_mod = (picks.abilities.get("wis", 10) - 10) // 2
                expected_slots = bonus_slots_from_mod(wis_mod, max_level=picks.level)
                for level, spells in prepared_spells.items():
                    if len(spells) > expected_slots.get(level, 0):
                        self.app_ref.log_panel.push(f"[CharGen] Too many Level {level} spells prepared for Cleric. Max: {expected_slots.get(level, 0)}")
                        return

            elif clazz == "sorcerer":
                spells_str = self.query_one("#spells_known_input", Input).value or ""
                spells_list = [s.strip() for s in spells_str.split(",") if s.strip()]
                picks.spells_known = spells_list

                # Basic validation for sorcerer spells known
                cha_mod = (picks.abilities.get("cha", 10) - 10) // 2
                expected_known = sorcerer_spells_known_from_cha(picks.level, cha_mod)
                total_expected_known = sum(expected_known.values())
                if len(spells_list) > total_expected_known:
                    self.app_ref.log_panel.push(f"[CharGen] Too many spells known for Sorcerer. Max: {total_expected_known}")
                    return

            # Route to wealth/shop step
            campaign = self.app_ref.engine.campaign
            if campaign.wealth.mode == "kits":
                self.app_ref.push_screen(StepKits(self.app_ref))
            else:
                self.app_ref.push_screen(StepWealthShop(self.app_ref))
