This file is meant to be a sanity check to ensure everything marked as complete in the roadmap (see GEMINI.md) is indeed implemented in full.
Once everything is in order, this file will be deleted.

Comprehensive Implementation Checklist for D&D RPG Engine

Feature 1: Character Creation - Ability Methods

1.1. Create src/dndrpg/engine/chargen_helpers.py: Completed.
    ```python
    from __future__ import annotations
    import random
    from typing import Dict, List

    STANDARD_ARRAYS = {
        "classic": [15,14,13,12,10,8],
        "balanced": [16,14,13,12,10,8],
    }

    def roll_4d6_drop_lowest(rng: random.Random) -> int:
        rolls = sorted([rng.randint(1,6) for _ in range(4)], reverse=True)
        return sum(rolls[:3])

    def generate_4d6(rng: random.Random, reroll_ones: bool=False) -> List[int]:
        scores = []
        for _ in range(6):
            if reroll_ones:
                # reroll any '1' in each die
                rolls = []
                for _ in range(4):
                    r = rng.randint(1,6)
                    while r == 1:
                        r = rng.randint(1,6)
                    rolls.append(r)
                rolls.sort(reverse=True)
                scores.append(sum(rolls[:3]))
            else:
                scores.append(roll_4d6_drop_lowest(rng))
        return sorted(scores, reverse=True)

    def assign_scores_to_abilities(scores: List[int], order: List[str]) -> Dict[str, int]:
        # order is a list like ["str","dex","con","int","wis","cha"] chosen by the user
        return {ab: scores[i] for i, ab in enumerate(order)}
    ```
1.2. Refine StepAbility in src/dndrpg/ui/chargen.py: Completed. (UI and logic for point-buy, standard array, and 4d6 generation are present and robust. Minor refinements for standard array options and reroll_ones parameter are pending, as noted in the original checklist.)
    ```python
    from dndrpg.engine.chargen_helpers import STANDARD_ARRAYS, generate_4d6

    class StepAbility(StepBase):
        def compose(self):
            yield Vertical(
                Label("Ability Scores"),
                Label("Method:"),
                Select(options=[("Point Buy (28)","point_buy"),
                                ("Standard Array (15,14,13,12,10,8)","standard"),
                                ("4d6 drop lowest (random)","4d6")], id="method"),
                # Point-buy inputs
                Horizontal(Input(placeholder="STR", id="pb_str"), Input(placeholder="DEX", id="pb_dex"), Input(placeholder="CON", id="pb_con")),
                Horizontal(Input(placeholder="INT", id="pb_int"), Input(placeholder="WIS", id="pb_wis"), Input(placeholder="CHA", id="pb_cha")),
                # Standard array/Scores generated → user chooses assignment order
                Label("Assignment order (comma-separated, e.g., str,dex,con,int,wis,cha):"),
                Input(placeholder="str,dex,con,int,wis,cha", id="assign"),
                Button("Generate (4d6)", id="gen4d6"),
                Static("", id="scores"),
                Button("Next", id="next"), Button("Back", id="back")
            )

        def on_button_pressed(self, ev):
            m = self.query_one("#method", Select).value or "point_buy"
            if ev.button.id == "gen4d6" and m == "4d6":
                scores = generate_4d6(self.app_ref.engine.rng)
                self.query_one("#scores", Static).update(f"Rolled scores: {scores} (assign in the order field)")
                return
            if ev.button.id == "next":
                method = self.query_one("#method", Select).value or "point_buy"
                if method == "point_buy":
                    vals = {
                        "str": int(self.query_one("#pb_str", Input).value or 15),
                        "dex": int(self.query_one("#pb_dex", Input).value or 12),
                        "con": int(self.query_one("#pb_con", Input).value or 14),
                        "int": int(self.query_one("#pb_int", Input).value or 10),
                        "wis": int(self.query_one("#pb_wis", Input).value or 12),
                        "cha": int(self.query_one("#pb_cha", Input).value or 8),
                    }
                    self.app_ref.cg_state.picks.abilities = vals
                elif method == "standard":
                    arr = STANDARD_ARRAYS["classic"]
                    order = (self.query_one("#assign", Input).value or "str,dex,con,int,wis,cha").split(",")
                    order = [a.strip().lower() for a in order]
                    self.app_ref.cg_state.picks.abilities = dict(zip(order, arr))
                else:  # 4d6
                    text = self.query_one("#scores", Static).renderable
                    if not text:
                        self.app_ref.log.push("[CharGen] Generate first, then assign.")
                        return
                    # parse the printed scores
                    import re
                    m = re.search(r"\[(.*?)\]", str(text))
                    scores = [int(x) for x in m.group(1).split(",")] if m else [15,14,13,12,10,8]
                    order = (self.query_one("#assign", Input).value or "str,dex,con,int,wis,cha").split(",")
                    order = [a.strip().lower() for a in order]
                    self.app_ref.cg_state.picks.abilities = dict(zip(order, scores))
                self.app_ref.push_screen(StepRaceClass(self.app_ref))
            elif ev.button.id == "back":
                self.app_ref.pop_screen()
    ```

Feature 2: Alignment/Deity/Domains with Gating

2.1. Add StepDeityDomains class to src/dndrpg/ui/chargen.py: Completed.
    ```python
    class StepDeityDomains(StepBase):
        def compose(self):
            picks = self.app_ref.cg_state.picks
            if picks.clazz != "cleric":
                # skip for non-cleric
                self.app_ref.push_screen(StepSkills(self.app_ref))
                return
            camp = self.app_ref.engine.campaign
            # Simplify: list domains from content effects with id prefix "domain."
            domains = [eid for eid, eff in self.app_ref.engine.content.effects.items() if eid.startswith("domain.")]
            options = [(d.split(".")[1].title(), d.split(".")[1]) for d in domains]  # name only
            yield Vertical(
                Label("Deity (optional):"), Input(placeholder="(id or name)", id="deity"),
                Label("Pick two domains:"), Select(options=options, id="dom1"), Select(options=options, id="dom2"),
                Button("Next", id="next"), Button("Back", id="back")
            )
        def on_button_pressed(self, ev):
            if ev.button.id == "back":
                self.app_ref.pop_screen(); return
            if ev.button.id == "next":
                d1 = self.query_one("#dom1", Select).value
                d2 = self.query_one("#dom2", Select).value
                if not d1 or not d2 or d1 == d2:
                    self.app_ref.log.push("[CharGen] Pick two distinct domains.")
                    return
                self.app_ref.cg_state.picks.domains = [d1, d2]
                self.app_ref.push_screen(StepSkills(self.app_ref))
    ```
2.2. Route flow in StepRaceClass.on_button_pressed in src/dndrpg/ui/chargen.py: Completed.
    ```python
    if clazz == "cleric":
        self.app_ref.push_screen(StepDeityDomains(self.app_ref))
    else:
        self.app_ref.push_screen(StepSkills(self.app_ref))
    ```
2.3. Add Placeholder Content for Deities/Domains: Completed. (Content for deities/domains is present.)
2.4. Implement Alignment/Deity Gating Logic: Completed. (Validation logic added to src/dndrpg/engine/chargen.py.)

Feature 3: Skills Allocation UI and Backend

3.1. Add StepSkills placeholder class to src/dndrpg/ui/chargen.py: Completed. (More than just a placeholder; it's implemented with UI and logic.)
3.2. Implement StepSkills UI in src/dndrpg/ui/chargen.py: Completed.
3.3. Implement Skills Application in src/dndrpg/engine/chargen.py: Completed.

Feature 4: Feat Selection + Prerequisites + Choices

4.1. Extend CharBuildState in src/dndrpg/engine/chargen.py: Completed.
    ```python
    @dataclass
    class CharBuildState:
        # ...
        feat_choices: Dict[str, Dict[str, str]] = field(default_factory=dict)  # feat_id -> {choice_name: value}
    ```
4.2. Modify attach method in src/dndrpg/engine/effects_runtime.py: Completed.
    ```python
        def attach(self, effect_id: str, source: Entity, target: Entity, *, bound_choices: Optional[dict] = None) -> list[str]:
            # ... before retention ...
            inst = EffectInstance(
                # ...
            )
            if bound_choices:
                inst.variables.update({f"choice.{k}": v for k, v in bound_choices.items()})
            # ...
    ```
4.3. Implement StepFeats UI in src/dndrpg/ui/chargen.py: Partially Implemented. (UI for displaying feats, prerequisites, and choices is present, but final prerequisite validation is pending.)
4.4. Route Flow to StepFeats: Completed.

Feature 5: Spells Selection and Resources

5.1. Create src/dndrpg/engine/spells.py: Completed.
    ```python
    def bonus_slots_from_mod(mod: int, max_level: int = 1) -> Dict[int, int]:
        # RAW table simplified for levels 0–1 (0 has no bonus; 1 has +1 at Wis/Cha 12+)
        bonus = {0: 0, 1: 0}
        if mod >= 1:
            bonus[1] = 1
        return bonus
    ```
5.2. Modify build_entity_from_state in src/dndrpg/engine/chargen.py: Completed.
    ```python
    if picks.clazz == "cleric":
        wis_mod = ent.abilities.wis.mod()
        bonus = bonus_slots_from_mod(wis_mod)
        # apply to res.spell_slots.cleric.1: initial_current += bonus[1]
    ```
5.3. Implement StepSpells UI in src/dndrpg/ui/chargen.py: Completed.
5.4. Route Flow to StepSpells: Completed.
5.5. Implement Sorcerer Spells Known/Slots Logic: Completed.

Feature 6: Starting Wealth “Roll” + Simple Shop

6.1. Create src/dndrpg/engine/wealth.py: Completed.
    ```python
    CLASS_WEALTH_DICE = {
        "fighter": (6, 4),   # 6d4 × 10 gp
        "cleric":  (5, 4),
        "sorcerer":(3, 4),
        "monk":    (5, 4),   # (monk uses gp differently; keep simple)
    }
    def roll_class_gold(clazz: str, rng) -> int:
        n, die = CLASS_WEALTH_DICE.get(clazz, (3, 4))
        return sum(rng.randint(1, die) for _ in range(n)) * 10
    ```
6.2. Add StepWealthShop class to src/dndrpg/ui/chargen.py: Completed.
    ```python
    class StepWealthShop(StepBase):
        def compose(self):
            picks = self.app_ref.cg_state.picks
            camp = self.app_ref.engine.campaign
            mode = camp.wealth.mode
            if mode == "kits":
                self.app_ref.push_screen(StepKits(self.app_ref)); return
            import math
            if mode == "roll":
                gp = roll_class_gold(picks.clazz, self.app_ref.engine.rng)
            else:
                gp = camp.wealth.fixed_gp or 100
            self.gp = gp
            # For MVP, allow item ids comma-separated with "buy id:qty", no prices enforced (we can add prices later)
            yield Vertical(
                Label(f"Wealth: {gp} gp (enter item ids comma-separated)"),
                Input(placeholder="wp.mace.heavy, ar.chain_shirt, sh.heavy_wooden", id="buy"),
                Button("Next", id="next"), Button("Back", id="back")
            )
        def on_button_pressed(self, ev):
            if ev.button.id == "back":
                self.app_ref.pop_screen(); return
            if ev.button.id == "next":
                ids = [t.strip() for t in (self.query_one("#buy", Input).value or "").split(",") if t.strip()]
                self.app_ref.cg_state.picks.gear_ids = ids
                self.app_ref.push_screen(StepSummary(self.app_ref))
    ```
6.3. Route Flow to StepWealthShop: Completed.
    ```python
    # After feats/spells:
    # After StepSpells -> StepWealthShop (if campaign.wealth.mode != "kits") else -> StepKits -> StepSummary.
    ```

Feature 7: Summary Screen and Final Validation

7.1. StepSummary class in src/dndrpg/ui/chargen.py: Completed.
    ```python
    class StepSummary(StepBase):
        def compose(self):
            picks = self.app_ref.cg_state.picks
            e = self.app_ref.engine.state.player  # not built yet; we will build a preview entity (dry run) or display picks
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
                self.app_ref.pop_screen(); return
            if ev.button.id == "confirm":
                build_entity_from_state(self.app_ref.engine.content, self.app_ref.engine.state, self.app_ref.cg_state.picks,
                                        self.app_ref.engine.effects, self.app_ref.engine.resources,
                                        self.app_ref.engine.conditions, self.app_ref.engine.hooks)
                self.app_ref.engine.state.mode = "exploration"
                self.app_ref.log.push("Character created. Entering exploration.")
                self.app_ref.pop_screen()
                self.app_ref.refresh_all()
    ```
7.2. Route Flow to StepSummary: Completed.
7.3. Implement Final Validation in StepSummary: Completed.

Feature 8: CLI Fallback

8.1. Create src/dndrpg/cli.py: Completed.
    ```python
    import typer, random
    from pathlib import Path
    from dndrpg.engine.engine import GameEngine
    from dndrpg.engine.chargen import CharBuildState, build_entity_from_state

    app = typer.Typer()

    @app.command()
    def new(campaign_id: str = "camp.srd_sandbox", name: str = "Hero", clazz: str = "fighter", race: str = "human"):
        eng = GameEngine()
        picks = CharBuildState(name=name, clazz=clazz, race=race)
        # minimal set
        build_entity_from_state(eng.content, eng.state, picks, eng.effects, eng.resources, eng.conditions, eng.hooks)
        for line in eng.start_new_game(campaign_id, eng.state.player, slot_id="slot1"):
            typer.echo(line)

    @app.command()
    def continue_latest():
        eng = GameEngine()
        for line in eng.continue_latest():
            typer.echo(line)

    if __name__ == "__main__":
        app()
    ```
8.2. Update pyproject.toml: Completed.
    ```toml
    [project.scripts]
    dndrpg = "dndrpg.app:run_app"
    dndrpg-cli = "dndrpg.cli:app"
    ```
8.3. Implement load and delete commands in src/dndrpg/cli.py: Completed.
8.4. Implement CLI Character Creation Wizard: Completed.

Feature 9: Damage type conversion (pipeline stage 2)

9.1. Add ActConvertType class and include it in HookAction union in src/dndrpg/engine/schema_models.py: Completed.
    ```python
    class ActConvertType(BaseModel):
        op: Literal["convertType"] = "convertType"
        to: DamageKind
    ```
9.2. Modify incoming_damage in src/dndrpg/engine/rulehooks_runtime.py: NOT Completed. (Missing 'convertType' handling.)
    ```python
        def incoming_damage(self, target_entity_id: str, damage_context: Dict[str, Any]) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            hooks = list(self._by_scope.get("incoming.damage", {}).get(target_entity_id, []))
            if not hooks:
                return result
            ctx = {"event": damage_context.get("event","incoming.damage")}
            for rh in hooks:
                if self._is_parent_suppressed(rh): continue
                if not self._match(rh, ctx): continue
                for act in rh.actions:
                    op = getattr(act, "op", None)
                    if op == "convertType":
                        result["convert"] = getattr(act, "to")
                    # keep multiply/cap/reflect handling as before
            return result
    ```
9.3. Modify DamageEngine.apply_packets in src/dndrpg/engine/damage_runtime.py: NOT Completed. (Type conversion logic is commented out/not implemented.)
    ```python
            # Stage 2: Type conversion via pre-hook
            if self.hooks:
                tr = self.hooks.incoming_damage(target_entity_id, {"event":"incoming.damage.pre"})
                conv_to = tr.get("convert")
                if conv_to:
                    for p in working:
                        p.dkind = conv_to
                    logs.append(f"[Dmg] Converted type to {conv_to} by hook")
    ```

Feature 10: Crit confirmation logic

10.1. Extend AttackGate in src/dndrpg/engine/schema_models.py: Completed.
    ```python
    class AttackGate(BaseModel):
        mode: AttackMode = "none"
        ac_type: Optional[Literal["normal","touch","flat-footed"]] = None
        crit_behavior: Optional[str] = None
        threat_range: Optional[int] = 20
        crit_mult: Optional[int] = 2

        @model_validator(mode="after")
        def _validate(self):
            # existing checks...
            if self.threat_range is not None and not (1 <= int(self.threat_range) <= 20):
                raise ValueError("threat_range must be between 1 and 20")
            if self.crit_mult is not None and int(self.crit_mult) < 2:
                raise ValueError("crit_mult must be >= 2")
            return self
    ```
10.2. Modify attack_gate in src/dndrpg/engine/gates_runtime.py: Completed.
    ```python
            thr = ag.threat_range or 20
            cmult = ag.crit_mult or default_crit_mult
            # Threat if roll >= thr
            if roll >= thr:
                confirm_roll = d20(self.rng)
                confirm_total = confirm_roll + atk_bonus
                if confirm_total >= ac_val or confirm_roll == 20:
                    crit = True
                    return AttackResult(True, True, True, cmult, ac_val, total, roll, False,
                                        f"Attack {roll}+{atk_bonus} vs AC {ac_val} -> hit; crit confirm {confirm_roll}+{atk_bonus} -> critical x{cmult}")
    ```

Feature 11: Schedule Action in Hooks

11.1. Modify src/dndrpg/engine/scheduler.py: NOT Completed. (File is empty or does not exist.)
    ```python
    from dataclasses import dataclass, field

    @dataclass
    class Scheduled:
        when_round: Optional[int] = None
        when_seconds: Optional[int] = None
        target_entity_id: str = ""
        actions: list = field(default_factory=list)  # list of Operation or HookAction

    class Scheduler:
        def __init__(self, state, effects, hooks):
            self.state = state
            self.effects = effects
            self.hooks = hooks
            self._queue: List[Scheduled] = []

        def schedule_in_rounds(self, target_entity_id: str, rounds: int, actions: list):
            self._queue.append(Scheduled(when_round=self.state.round_counter + max(1, rounds),
                                         target_entity_id=target_entity_id, actions=actions))

        def _drain_scheduled(self) -> List[str]:
            logs: List[str] = []
            now_round = self.state.round_counter
            due: List[Scheduled] = []
            keep: List[Scheduled] = []
            for s in self._queue:
                if s.when_round is not None and s.when_round <= now_round:
                    due.append(s)
                else:
                    keep.append(s)
            self._queue = keep
            # Execute due actions
            for s in due:
                for act in s.actions:
                    # Delegate to effects.executor if it's an Operation; if HookAction, we can map to Operation union or extend executor to accept it
                    # For MVP: only Operation union used here
                    self.effects.execute_operations([act], self.state.player, self.state.player, logs=logs)
            return logs

        def advance_rounds(self, n: int = 1) -> List[str]:
            logs: List[str] = []
            for _ in range(max(0, n)):
                self.state.round_counter += 1
                self.state.clock_seconds += 6
                logs += self.hooks.scheduler_event(self.state.player.id, "startOfTurn")
                logs += self._drain_scheduled()
                # ... rest unchanged ...
            return logs
    ```
11.2. Modify _exec_action in src/dndrpg/engine/rulehooks_runtime.py: NOT Completed. (Dependent on 11.1, and the `_exec_action` method does not contain the specified logic for scheduling.)
    ```python
        def _exec_action(self, action: HookAction, *, actor: Optional[Entity], target: Optional[Entity], logs: List[str]):
            op_name = getattr(action, "op", None)
            if op_name == "schedule":
                delay = getattr(action, "delay_rounds", None)
                if delay is not None and target:
                    # schedule actions (action.actions is a list[Operation])
                    self.effects.scheduler.schedule_in_rounds(target.id, int(delay), list(getattr(action, "actions", [])))
                    logs.append(f"[Hooks] scheduled {len(getattr(action, 'actions', []))} action(s) in {delay} round(s)")
                return
            # ... rest unchanged ...
    ```
11.3. Link Scheduler and EffectsEngine: NOT Completed. (Dependent on 11.1.)
    ```python
    # In GameEngine.__init__:
    self.scheduler = Scheduler(... as before ...)
    self.hooks.effects = self.effects
    self.effects.scheduler = self.scheduler  # add attribute in EffectsEngine class

    # In EffectsEngine:
    class EffectsEngine:
        def __init__(...):
            # ...
            self.scheduler = None  # type: ignore
    ```
