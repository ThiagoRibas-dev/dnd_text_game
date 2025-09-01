from __future__ import annotations
from textual.widgets import Button, Input, Label, Select, Static
from textual.containers import Vertical, Horizontal
from textual import on

from dndrpg.engine.chargen_helpers import STANDARD_ARRAYS, generate_4d6

from .base import StepBase
from .step_race_class import StepRaceClass

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
                    print(f"[CharGen] {msg}")
                    return
                self.app_ref.cg_state.picks.abilities = vals
            elif method == "standard":
                arr = STANDARD_ARRAYS["classic"]
                order_str = self.query_one("#assign_input", Input).value
                if not order_str:
                    print("[CharGen] Please provide an assignment order (e.g., str,dex,con,int,wis,cha).")
                    return
                order = [a.strip().lower() for a in order_str.split(",")]
                if len(order) != 6 or len(set(order)) != 6 or not all(ab in ["str", "dex", "con", "int", "wis", "cha"] for ab in order):
                    print("[CharGen] Invalid assignment order. Must be 6 unique abilities (str,dex,con,int,wis,cha).")
                    return
                self.app_ref.cg_state.picks.abilities = dict(zip(order, arr))
            else:  # 4d6
                text = self.query_one("#scores_display", Static).renderable
                if not text:
                    print("[CharGen] Generate scores first, then assign.")
                    return
                import re
                m = re.search(r"\[(.*?)\]", str(text))
                scores = [int(x) for x in m.group(1).split(",")] if m else []
                if not scores or len(scores) != 6: # Ensure 6 scores are present
                    print("[CharGen] No valid scores generated or not enough scores. Click 'Generate (4d6)' first.")
                    return

                order_str = self.query_one("#assign_input", Input).value
                if not order_str:
                    print("[CharGen] Please provide an assignment order (e.g., str,dex,con,int,wis,cha).")
                    return
                order = [a.strip().lower() for a in order_str.split(",")]
                if len(order) != 6 or len(set(order)) != 6 or not all(ab in ["str", "dex", "con", "int", "wis", "cha"] for ab in order):
                    print("[CharGen] Invalid assignment order. Must be 6 unique abilities (str,dex,con,int,wis,cha).")
                    return
                self.app_ref.cg_state.picks.abilities = dict(zip(order, scores))

            self.app_ref.push_screen(StepRaceClass(self.app_ref))
        elif ev.button.id == "back":
            self.app_ref.pop_screen()
