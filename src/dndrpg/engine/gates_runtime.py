from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
import random

from .schema_models import EffectDefinition, Gates, SaveGate, AttackGate
from .models import Entity
from .modifiers_runtime import ModifiersEngine
from .expr import eval_expr
from .dice import d20, d100

@dataclass
class SRResult:
    checked: bool
    passed: bool
    note: str

@dataclass
class SaveResult:
    attempted: bool
    succeeded: bool
    branch: Literal["negates","half","partial","none"] | None
    dc: int
    roll: int
    total: int
    save_type: Literal["Fort","Ref","Will"] | None
    note: str

@dataclass
class AttackResult:
    attempted: bool
    hit: bool
    crit: bool
    crit_mult: int
    ac_used: int
    attack_total: int
    roll: int
    concealment_miss: bool
    note: str

@dataclass
class GateOutcome:
    allowed: bool
    sr: SRResult
    save: SaveResult
    attack: AttackResult
    damage_scale: float      # 1.0 normally; 0.5 on half
    saved_flag: bool         # True when save succeeded (partial branch uses this)
    crit_mult: int           # 1 by default; x2 on crit hits

class GatesEngine:
    def __init__(self, modifiers: ModifiersEngine, rng: random.Random):
        self.modifiers = modifiers
        self.rng = rng

    # -------- SR gate --------
    def sr_gate(self, ed: EffectDefinition, source: Entity, target: Entity) -> SRResult:
        applies = bool(getattr(getattr(ed.gates or Gates(), "sr", None), "applies", False))
        if not applies:
            return SRResult(checked=False, passed=True, note="SR:N/A")
        if ed.abilityType not in ("Spell","Sp"):
            return SRResult(checked=False, passed=True, note="SR:N/A (abilityType not Spell/Sp)")
        sr_value = getattr(target, "spell_resistance", 0) or 0
        if sr_value <= 0:
            return SRResult(checked=False, passed=True, note="SR: target has none")
        # CL = caster_level() from source
        cl = int(eval_expr("caster_level()", actor=source))
        roll = d20(self.rng)
        total = roll + cl
        passed = total >= sr_value or roll == 20
        note = f"SR check d20({roll}) + CL {cl} = {total} vs SR {sr_value} → {'pass' if passed else 'fail'}"
        return SRResult(checked=True, passed=passed, note=note)

    # -------- Save gate --------
    def save_gate(self, ed: EffectDefinition, source: Entity, target: Entity) -> SaveResult:
        sg: Optional[SaveGate] = getattr(ed.gates or Gates(), "save", None)
        if not sg:
            return SaveResult(attempted=False, succeeded=False, branch=None, dc=0, roll=0, total=0, save_type=None, note="Save:N/A")
        # Compute DC
        dc_expr = getattr(sg, "dcExpression", None) or getattr(sg, "dc", None)
        dc_val = int(eval_expr(str(dc_expr), actor=source, target=target)) if isinstance(dc_expr, str) else int(dc_expr or 0)
        # Resolved save total
        stats = self.modifiers.resolved_stats(target)
        stype = sg.type  # "Fort"/"Ref"/"Will"
        save_total = {
            "Fort": stats["save_fort"],
            "Ref":  stats["save_ref"],
            "Will": stats["save_will"],
        }.get(stype, 0)
        roll = d20(self.rng)
        total = roll + save_total
        succeeded = (roll == 20) or (total >= dc_val)  # RAW: 20 auto success on saves? In 3.5, only attack rolls auto 20; saves: 20 always succeeds? No. In 3.5, a natural 1 on a save is always a failure? Actually RAW: Saving throws: a natural 1 on a saving throw is always a failure; a natural 20 is always a success. We'll adopt that.
        if roll == 1:
            succeeded = False
        branch = sg.effect or "negates"
        note = f"{stype} save d20({roll}) + {save_total} = {total} vs DC {dc_val} → {'success' if succeeded else 'fail'} ({branch})"
        return SaveResult(attempted=True, succeeded=succeeded, branch=branch, dc=dc_val, roll=roll, total=total, save_type=stype, note=note)

    # -------- Attack gate --------
    def _concealment_pct(self, source: Entity, target: Entity) -> int:
        # Very simple: if target has invisible condition → 50%; can expand with lighting later
        # Conditions are on state; ModifiersEngine can’t see tags list directly. We read target’s active conditions via modifiers.state.
        for inst in self.modifiers.state.active_conditions.get(target.id, []):
            # tags are stored on instance
            if "invisible" in (inst.tags or []):
                return 50
        return 0

    def attack_gate(self, ed: EffectDefinition, source: Entity, target: Entity, ag: AttackGate | None) -> AttackResult:
        if not ag or ag.mode == "none":
            return AttackResult(attempted=False, hit=True, crit=False, crit_mult=1, ac_used=0, attack_total=0, roll=0, concealment_miss=False, note="Attack:N/A")

        # Resolve attacker bonuses and target ACs
        sstats = self.modifiers.resolved_stats(source)
        tstats = self.modifiers.resolved_stats(target)
        # Choose AC type
        ac_type = ag.ac_type or "normal"
        ac_val = {
            "normal": tstats["ac_total"],
            "touch":  tstats["ac_touch"],
            "flat-footed": tstats["ac_ff"],
        }.get(ac_type, tstats["ac_total"])
        # Choose attack bonus by mode
        if ag.mode in ("melee","melee_touch"):
            atk_bonus = sstats["attack_melee_bonus"]
            default_crit_mult = 2
        elif ag.mode in ("ranged","ranged_touch","ray"):
            atk_bonus = sstats["attack_ranged_bonus"]
            default_crit_mult = 2
        else:
            atk_bonus = sstats["attack_melee_bonus"]
            default_crit_mult = 2

        # Attack roll
        roll = d20(self.rng)
        total = roll + atk_bonus

        # Auto miss/hit policy: natural 1 misses, natural 20 hits (threat)
        if roll == 1:
            return AttackResult(True, False, False, default_crit_mult, ac_val, total, roll, False, f"Attack d20({roll}) + {atk_bonus} vs AC {ac_val} → auto miss")

        # Concealment
        conceal_pct = self._concealment_pct(source, target)
        if conceal_pct > 0:
            miss_roll = d100(self.rng)
            if miss_roll <= conceal_pct:
                return AttackResult(True, False, False, default_crit_mult, ac_val, total, roll, True, f"Attack d20({roll}) + {atk_bonus} vs AC {ac_val} → concealment {conceal_pct}% miss (roll {miss_roll})")

        # Hit check
        hit = (total >= ac_val) or (roll == 20)
        if not hit:
            return AttackResult(True, False, False, default_crit_mult, ac_val, total, roll, False, f"Attack d20({roll}) + {atk_bonus} vs AC {ac_val} → miss")

        # Threat/confirm (use 20 threat range default; use ×2 multiplier)
        if roll == 20 or False:
            # Confirm
            confirm_roll = d20(self.rng)
            confirm_total = confirm_roll + atk_bonus
            if confirm_total >= ac_val or confirm_roll == 20:
                return AttackResult(True, True, True, default_crit_mult, ac_val, total, roll, False, f"Attack {roll}+{atk_bonus} vs AC {ac_val} → hit; crit confirm {confirm_roll}+{atk_bonus} → critical x{default_crit_mult}")
        return AttackResult(True, True, False, default_crit_mult, ac_val, total, roll, False, f"Attack {roll}+{atk_bonus} vs AC {ac_val} → hit")

    # -------- Top-level evaluator --------
    def evaluate(self, ed: EffectDefinition, source: Entity, target: Entity) -> Tuple[GateOutcome, list[str]]:
        logs: list[str] = []
        sr = self.sr_gate(ed, source, target)
        logs.append(sr.note)
        if not sr.passed:
            return GateOutcome(False, sr, SaveResult(False, False, None, 0, 0, 0, None, ""), AttackResult(False, False, False, 1, 0, 0, 0, False, ""), 1.0, False, 1), logs

        sv = self.save_gate(ed, source, target)
        if sv.attempted:
            logs.append(sv.note)

        # Apply save branch policy
        damage_scale = 1.0
        saved_flag = False
        allowed_after_save = True
        if sv.attempted:
            if sv.branch == "negates":
                allowed_after_save = not sv.succeeded
            elif sv.branch == "half":
                damage_scale = 0.5 if sv.succeeded else 1.0
                saved_flag = sv.succeeded
            elif sv.branch == "partial":
                # Author content should model partial via inline save ops; pass a flag
                saved_flag = sv.succeeded
                allowed_after_save = True
            elif sv.branch == "none":
                allowed_after_save = True

        if not allowed_after_save:
            return GateOutcome(False, sr, sv, AttackResult(False, False, False, 1, 0, 0, 0, False, ""), damage_scale, saved_flag, 1), logs

        ag = getattr(ed.gates or Gates(), "attack", None)
        atk = self.attack_gate(ed, source, target, ag)
        if atk.attempted:
            logs.append(atk.note)
        if atk.attempted and not atk.hit:
            return GateOutcome(False, sr, sv, atk, damage_scale, saved_flag, 1), logs

        crit_mult = atk.crit_mult if atk.crit else 1
        return GateOutcome(True, sr, sv, atk, damage_scale, saved_flag, crit_mult), logs
