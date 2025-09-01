from __future__ import annotations
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static, Checkbox
from textual.containers import Vertical, Horizontal
from textual import on
from dndrpg.engine.chargen import CharBuildState, build_entity_from_state, validate_character_picks
from dndrpg.engine.skills import skill_points_at_level1, max_ranks, CLASS_SKILLS
from dndrpg.engine.spells import bonus_slots_from_mod, sorcerer_spells_known_from_cha
from dndrpg.engine.prereq import eval_prereq, BuildView
from dndrpg.engine.chargen_helpers import STANDARD_ARRAYS, generate_4d6
from dndrpg.engine.wealth import roll_class_gold # Moved to top

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
        # 3.5 point-buy costs (8=0, 9=1, 10=2, 11=3, 12=4, 13=5, 14=6, 15=8, 16=10, 17:13, 18:16)
        table = {8:0,9:1,10:2,11:3,12:4,13:5,14:6,15:8,16:10,17:13,18:16}
        if score < 8 or score > 18:
            return 0
        return table.get(score, 0)

    def _validate_pb(self, vals: dict) -> tuple[bool, str]:
        try:
            scores = {k:int(v) for k,v in vals.items()}
        except ValueError:
            return (False, "All abilities must be integers.")
        if min(scores.values()) < 8 or max(scores.values()) > 18:
            return (False, "Scores must be between 8 and 18.")
        total = sum(self._point_cost(s) for s in scores.values())
        campaign_pb_limit = self.app_ref.engine.campaign.houserules.point_buy
        if total > campaign_pb_limit:
            return (False, f"Point-buy exceeds {campaign_pb_limit} (used {total}).")
        return (True, f"Point-buy OK (used {total}/{campaign_pb_limit}).")

    def compose(self):
        yield Vertical(
            Label("Ability Scores"),
            Label("Method:"),
            Select(options=[("Point Buy (28)","point_buy"),
                            ("Standard Array (15,14,13,12,10,8)","standard"),
                            ("4d6 drop lowest (random)","4d6")], id="method"),
            # Point-buy inputs
            Horizontal(
                Input(placeholder="STR", id="pb_str", classes="pb_input"),
                Input(placeholder="DEX", id="pb_dex", classes="pb_input"),
                Input(placeholder="CON", id="pb_con", classes="pb_input")
            ),
            Horizontal(
                Input(placeholder="INT", id="pb_int", classes="pb_input"),
                Input(placeholder="WIS", id="pb_wis", classes="pb_wis"),
                Input(placeholder="CHA", id="pb_cha", classes="pb_cha")
            ),
            # Standard array/Scores generated → user chooses assignment order
            Label("Assignment order (comma-separated, e.g., str,dex,con,int,wis,cha):", id="assign_label"),
            Input(placeholder="str,dex,con,int,wis,cha", id="assign_input"),
            Button("Generate (4d6)", id="gen4d6_button"),
            Static("", id="scores_display"),
            Button("Next", id="next"), Button("Back", id="back")
        )

    def on_mount(self):
        self._update_ui_visibility("point_buy")

    @on(Select.Changed, "#method")
    def on_method_changed(self, event: Select.Changed):
        self._update_ui_visibility(event.value)

    def _update_ui_visibility(self, method: str):
        is_point_buy = method == "point_buy"
        is_4d6 = method == "4d6"

        for input_widget in self.query(".pb_input"):
            input_widget.display = is_point_buy

        self.query_one("#assign_label").display = not is_point_buy
        self.query_one("#assign_input").display = not is_point_buy
        self.query_one("#gen4d6_button").display = is_4d6
        self.query_one("#scores_display").display = is_4d6

    def on_button_pressed(self, ev):
        method = self.query_one("#method", Select).value or "point_buy"
        if ev.button.id == "gen4d6_button" and method == "4d6":
            scores = generate_4d6(self.app_ref.engine.rng)
            self.query_one("#scores_display", Static).update(f"Rolled scores: {scores} (assign in the order field)")
            return
        if ev.button.id == "next":
            if method == "point_buy":
                vals = {
                    "str": int(self.query_one("#pb_str", Input).value or 15),
                    "dex": int(self.query_one("#pb_dex", Input).value or 12),
                    "con": int(self.query_one("#pb_con", Input).value or 14),
                    "int": int(self.query_one("#pb_int", Input).value or 10),
                    "wis": int(self.query_one("#pb_wis", Input).value or 12),
                    "cha": int(self.query_one("#pb_cha", Input).value or 8),
                }
                ok, msg = self._validate_pb(vals)
                if not ok:
                    self.app_ref.log_panel.push(f"[CharGen] {msg}")
                    return
                self.app_ref.cg_state.picks.abilities = vals
            elif method == "standard":
                arr = STANDARD_ARRAYS["classic"]
                order_str = self.query_one("#assign_input", Input).value
                if not order_str:
                    self.app_ref.log_panel.push("[CharGen] Please provide an assignment order (e.g., str,dex,con,int,wis,cha).")
                    return
                order = [a.strip().lower() for a in order_str.split(",")]
                if len(order) != 6 or len(set(order)) != 6 or not all(ab in ["str", "dex", "con", "int", "wis", "cha"] for ab in order):
                    self.app_ref.log_panel.push("[CharGen] Invalid assignment order. Must be 6 unique abilities (str,dex,con,int,wis,cha).")
                    return
                self.app_ref.cg_state.picks.abilities = dict(zip(order, arr))
            else:  # 4d6
                text = self.query_one("#scores_display", Static).renderable
                if not text:
                    self.app_ref.log_panel.push("[CharGen] Generate scores first, then assign.")
                    return
                import re
                m = re.search(r"\[(.*?)\]", str(text))
                scores = [int(x) for x in m.group(1).split(",")] if m else []
                if not scores or len(scores) != 6: # Ensure 6 scores are present
                    self.app_ref.log_panel.push("[CharGen] No valid scores generated or not enough scores. Click 'Generate (4d6)' first.")
                    return

                order_str = self.query_one("#assign_input", Input).value
                if not order_str:
                    self.app_ref.log_panel.push("[CharGen] Please provide an assignment order (e.g., str,dex,con,int,wis,cha).")
                    return
                order = [a.strip().lower() for a in order_str.split(",")]
                if len(order) != 6 or len(set(order)) != 6 or not all(ab in ["str", "dex", "con", "int", "wis", "cha"] for ab in order):
                    self.app_ref.log_panel.push("[CharGen] Invalid assignment order. Must be 6 unique abilities (str,dex,con,int,wis,cha).")
                    return
                self.app_ref.cg_state.picks.abilities = dict(zip(order, scores))

            self.app_ref.push_screen(StepRaceClass(self.app_ref))
        elif ev.button.id == "back":
            self.app_ref.pop_screen()


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
            is_valid, validation_message = validate_character_picks(
                self.app_ref.engine.content, self.app_ref.cg_state.picks
            )
            if not is_valid:
                self.app_ref.log_panel.push(f"[CharGen Validation Error] {validation_message}")
                return

            build_entity_from_state(self.app_ref.engine.content, self.app_ref.engine.state, self.app_ref.cg_state.picks,
                                    self.app_ref.engine.effects, self.app_ref.engine.resources,
                                    self.app_ref.engine.conditions, self.app_ref.engine.hooks)
            self.app_ref.engine.state.mode = "exploration"
            self.app_ref.log.push("Character created. Entering exploration.")
            self.app_ref.pop_screen()
            self.app_ref.refresh_all()

class StepDeityDomains(StepBase):
    def compose(self):
        picks = self.app_ref.cg_state.picks
        if picks.clazz != "cleric":
            # skip for non-cleric
            self.app_ref.push_screen(StepSkills(self.app_ref))
            return
        # Simplify: list domains from content effects with id prefix "domain."
        domains = [eid for eid, eff in self.app_ref.engine.content.effects.items() if eid.startswith("domain.")]
        options = [(d.split(".")[1].title(), d) for d in domains]  # name only, but value is full ID
        yield Vertical(
            Label("Deity (optional):"), Input(placeholder="(id or name)", id="deity"),
            Label("Pick two domains:"), Select(options=options, id="dom1"), Select(options=options, id="dom2"),
            Button("Next", id="next"), Button("Back", id="back")
        )
    def on_button_pressed(self, ev):
        if ev.button.id == "back":
            self.app_ref.pop_screen()
        if ev.button.id == "next":
            deity_id = self.query_one("#deity", Input).value
            if deity_id:
                self.app_ref.cg_state.picks.deity = deity_id

            d1 = self.query_one("#dom1", Select).value
            d2 = self.query_one("#dom2", Select).value
            if not d1 or not d2 or d1 == d2:
                self.app_ref.log.push("[CharGen] Pick two distinct domains.")
                return
            self.app_ref.cg_state.picks.domains = [d1, d2]
            self.app_ref.push_screen(StepSkills(self.app_ref))

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

class StepSkills(StepBase):
    def compose(self):
        yield Vertical(
            Label("Skills"),
            Static("Skill Points Available: 0", id="skill_points_display"),
            Static("Remaining: 0", id="skill_points_remaining"),
            Horizontal(
                Vertical(
                    Label("Acrobatics:"), Input(placeholder="0", id="skill_acrobatics", classes="skill_input"),
                    Label("Bluff:"), Input(placeholder="0", id="skill_bluff", classes="skill_input"),
                    Label("Concentration:"), Input(placeholder="0", id="skill_concentration", classes="skill_input"),
                    Label("Diplomacy:"), Input(placeholder="0", id="skill_diplomacy", classes="skill_input"),
                    Label("Heal:"), Input(placeholder="0", id="skill_heal", classes="skill_input"),
                ),
                Vertical(
                    Label("Intimidate:"), Input(placeholder="0", id="skill_intimidate", classes="skill_input"),
                    Label("Knowledge (Arcana):"), Input(placeholder="0", id="skill_knowledge_arcana", classes="skill_input"),
                    Label("Listen:"), Input(placeholder="0", id="skill_listen", classes="skill_input"),
                    Label("Sense Motive:"), Input(placeholder="0", id="skill_sense_motive", classes="skill_input"),
                    Label("Spot:"), Input(placeholder="0", id="skill_spot", classes="skill_input"),
                )
            ),
            Button("Next", id="next"), Button("Back", id="back")
        )

    def on_mount(self):
        self._update_skill_points()

    @on(Input.Changed, ".skill_input")
    def on_skill_input_changed(self, event: Input.Changed):
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
                
                # Validate max ranks
                is_class_skill = skill_name in CLASS_SKILLS.get(picks.clazz, [])
                max_allowed_ranks = max_ranks(1, is_class_skill) # Assuming level 1

                if ranks > max_allowed_ranks:
                    self.app_ref.log_panel.push(f"[CharGen] {skill_name.title()} ranks cannot exceed {max_allowed_ranks}.")
                    ranks = max_allowed_ranks
                    skill_input.value = str(ranks) # Correct invalid input

                current_skills[skill_name] = ranks
                allocated_points += ranks
            except ValueError:
                self.app_ref.log_panel.push(f"[CharGen] Invalid input for {skill_name.title()} ranks. Please enter a number.")
                skill_input.value = "0" # Reset invalid input
                current_skills[skill_name] = 0

        picks.skills = current_skills
        remaining_points = total_skill_points - allocated_points
        self.query_one("#skill_points_remaining", Static).update(f"Remaining: {remaining_points}")

        if remaining_points < 0:
            self.query_one("#skill_points_remaining", Static).add_class("error")
            self.app_ref.log_panel.push(f"[CharGen] You have allocated {abs(remaining_points)} too many skill points!")
        else:
            self.query_one("#skill_points_remaining", Static).remove_class("error")

    def on_button_pressed(self, ev):
        if ev.button.id == "next":
            # Final validation before proceeding
            picks = self.app_ref.cg_state.picks
            temp_int_score = picks.abilities.get("int", 10)
            temp_int_mod = (temp_int_score - 10) // 2
            total_skill_points = skill_points_at_level1(picks.clazz, temp_int_mod, picks.race == "human")

            allocated_points = sum(picks.skills.values())
            if allocated_points > total_skill_points:
                self.app_ref.log_panel.push(f"[CharGen] You have allocated {allocated_points - total_skill_points} too many skill points. Please adjust.")
                return
            
            # Proceed to next step (StepFeats)
            self.app_ref.push_screen(StepFeats(self.app_ref)) # Assuming StepFeats is the next step
        elif ev.button.id == "back":
            self.app_ref.pop_screen()

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

class StepWealthShop(StepBase):
    def compose(self):
        picks = self.app_ref.cg_state.picks
        mode = self.app_ref.engine.campaign.wealth.mode
        if mode == "kits":
            self.app_ref.push_screen(StepKits(self.app_ref))
            return
        if mode == "roll":
            gp = roll_class_gold(picks.clazz, self.app_ref.engine.rng)
        else:
            gp = self.app_ref.engine.campaign.wealth.fixed_gp or 100
        self.gp = gp
        # For MVP, allow item ids comma-separated with "buy id:qty", no prices enforced (we can add prices later)
        yield Vertical(
            Label(f"Wealth: {gp} gp (enter item ids comma-separated)"),
            Input(placeholder="wp.mace.heavy, ar.chain_shirt, sh.heavy_wooden", id="buy"),
            Button("Next", id="next"), Button("Back", id="back")
        )
    def on_button_pressed(self, ev):
        if ev.button.id == "back":
            self.app_ref.pop_screen()
        if ev.button.id == "next":
            ids = [t.strip() for t in (self.query_one("#buy", Input).value or "").split(",") if t.strip()]
            self.app_ref.cg_state.picks.gear_ids = ids
            self.app_ref.push_screen(StepSummary(self.app_ref))

class StepKits(StepBase):
    def compose(self):
        # show class kits from campaign
        kits = self.app_ref.engine.campaign.starting_equipment_packs.get(self.app_ref.cg_state.picks.clazz, [])
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
                                    self.app_ref.engine.effects, self.app_ref.engine.resources,
                                    self.app_ref.engine.conditions, self.app_ref.engine.hooks)
            
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
            
class StepFeats(StepBase):
    def compose(self):
        feats_container = Vertical(id="feats_container")
        # Placeholder for displaying feats
        feats_container.add_component(Label("Loading feats..."))
        yield Vertical(
            Label("Feats"),
            feats_container,
            Button("Next", id="next"), Button("Back", id="back")
        )

    def on_mount(self):
        self._load_and_display_feats()

    def _load_and_display_feats(self):
        feats_container = self.query_one("#feats_container", Vertical)
        feats_container.remove_children() # Clear existing content

        available_feats = []
        # Assuming feats are effects with id starting with "feat."
        for feat_id, feat_def in self.app_ref.engine.content.effects.items():
            if feat_id.startswith("feat."):
                available_feats.append(feat_def)

        if not available_feats:
            feats_container.add_component(Label("No feats available."))
            return

        # Create a BuildView for prerequisite evaluation
        import dataclasses
        picks = self.app_ref.cg_state.picks
        build_view = BuildView(entity=None, picks=dataclasses.asdict(picks))

        for feat_def in available_feats:
            # Display feat name and description
            feats_container.add_component(Label(f"[b]{feat_def.name}[/b]"))
            if feat_def.notes:
                feats_container.add_component(Label(feat_def.notes))
            feats_container.add_component(Label(feat_def.description))

            # Prerequisite checking
            can_take_feat = True
            prereq_msg = ""
            if feat_def.prerequisites:
                can_take_feat = eval_prereq(feat_def.prerequisites, build_view)
                prereq_msg = feat_def.prerequisites

            checkbox_id = f"feat_checkbox_{feat_def.id}"
            checkbox = Checkbox(
                f"Select {feat_def.name}",
                id=checkbox_id,
                classes="feat_checkbox",
                disabled=not can_take_feat
            )
            feats_container.add_component(checkbox)

            if not can_take_feat:
                feats_container.add_component(Label(f"[i]Prerequisites not met: {prereq_msg}[/i]", classes="prereq_error"))
            
            # Check if the feat is already selected (e.g., from a previous step or if returning to this screen)
            if feat_def.id in picks.feats:
                checkbox.value = True

            # Handle feat choices
            if feat_def.choices:
                for choice in feat_def.choices:
                    choice_id = f"feat_choice_{feat_def.id}_{choice.id}"
                    feats_container.add_component(Label(f"  {choice.name}:"))
                    if choice.type == "text":
                        input_widget = Input(
                            placeholder=choice.placeholder or "",
                            id=choice_id,
                            classes="feat_choice_input"
                        )
                        feats_container.add_component(input_widget)
                        # Restore previous choice if available
                        if feat_def.id in picks.feat_choices and choice.id in picks.feat_choices[feat_def.id]:
                            input_widget.value = picks.feat_choices[feat_def.id][choice.id]
                    elif choice.type == "select":
                        select_options = [(opt.label, opt.value) for opt in choice.options]
                        select_widget = Select(
                            options=select_options,
                            id=choice_id,
                            classes="feat_choice_select"
                        )
                        feats_container.add_component(select_widget)
                        # Restore previous choice if available
                        if feat_def.id in picks.feat_choices and choice.id in picks.feat_choices[feat_def.id]:
                            select_widget.value = picks.feat_choices[feat_def.id][choice.id]
            feats_container.add_component(Static("")) # Spacer

    @on(Checkbox.Changed, ".feat_checkbox")
    def on_feat_checkbox_changed(self, event: Checkbox.Changed):
        feat_id = event.widget.id.replace("feat_checkbox_", "")
        if event.value: # Checkbox is checked
            self.app_ref.cg_state.picks.feats.add(feat_id)
        else: # Checkbox is unchecked
            self.app_ref.cg_state.picks.feats.discard(feat_id)
        self.app_ref.log_panel.push(f"Selected feats: {sorted(list(self.app_ref.cg_state.picks.feats))}")

    @on(Input.Changed, ".feat_choice_input")
    def on_feat_choice_input_changed(self, event: Input.Changed):
        parts = event.widget.id.split("_")
        # Assuming ID format: feat_choice_feat.id_choice.id
        # This needs to be robust for different feat_id formats (e.g., feat.power_attack)
        # A better way might be to store feat_id and choice_id in data attributes of the widget
        # For now, let's assume feat_id is always two parts separated by a dot.
        feat_id_parts = parts[2:-1] # Get all parts between "feat_choice_" and "_choice.id"
        feat_id = ".".join(feat_id_parts)
        choice_id = parts[-1]
        
        if feat_id not in self.app_ref.cg_state.picks.feat_choices:
            self.app_ref.cg_state.picks.feat_choices[feat_id] = {}
        self.app_ref.cg_state.picks.feat_choices[feat_id][choice_id] = event.value
        self.app_ref.log_panel.push(f"Feat choice for {feat_id} ({choice_id}): {event.value}")

    @on(Select.Changed, ".feat_choice_select")
    def on_feat_choice_select_changed(self, event: Select.Changed):
        parts = event.widget.id.split("_")
        # Assuming ID format: feat_choice_feat.id_choice.id
        feat_id_parts = parts[2:-1]
        feat_id = ".".join(feat_id_parts)
        choice_id = parts[-1]

        if feat_id not in self.app_ref.cg_state.picks.feat_choices:
            self.app_ref.cg_state.picks.feat_choices[feat_id] = {}
        self.app_ref.cg_state.picks.feat_choices[feat_id][choice_id] = event.value
        self.app_ref.log_panel.push(f"Feat choice for {feat_id} ({choice_id}): {event.value}")
         
    def on_button_pressed(self, ev):
        if ev.button.id == "next":
            # Prerequisite validation
            picks = self.app_ref.cg_state.picks
            import dataclasses
            build_view = BuildView(entity=None, picks=dataclasses.asdict(picks))

            all_feats_valid = True
            for feat_id in picks.feats:
                feat_def = self.app_ref.engine.content.effects.get(feat_id)
                if feat_def and feat_def.prerequisites:
                    if not eval_prereq(feat_def.prerequisites, build_view):
                        self.app_ref.log_panel.push(f"[CharGen] Prerequisite not met for {feat_def.name}: {feat_def.prerequisites}")
                        all_feats_valid = False
            
            if not all_feats_valid:
                return # Stop if any feat is invalid

            self.app_ref.push_screen(StepSpells(self.app_ref))
        elif ev.button.id == "back":
            self.app_ref.pop_screen()