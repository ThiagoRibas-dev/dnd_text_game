from pathlib import Path
from dndrpg.engine.loader import load_content
from dndrpg.engine.state import default_state, GameState
from dndrpg.engine.damage_runtime import DamageEngine, DamagePacket
from dndrpg.engine.models import DREntry
from dndrpg.engine.resources_runtime import ResourceState
from dndrpg.engine.schema_models import AbsorptionSpec

def test_smoke_default_player_stats():
    content_dir = Path(__file__).resolve().parents[1] / "src" / "dndrpg" / "content"
    content = load_content(content_dir)
    state: GameState = default_state(content)
    p = state.player

    assert p.hp_max >= 1 and p.hp_current == p.hp_max
    assert isinstance(p.ac_total, int) and p.ac_total > 0
    assert isinstance(p.ac_touch, int) and p.ac_touch > 0
    assert isinstance(p.ac_ff, int) and p.ac_ff > 0
    assert p.save_fort == int(p.save_fort)
    assert p.save_ref == int(p.save_ref)
    assert p.save_will == int(p.save_will)

def test_damage_pipeline():
    content_dir = Path(__file__).resolve().parents[1] / "src" / "dndrpg" / "content"
    content = load_content(content_dir)
    state: GameState = default_state(content)
    p = state.player

    # Setup defenses
    p.dr = [DREntry(value=5, bypass_magic=True)]
    p.energy_resist = {"fire": 10}
    p.vulnerabilities = {"cold": 1.5}
    p.hp_current = 50
    p.hp_max = 50

    damage_engine = DamageEngine(content, state)

    # Test 1: Physical damage, not magic -> DR applies
    p.hp_current = 50
    packets = [DamagePacket(amount=12, dkind="physical.bludgeoning", counts_as_magic=False)]
    result = damage_engine.apply_packets(p.id, packets)
    assert p.hp_current == 50 - (12 - 5)
    assert result.physical_damage_applied == 7
    assert any("[Dmg] DR 5/- reduces total physical 12 by 5 (per attack)" in log for log in result.logs)

    # Test 2: Fire damage -> resistance applies
    p.hp_current = 50
    packets = [DamagePacket(amount=15, dkind="fire")]
    result = damage_engine.apply_packets(p.id, packets)
    assert p.hp_current == 50 - (15 - 10)
    assert any("[Dmg] Resist fire 10 → 15->5" in log for log in result.logs)

    # Test 3: Cold damage -> vulnerability applies
    p.hp_current = 50
    packets = [DamagePacket(amount=10, dkind="cold")]
    result = damage_engine.apply_packets(p.id, packets)
    assert p.hp_current == 50 - int(10 * 1.5)
    assert any("[Dmg] Vulnerability cold x1.5 → 10->15" in log for log in result.logs)

    # Test 4: Physical damage, but magic -> DR is bypassed
    p.hp_current = 50
    packets = [DamagePacket(amount=12, dkind="physical.slashing", counts_as_magic=True)]
    result = damage_engine.apply_packets(p.id, packets)
    assert p.hp_current == 50 - 12
    assert result.physical_damage_applied == 12
    assert not any("DR" in log for log in result.logs)

    # Test 5: Mixed damage
    p.hp_current = 50
    packets = [
        DamagePacket(amount=10, dkind="physical.piercing"),
        DamagePacket(amount=8, dkind="fire"),
        DamagePacket(amount=6, dkind="cold"),
    ]
    result = damage_engine.apply_packets(p.id, packets)
    # physical: 10 - 5(DR) = 5
    # fire: 8 - 10(resist) = 0
    # cold: 6 * 1.5(vuln) = 9
    # total = 5 + 0 + 9 = 14
    assert p.hp_current == 50 - 14

def test_damage_pipeline_with_temp_hp():
    content_dir = Path(__file__).resolve().parents[1] / "src" / "dndrpg" / "content"
    content = load_content(content_dir)
    state: GameState = default_state(content)
    p = state.player

    # Temp HP as a resource
    temp_hp_res = ResourceState(definition_id="res:temp_hp", name="Temporary HP", current=20, capacity=20, owner_entity_id=p.id)
    temp_hp_res.absorption = AbsorptionSpec(absorbTypes=["any"])
    state.resources[f"entity:{p.id}"] = [temp_hp_res]

    p.hp_current = 50
    p.hp_max = 50

    damage_engine = DamageEngine(content, state)

    packets = [DamagePacket(amount=30, dkind="physical.bludgeoning")]
    result = damage_engine.apply_packets(p.id, packets)

    # 20 damage absorbed by temp hp, 10 to player hp
    assert temp_hp_res.current == 0
    assert p.hp_current == 50 - 10
    assert any("[Dmg] Temporary HP absorbed 20 (0 left)" in log for log in result.logs)
