from __future__ import annotations
from typing import TYPE_CHECKING
from textual.screen import Screen
from dndrpg.engine.chargen import CharBuildState

if TYPE_CHECKING:
    from ...app import DnDApp

class CharGenState:
    def __init__(self):
        self.picks = CharBuildState()

class StepBase(Screen):
    app_ref: DnDApp

    def __init__(self, app_ref: DnDApp):
        super().__init__()
        self.app_ref = app_ref

    def game_log(self, msg: str):
        self.app_ref.game_log(msg)
