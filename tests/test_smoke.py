from pathlib import Path
from dndrpg.engine.loader import load_content
from dndrpg.engine.state import default_state, GameState

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