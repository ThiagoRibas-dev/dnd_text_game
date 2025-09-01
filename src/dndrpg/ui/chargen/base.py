from __future__ import annotations
from textual.screen import Screen
from dndrpg.engine.chargen import CharBuildState

class CharGenState:
    def __init__(self):
        self.picks = CharBuildState()

class StepBase(Screen):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref  # DnDApp
