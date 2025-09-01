from __future__ import annotations
from textual.widgets import Button, Input, Label, Static, Checkbox, Select
from textual.containers import Vertical
from textual import on

from dndrpg.engine.prereq import eval_prereq, BuildView

from .base import StepBase
from .step_spells import StepSpells

class StepFeats(StepBase):
    def compose(self):
        feats_container = Vertical(id="feats_container")
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
            feats_container.mount(Label("No feats available."))
            return

        # Create a BuildView for prerequisite evaluation
        import dataclasses
        picks = self.app_ref.cg_state.picks
        build_view = BuildView(entity=None, picks=dataclasses.asdict(picks))

        for feat_def in available_feats:
            # Display feat name and description
            feats_container.mount(Label(f"[b]{feat_def.name}[/b]"))
            if feat_def.notes:
                feats_container.mount(Label(feat_def.notes))
            feats_container.mount(Label(feat_def.description))

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
            feats_container.mount(checkbox)

            if not can_take_feat:
                feats_container.mount(Label(f"[i]Prerequisites not met: {prereq_msg}[/i]", classes="prereq_error"))
            
            # Check if the feat is already selected (e.g., from a previous step or if returning to this screen)
            if feat_def.id in picks.feats:
                checkbox.value = True

            # Handle feat choices
            if feat_def.choices:
                for choice in feat_def.choices:
                    choice_id = f"feat_choice_{feat_def.id}_{choice.id}"
                    feats_container.mount(Label(f"  {choice.name}:"))
                    if choice.type == "text":
                        input_widget = Input(
                            placeholder=choice.placeholder or "",
                            id=choice_id,
                            classes="feat_choice_input"
                        )
                        feats_container.mount(input_widget)
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
                        feats_container.mount(select_widget)
                        # Restore previous choice if available
                        if feat_def.id in picks.feat_choices and choice.id in picks.feat_choices[feat_def.id]:
                            select_widget.value = picks.feat_choices[feat_def.id][choice.id]
            feats_container.mount(Static("")) # Spacer

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
