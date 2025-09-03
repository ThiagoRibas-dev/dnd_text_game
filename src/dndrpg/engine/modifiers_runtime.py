from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from .schema_models import Modifier
from .loader import ContentIndex
from .models import Entity
from .expr import eval_expr
if TYPE_CHECKING:
    from .state import GameState

# Typed bonus stacking policy
TYPED_NO_STACK_HIGHEST = {
    "enhancement","morale","luck","insight","competence","sacred","profane",
    "resistance","deflection","size","natural_armor","natural_armor_enhancement",
    "circumstance","alchemical"
}
TYPED_STACK = {"dodge"}  # only dodge stacks by itself

@dataclass
class EvaluatedMod:
    operator: str
    value: float
    bonusType: Optional[str]
    sourceKey: Optional[str]
    # provenance (debug/explain)
    source_kind: str  # "effect" or "condition"
    source_id: str
    source_name: str

class ModifiersEngine:
    """
    Collects and applies modifiers with 3.5e stacking rules and operator ordering.
    This engine does not mutate Entity; it computes effective values on demand.
    """

    def __init__(self, content: ContentIndex, state: "GameState"):
        self.content = content
        self.state = state

    # -------- helper: entity lookup --------
    def _entity_by_id(self, ent_id: str) -> Optional[Entity]:
        # For now only player; extend when you track NPCs by id
        if ent_id == self.state.player.id:
            return self.state.player
        return None

    # -------- collect modifiers for an entity --------
    def collect_for_entity(self, entity_id: str) -> Dict[str, List[EvaluatedMod]]:
        out: Dict[str, List[EvaluatedMod]] = {}
        # Effects
        for inst in self.state.active_effects.get(entity_id, []):
            if getattr(inst, "suppressed", False):
                continue
            ed = self.content.effects.get(inst.definition_id)
            if not ed: 
                continue
            src = self._entity_by_id(inst.source_entity_id) or self._entity_by_id(entity_id)  # fallback
            tgt = self._entity_by_id(entity_id)
            for m in (ed.modifiers or []):
                em = self._eval_modifier(m, actor=src, target=tgt, source_kind="effect", source_id=ed.id, source_name=ed.name)
                if em:
                    out.setdefault(m.targetPath, []).append(em)
        # Conditions
        for inst in self.state.active_conditions.get(entity_id, []):
            cd = self.content.conditions.get(inst.definition_id)
            if not cd:
                continue
            src = self._entity_by_id(inst.source_entity_id) or self._entity_by_id(entity_id)
            tgt = self._entity_by_id(entity_id)
            for m in (cd.modifiers or []):
                em = self._eval_modifier(m, actor=src, target=tgt, source_kind="condition", source_id=cd.id, source_name=cd.name)
                if em:
                    out.setdefault(m.targetPath, []).append(em)
        return out

    def _eval_modifier(self, m: Modifier, *, actor: Optional[Entity], target: Optional[Entity], source_kind: str, source_id: str, source_name: str) -> Optional[EvaluatedMod]:
        # value can be numeric or expr (string/dict -> expr string)
        val_raw = m.value
        try:
            if isinstance(val_raw, (int, float)):
                val = float(val_raw)
            elif isinstance(val_raw, str):
                v = eval_expr(val_raw, actor=actor, target=target)
                val = float(v) if isinstance(v, (int, float)) else 0.0
            elif isinstance(val_raw, dict) and "expr" in val_raw:
                v = eval_expr(str(val_raw["expr"]), actor=actor, target=target)
                val = float(v) if isinstance(v, (int, float)) else 0.0
            else:
                # allow dict or other shapes in future; default 0
                val = 0.0
        except Exception:
            val = 0.0
        return EvaluatedMod(
            operator=m.operator,
            value=val,
            bonusType=m.bonusType,
            sourceKey=m.sourceKey,
            source_kind=source_kind,
            source_id=source_id,
            source_name=source_name
        )

    # -------- apply stacking and operator ordering --------
    def apply_to_value(self, base: float, mods: List[EvaluatedMod]) -> float:
        if not mods:
            return base

        # 1) set/replace
        current = base
        for em in mods:
            if em.operator in ("set", "replace"):
                current = em.value

        # 2) add/sub with stacking by bonusType
        # group by bonusType
        by_type: Dict[str, List[EvaluatedMod]] = {}
        untyped: List[EvaluatedMod] = []
        for em in mods:
            if em.operator not in ("add", "subtract"):
                continue
            if em.bonusType:
                by_type.setdefault(em.bonusType, []).append(em)
            else:
                untyped.append(em)

        # typed: sum only highest per type (except dodge stacks)
        typed_total = 0.0
        for btype, lst in by_type.items():
            if btype in TYPED_STACK:
                # sum all adds/subs
                typed_total += sum((em.value if em.operator == "add" else -em.value) for em in lst)
            else:
                # take highest magnitude in absolute add (subtract treated as negative)
                vals = [(em.value if em.operator == "add" else -em.value) for em in lst]
                typed_total += max(vals) if vals else 0.0

        # untyped: stack, but same sourceKey does not stack (take highest per sourceKey)
        by_source: Dict[Optional[str], List[EvaluatedMod]] = {}
        for em in untyped:
            by_source.setdefault(em.sourceKey, []).append(em)
        untyped_total = 0.0
        for skey, lst in by_source.items():
            # choose sum of all when different sourceKey (already grouped), within a key choose highest delta
            vals = [(em.value if em.operator == "add" else -em.value) for em in lst]
            if skey is None:
                untyped_total += sum(vals)
            else:
                # same source: take highest delta
                untyped_total += max(vals) if vals else 0.0

        current += typed_total + untyped_total

        # 3) multiply/divide (apply multiplicatively; collect a single factor)
        factor = 1.0
        for em in mods:
            if em.operator == "multiply":
                factor *= em.value
            elif em.operator == "divide":
                if em.value != 0:
                    factor *= (1.0 / em.value)
        current *= factor

        # 4) min/max
        min_bound: Optional[float] = None
        max_bound: Optional[float] = None
        for em in mods:
            if em.operator == "min":
                min_bound = em.value if min_bound is None else max(min_bound, em.value)
            elif em.operator == "max":
                max_bound = em.value if max_bound is None else min(max_bound, em.value)
        if min_bound is not None:
            current = max(current, min_bound)
        if max_bound is not None:
            current = min(current, max_bound)

        # 5) cap/clamp (treat both as a simple upper cap for now)
        for em in mods:
            if em.operator in ("cap", "clamp"):
                current = min(current, em.value)

        return current

    # -------- resolved stats view --------
    def resolved_ability_scores(self, entity: Entity) -> Dict[str, int]:
        # base scores
        base_scores = {
            "str": entity.abilities.str_.score(),
            "dex": entity.abilities.dex.score(),
            "con": entity.abilities.con.score(),
            "int": entity.abilities.int_.score(),
            "wis": entity.abilities.wis.score(),
            "cha": entity.abilities.cha.score(),
        }
        all_mods = self.collect_for_entity(entity.id)
        eff: Dict[str, int] = {}
        for ab in ("str","dex","con","int","wis","cha"):
            path_prefix = f"abilities.{ab}"
            # Take any modifiers targeting abilities.ab.* and fold them into a delta to the score
            # We allow two modes: authors can target abilities.ab (directly) or abilities.ab.enhancement/etc.
            # Collect mods for any path that starts with the prefix
            relevant: List[EvaluatedMod] = []
            for path, mods in all_mods.items():
                if path == path_prefix or path.startswith(path_prefix + "."):
                    relevant += mods
            eff_val = int(round(self.apply_to_value(float(base_scores[ab]), relevant)))
            # clamp to >= 0
            eff[ab] = max(0, eff_val)
        return eff

    def resolved_stats(self, entity: Entity) -> Dict[str, Any]:
        """
        Compute effective stats for display/use:
        - ability mods
        - AC total/touch/flat-footed (base + path modifiers)
        - Saves
        - Melee/Ranged attack bonuses
        - Speed (land)
        """
        all_mods = self.collect_for_entity(entity.id)
        eff_abilities = self.resolved_ability_scores(entity)
        mod = {k: (v - 10) // 2 for k, v in eff_abilities.items()}

        # Base armor/shield and Dex cap from armor
        armor = entity.equipped_armor()
        shield = entity.equipped_shield()
        armor_bonus = armor.effective_armor_bonus if armor else 0
        shield_bonus = shield.effective_shield_bonus if shield else 0
        dex_cap = armor.max_dex_bonus if (armor and armor.max_dex_bonus is not None) else 99
        size_mod = (0 if entity.size.value == "Medium" else 0)  # you already have SIZE_TO_MOD; but avoid import cycle

        # Pull size mod via entity method (safer)
        try:
            size_mod = entity._size_mod()
        except Exception:
            size_mod = 0

        # Natural armor, deflection, dodge via modifiers (we also allow “ac.*” mods)
        natural = 0.0
        deflection = 0.0
        dodge = 0.0
        misc_ac = 0.0

        # Apply ac.component modifiers into a temp current 0 base (then add to total)
        def apply_ac_component(path_suffix: str) -> float:
            mods = all_mods.get(f"ac.{path_suffix}", [])
            return self.apply_to_value(0.0, mods)

        natural += apply_ac_component("natural")
        deflection += apply_ac_component("deflection")
        dodge += apply_ac_component("dodge")
        misc_ac += apply_ac_component("misc")

        # AC totals before “ac.total” modifiers
        dex_used = min(mod["dex"], dex_cap)
        ac_base_total = 10 + armor_bonus + shield_bonus + dex_used + size_mod + natural + deflection + dodge + misc_ac

        # Now apply ac.total modifiers to the total
        ac_total = self.apply_to_value(float(ac_base_total), all_mods.get("ac.total", []))
        # Touch AC: ignore armor, shield, natural
        ac_touch_base = 10 + dex_used + size_mod + deflection + dodge + misc_ac
        ac_touch = self.apply_to_value(float(ac_touch_base), all_mods.get("ac.touch", []))
        # Flat-footed: no Dex, no dodge
        ac_ff_base = 10 + armor_bonus + shield_bonus + size_mod + natural + deflection + misc_ac
        ac_ff = self.apply_to_value(float(ac_ff_base), all_mods.get("ac.flat_footed", []))

        # Saves base
        base_fort = entity.base_fort + mod["con"]
        base_ref = entity.base_ref + mod["dex"]
        base_will = entity.base_will + mod["wis"]
        save_fort = int(round(self.apply_to_value(float(base_fort), all_mods.get("save.fort", []))))
        save_ref = int(round(self.apply_to_value(float(base_ref), all_mods.get("save.ref", []))))
        save_will = int(round(self.apply_to_value(float(base_will), all_mods.get("save.will", []))))

        # Effective BAB (max with modifier if any)
        eff_bab = entity.base_attack_bonus
        if "attack.bab.effective" in all_mods:
            eff_bab = int(round(self.apply_to_value(float(eff_bab), all_mods["attack.bab.effective"])))

        # Attacks
        melee_base = eff_bab + mod["str"] + size_mod + (entity.equipped_main_weapon().enhancement_bonus if entity.equipped_main_weapon() else 0)
        ranged_base = eff_bab + mod["dex"] + size_mod + (entity.equipped_ranged_weapon().enhancement_bonus if entity.equipped_ranged_weapon() else 0)
        attack_melee = int(round(self.apply_to_value(float(melee_base), all_mods.get("attack.melee.bonus", []))))
        attack_ranged = int(round(self.apply_to_value(float(ranged_base), all_mods.get("attack.ranged.bonus", []))))

        # Speed (land)
        speed_base = entity.speed_land
        speed_land = int(round(self.apply_to_value(float(speed_base), all_mods.get("speed.land", []))))

        return {
            "abilities": eff_abilities,
            "mods": mod,
            "ac_total": int(round(ac_total)),
            "ac_touch": int(round(ac_touch)),
            "ac_ff": int(round(ac_ff)),
            "save_fort": save_fort,
            "save_ref": save_ref,
            "save_will": save_will,
            "attack_melee_bonus": attack_melee,
            "attack_ranged_bonus": attack_ranged,
            "speed_land": speed_land,
        }

    def apply_with_trace(self, base: float, mods: List[EvaluatedMod]) -> tuple[float, list[str]]:
        lines: list[str] = []
        current = base
        # set/replace
        for em in mods:
            if em.operator in ("set","replace"):
                lines.append(f'  set -> {em.value} from {em.source_name} [{em.source_kind}]')
                current = em.value
        # add/sub
        by_type: Dict[str, List[EvaluatedMod]] = {}
        untyped: List[EvaluatedMod] = []
        for em in mods:
            if em.operator not in ("add","subtract"): 
                continue
            if em.bonusType: 
                by_type.setdefault(em.bonusType, []).append(em)
            else: 
                untyped.append(em)
        # typed
        add_total = 0.0
        for btype, lst in by_type.items():
            if btype in TYPED_STACK:
                delta = sum((em.value if em.operator=='add' else -em.value) for em in lst)
                add_total += delta
                for em in lst:
                    lines.append(f'  {btype} {"+" if em.operator=="add" else ""}{em.value} from {em.source_name} [stack]')
            else:
                vals = [(em.value if em.operator=='add' else -em.value, em) for em in lst]
                if not vals: 
                    continue
                best_val, best_em = max(vals, key=lambda t: t[0])
                add_total += best_val
                # show all contenders; mark chosen
                for v, em in vals:
                    tag = " (chosen)" if v == best_val else ""
                    lines.append(f'  {btype} {"+" if em.operator=="add" else ""}{em.value} from {em.source_name}{tag}')
        # untyped (same-sourceKey no-stack)
        by_source: Dict[Optional[str], List[EvaluatedMod]] = {}
        for em in untyped:
            by_source.setdefault(em.sourceKey, []).append(em)
        for skey, lst in by_source.items():
            if skey is None:
                s = sum((em.value if em.operator=='add' else -em.value) for em in lst)
                add_total += s
                for em in lst:
                    lines.append(f'  untyped {"+" if em.operator=="add" else ""}{em.value} from {em.source_name}')
            else:
                vals = [(em.value if em.operator=='add' else -em.value, em) for em in lst]
                best_val, best_em = max(vals, key=lambda t: t[0])
                add_total += best_val
                for v, em in vals:
                    tag = " (chosen same-source)" if v == best_val else " (same-source dropped)"
                    lines.append(f'  untyped {"+" if em.operator=="add" else ""}{em.value} from {em.source_name}{tag}')
        current += add_total

        # multiply/divide
        factor = 1.0
        for em in mods:
            if em.operator == "multiply": 
                factor *= em.value
            elif em.operator == "divide" and em.value != 0: 
                factor *= (1.0/em.value)
        if factor != 1.0:
            lines.append(f"  × {factor}")
        current *= factor

        # min/max
        minb = None
        maxb = None
        for em in mods:
            if em.operator == "min": 
                minb = em.value if minb is None else max(minb, em.value)
            elif em.operator == "max": 
                maxb = em.value if maxb is None else min(maxb, em.value)
        if minb is not None: 
            lines.append(f"  min {minb}")
        if maxb is not None: 
            lines.append(f"  max {maxb}")
        if minb is not None: 
            current = max(current, minb)
        if maxb is not None: 
            current = min(current, maxb)

        # cap/clamp
        for em in mods:
            if em.operator in ("cap","clamp"):
                lines.append(f"  cap {em.value}")
                current = min(current, em.value)
        return current, lines

    def explain_paths(self, entity: Entity, paths: list[str]) -> list[str]:
        lines: list[str] = []
        all_mods = self.collect_for_entity(entity.id)
        for path in paths:
            mods = all_mods.get(path, [])
            if not mods:
                continue
            base = 0.0
            if path == "ac.natural":
                base = entity.natural_armor
            # other bases 0 for additive components
            final, plines = self.apply_with_trace(base, mods)
            lines.append(f"{path}: base {base} -> {int(round(final))}")
            lines.extend(plines)
        return lines

    def diff_stats(self, before: dict, after: dict) -> list[str]:
        # show diffs for abilities, ac_total, saves, attacks, speed
        interesting = [
            ("STR", "abilities['str']"),
            ("DEX","abilities['dex']"),
            ("CON","abilities['con']"),
            ("INT","abilities['int']"),
            ("WIS","abilities['wis']"),
            ("CHA","abilities['cha']"),
            ("AC", "ac_total"),
            ("Touch", "ac_touch"),
            ("FF", "ac_ff"),
            ("Fort","save_fort"),
            ("Ref","save_ref"),
            ("Will","save_will"),
            ("Melee","+attack_melee_bonus"),
            ("Ranged","+attack_ranged_bonus"),
            ("Speed","speed_land"),
        ]
        lines = ["[Stacking] Resolved stat changes:"]
        
        def get_value(data, key_str):
            if "abilities" in key_str:
                ability = key_str.split("'")[1]
                return data["abilities"][ability]
            else:
                return data[key_str.strip('+')]

        for label, key in interesting:
            val_b = get_value(before, key)
            val_a = get_value(after, key)
            if val_a != val_b:
                if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                    diff = val_a - val_b
                    sign = "+" if diff > 0 else ""
                    lines.append(f'  {label}: {val_b} -> {val_a} ({sign}{diff})')
                else:
                    lines.append(f'  {label}: {val_b} -> {val_a}')

        if len(lines) == 1:
            lines.append("  (no changes)")
        return lines