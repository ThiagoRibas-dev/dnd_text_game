from __future__ import annotations
from textual.widgets import Button, Input, Label
from textual.containers import Vertical

from dndrpg.engine.wealth import roll_class_gold

from .base import StepBase
from .step_kits import StepKits
from .step_summary import StepSummary

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
