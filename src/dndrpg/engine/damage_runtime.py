from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Literal, Tuple, TYPE_CHECKING
from .models import Entity, DREntry, DamageKind
from .loader import ContentIndex
from .rulehooks_runtime import RuleHooksRegistry

if TYPE_CHECKING:
    from .state import GameState
    from .resources_runtime import ResourceState

@dataclass
class DamagePacket:
    amount: int
    dkind: DamageKind
    counts_as_magic: bool = False
    counts_as_material: Optional[List[Literal["adamantine","silver","cold-iron"]]] = None
    counts_as_alignment: Optional[List[Literal["good","evil","law","chaos"]]] = None

@dataclass
class AttackContext:
    # For DR policy, treat all packets in one call as a single attack
    source_entity_id: Optional[str] = None
    note: str = ""

@dataclass
class PipelineResult:
    total_hp_damage: int
    total_nonlethal: int
    physical_damage_applied: int      # sum of physical damage that actually hit HP (post DR/resist/pools/vuln)
    logs: List[str]

class DamageEngine:
    """
    Full pipeline:
      1) Immunity
      2) Type conversion (pre-hook)
      3) Resist/DR/ablative pools
         - DR policy: apply to total physical damage per attack (combine all non-bypassed physical packets)
         - Energy resist per packet
         - Pools applied after DR (temp HP modeled via absorption.any)
      4) Vulnerability (per packet)
      5) Apply to HP / Nonlethal
      6) Injury rider negation signal (physical_damage_applied == 0)
      7) Post hooks (triggers only)
    """

    def __init__(self, content: ContentIndex, state: "GameState", hooks: Optional[RuleHooksRegistry] = None):
        self.content = content
        self.state = state
        self.hooks = hooks

    # ------- helpers -------
    def _entity_by_id(self, ent_id: str | None) -> Optional[Entity]:
        if not ent_id:
            return None
        if self.state.player.id == ent_id:
            return self.state.player
        return None

    def _find_absorbers(self, entity_id: str, dkind: DamageKind) -> List["ResourceState"]:
        matches: List[ResourceState] = []
        key_ent = f"entity:{entity_id}"
        for rs in self.state.resources.get(key_ent, []):
            if rs.absorption and self._absorption_matches(rs, dkind):
                matches.append(rs)
        for key, lst in self.state.resources.items():
            if not key.startswith("effect:"):
                continue
            for rs in lst:
                if rs.owner_entity_id == entity_id and rs.absorption and self._absorption_matches(rs, dkind):
                    matches.append(rs)
        return matches

    def _absorption_matches(self, rs: "ResourceState", dkind: DamageKind) -> bool:
        if not rs.absorption:
            return False
        types = set(rs.absorption.absorbTypes or [])
        if "any" in types:
            return True
        if "physical" in types and dkind.startswith("physical."):
            return True
        return dkind in types

    def _dr_applies(self, dr: DREntry, pkt: DamagePacket) -> bool:
        # True if this DR entry applies to the packet (i.e., not bypassed)
        if pkt.counts_as_magic and dr.bypass_magic:
            return False
        if dr.bypass_materials:
            if pkt.counts_as_material and any(m in dr.bypass_materials for m in pkt.counts_as_material):
                return False
        if dr.bypass_alignments:
            if pkt.counts_as_alignment and any(a in dr.bypass_alignments for a in pkt.counts_as_alignment):
                return False
        if dr.bypass_weapon_types:
            # If packet is physical of type matching bypass weapon types (slashing, etc.) treat as bypass
            # We have pkt.dkind like "physical.slashing" | "...piercing" | "...bludgeoning"
            tail = pkt.dkind.split(".")[-1] if pkt.dkind.startswith("physical.") else ""
            if tail and tail in dr.bypass_weapon_types:
                return False
        return True

    # ------- pipeline -------
    def apply_packets(self, target_entity_id: str, packets: List[DamagePacket], *, ctx: Optional[AttackContext] = None) -> PipelineResult:
        logs: List[str] = []
        ent = self._entity_by_id(target_entity_id)
        if not ent:
            logs.append("[Dmg] unknown target")
            return PipelineResult(0,0,0,logs)
        # Stage 1: Immunity
        working: List[DamagePacket] = []
        for p in packets:
            if p.dkind in ent.immunities:
                logs.append(f"[Dmg] Immune to {p.dkind} (ignored {p.amount})")
                continue
            working.append(DamagePacket(amount=max(0,int(p.amount)),
                                        dkind=p.dkind,
                                        counts_as_magic=p.counts_as_magic,
                                        counts_as_material=p.counts_as_material,
                                        counts_as_alignment=p.counts_as_alignment))
        if not working:
            return PipelineResult(0,0,0,logs)

        # Stage 2: Type conversion via pre-hook (optional)
        if self.hooks:
            self.hooks.incoming_damage(target_entity_id, {"event":"incoming.damage.pre"})
            # If a conversion is requested
            # conv = tr.get("convert") if isinstance(tr, dict) else None  # only if you added convert in hooks
            # We’ll accept an inline "convert" mapping: {"from":"fire","to":"cold"} — optional future
            # For now, skip unless explicitly implemented in hooks

        # Stage 3: Resist / DR / Ablative pools
        # 3.1 Energy resistance per packet
        for p in working:
            resist = int(ent.energy_resist.get(p.dkind, 0) or 0)
            if resist > 0 and p.amount > 0:
                reduced = max(0, p.amount - resist)
                if reduced != p.amount:
                    logs.append(f"[Dmg] Resist {p.dkind} {resist} → {p.amount}->{reduced}")
                    p.amount = reduced

        # 3.2 DR per attack total (physical only; non-bypassed)
        # Collect DR entries and compute total physical amount subject to DR
        phys_indices = [i for i, pkt in enumerate(working) if pkt.dkind.startswith("physical.") and pkt.amount > 0]
        if phys_indices and ent.dr:
            # Choose the best DR entry (highest value) that applies to this attack’s packets
            # RAW: one DR value applies; we take the single best DR among the ones that are not bypassed by all packets.
            applicable_dr_values: List[Tuple[int,DREntry]] = []
            for dr in ent.dr:
                # If at least one packet would be reduced by this DR (i.e., not bypassed), consider it
                any_applies = any(self._dr_applies(dr, working[i]) for i in phys_indices)
                if any_applies:
                    applicable_dr_values.append((dr.value, dr))
            if applicable_dr_values:
                best_value, best_dr = max(applicable_dr_values, key=lambda x: x[0])
                # Compute sum of amounts of packets for which DR applies
                sum_subject = sum(working[i].amount for i in phys_indices if self._dr_applies(best_dr, working[i]))
                if sum_subject > 0 and best_value > 0:
                    dr_amount = min(best_value, sum_subject)
                    logs.append(f"[Dmg] DR {best_value}/- reduces total physical {sum_subject} by {dr_amount} (per attack)")
                    # Reduce packets in order until DR is consumed
                    remaining_dr = dr_amount
                    for i in phys_indices:
                        if remaining_dr <= 0:
                            break
                        pkt = working[i]
                        if not self._dr_applies(best_dr, pkt) or pkt.amount <= 0:
                            continue
                        take = min(pkt.amount, remaining_dr)
                        pkt.amount -= take
                        remaining_dr -= take

        # 3.3 Ablative pools (temp HP, Stoneskin-like) after DR
        # Absorption per packet with absorbPerHit cap
        for p in working:
            if p.amount <= 0:
                continue
            absorbers = self._find_absorbers(target_entity_id, p.dkind)
            for rs in absorbers:
                if p.amount <= 0:
                    break
                per_hit_cap = rs.absorption.absorbPerHit if rs.absorption else None
                can = rs.current
                if per_hit_cap is not None:
                    can = min(can, per_hit_cap)
                take = min(can, p.amount)
                if take > 0:
                    rs.current -= take
                    p.amount -= take
                    logs.append(f"[Dmg] {rs.name or rs.definition_id} absorbed {take} ({rs.current} left)")

        # Stage 4: Vulnerability (multiply)
        for p in working:
            if p.amount <= 0:
                continue
            v = float(ent.vulnerabilities.get(p.dkind, 1.0) or 1.0)
            if v != 1.0:
                new_amt = int(max(0, round(p.amount * v)))
                if new_amt != p.amount:
                    logs.append(f"[Dmg] Vulnerability {p.dkind} x{v} → {p.amount}->{new_amt}")
                    p.amount = new_amt

        # Stage 5: Apply to HP / Nonlethal
        total_hp = 0
        total_nl = 0
        for p in working:
            if p.amount <= 0:
                continue
            if p.dkind == "nonlethal":
                # Nonlethal: stored separately
                ent.nonlethal_damage = max(0, ent.nonlethal_damage + p.amount)
                total_nl += p.amount
                logs.append(f"[Dmg] +{p.amount} nonlethal (total NL {ent.nonlethal_damage})")
            else:
                before = ent.hp_current
                ent.hp_current = max(0, ent.hp_current - p.amount)
                dealt = before - ent.hp_current
                total_hp += dealt
                logs.append(f"[Dmg] {p.dkind} +{dealt} (HP {ent.hp_current}/{ent.hp_max})")

        # Stage 6: Injury-rider negation signal
        physical_applied = sum(p.amount for p in working if p.dkind.startswith("physical."))

        # Stage 7: Post hooks (triggers only; no transforms here yet)
        if self.hooks:
            _ = self.hooks.incoming_damage(target_entity_id, {"event": "incoming.damage.post"})

        return PipelineResult(total_hp_damage=total_hp, total_nonlethal=total_nl, physical_damage_applied=physical_applied, logs=logs)
