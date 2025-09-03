import pytest
from pydantic import ValidationError
from dndrpg.engine.schema_models import ResourceDefinition, CapacitySpec, ResourceRefresh, AbsorptionSpec
from dndrpg.engine.resources_runtime import ResourceEngine
from dndrpg.engine.models import Entity
from dndrpg.engine.loader import ContentIndex
from dndrpg.engine.state import GameState

# Mock ContentIndex and GameState for testing
@pytest.fixture
def mock_content_index():
    return ContentIndex(
        items_by_id={},
        weapons={},
        armors={},
        shields={},
        campaigns={},
        kits={},
        effects={},
        resources={
            "test_resource_level_capacity": ResourceDefinition(
                id="test_resource_level_capacity",
                name="Level Capacity Resource",
                scope="entity",
                capacity=CapacitySpec(formula="level * 5")
            ),
            "test_resource_fixed_capacity": ResourceDefinition(
                id="test_resource_fixed_capacity",
                name="Fixed Capacity Resource",
                scope="entity",
                capacity=CapacitySpec(formula="10")
            ),
            "test_resource_capped_capacity": ResourceDefinition(
                id="test_resource_capped_capacity",
                name="Capped Capacity Resource",
                scope="entity",
                capacity=CapacitySpec(formula="level * 10", cap=20)
            ),
            "test_resource_refresh_reset": ResourceDefinition(
                id="test_resource_refresh_reset",
                name="Refresh Reset Resource",
                scope="entity",
                capacity=CapacitySpec(formula="10"),
                initial_current=5,
                refresh=ResourceRefresh(cadence="per_round", behavior="reset_to_max")
            ),
            "test_resource_refresh_increment": ResourceDefinition(
                id="test_resource_refresh_increment",
                name="Refresh Increment Resource",
                scope="entity",
                capacity=CapacitySpec(formula="10"),
                initial_current=5,
                refresh=ResourceRefresh(cadence="per_round", behavior="increment_by", increment_by="1")
            ),
            "test_resource_refresh_increment_formula": ResourceDefinition(
                id="test_resource_refresh_increment_formula",
                name="Refresh Increment Formula Resource",
                scope="entity",
                capacity=CapacitySpec(formula="level * 2"),
                refresh=ResourceRefresh(cadence="per_round", behavior="increment_by", increment_by="level / 2")
            ),
        },
        conditions={},
        deities={},
        zones={}
    )

@pytest.fixture
def mock_game_state(mock_content_index):
    player_entity = Entity(id="player1", name="Test Player", level=5)
    gs = GameState(
        player=player_entity,
        npcs=[],
        round_counter=0,
        resources={},
        mode="exploration",
        clock_seconds=0.0,
        rng_seed=123
    )
    return gs

@pytest.fixture
def resource_engine(mock_content_index, mock_game_state):
    return ResourceEngine(mock_content_index, mock_game_state)

# --- ResourceDefinition Schema Tests ---

def test_resource_definition_valid():
    rd = ResourceDefinition(
        id="hp",
        name="Hit Points",
        scope="entity",
        capacity=CapacitySpec(formula="level * 10 + con_mod"),
        initial_current="capacity",
        refresh=ResourceRefresh(cadence="per_day", behavior="reset_to_max"),
        absorption=AbsorptionSpec(absorbTypes=["physical"])
    )
    assert rd.id == "hp"
    assert rd.capacity.formula == "level * 10 + con_mod"
    assert rd.refresh.cadence == "per_day"

def test_resource_definition_invalid_capacity_cap():
    with pytest.raises(ValidationError, match="capacity.cap must be >= 0"):
        ResourceDefinition(
            id="invalid_cap",
            name="Invalid Cap",
            scope="entity",
            capacity=CapacitySpec(formula="10", cap=-5)
        )

def test_resource_definition_invalid_refresh_increment_by_missing():
    with pytest.raises(ValidationError, match="refresh.behavior 'increment_by' requires increment_by"):
        ResourceDefinition(
            id="invalid_refresh",
            name="Invalid Refresh",
            scope="entity",
            capacity=CapacitySpec(formula="10"),
            refresh=ResourceRefresh(cadence="per_round", behavior="increment_by")
        )

def test_resource_definition_invalid_absorption_types_empty():
    with pytest.raises(ValidationError, match="absorption.absorbTypes must be a non-empty list"):
        ResourceDefinition(
            id="invalid_absorb",
            name="Invalid Absorb",
            scope="entity",
            capacity=CapacitySpec(formula="10"),
            absorption=AbsorptionSpec(absorbTypes=[])
        )

# --- ResourceEngine Functionality Tests ---

def test_resource_engine_create_from_definition_level_capacity(resource_engine, mock_game_state):
    rs, logs = resource_engine.create_from_definition(
        "test_resource_level_capacity",
        owner_scope="entity",
        owner_entity_id="player1"
    )
    assert rs is not None
    assert rs.definition_id == "test_resource_level_capacity"
    assert rs.owner_entity_id == "player1"
    # Player level is 5, formula is level * 5 = 25
    assert rs.max_computed == 25
    assert rs.current == 25 # initial_current defaults to max_computed

def test_resource_engine_create_from_definition_fixed_capacity(resource_engine, mock_game_state):
    rs, logs = resource_engine.create_from_definition(
        "test_resource_fixed_capacity",
        owner_scope="entity",
        owner_entity_id="player1"
    )
    assert rs is not None
    assert rs.max_computed == 10
    assert rs.current == 10

def test_resource_engine_create_from_definition_capped_capacity(resource_engine, mock_game_state):
    rs, logs = resource_engine.create_from_definition(
        "test_resource_capped_capacity",
        owner_scope="entity",
        owner_entity_id="player1"
    )
    assert rs is not None
    # Player level is 5, formula is level * 10 = 50, cap is 20
    assert rs.max_computed == 20
    assert rs.current == 20

def test_resource_engine_refresh_cadence_reset_to_max(resource_engine, mock_game_state):
    rs, logs = resource_engine.create_from_definition(
        "test_resource_refresh_reset",
        owner_scope="entity",
        owner_entity_id="player1"
    )
    assert rs.current == 5 # initial_current set to 5 in definition
    rs.current = 2 # Simulate resource being spent
    assert rs.current == 2

    resource_engine.refresh_cadence("per_round")
    assert rs.current == rs.max_computed # Should reset to max (10)

def test_resource_engine_refresh_cadence_increment_by(resource_engine, mock_game_state):
    rs, logs = resource_engine.create_from_definition(
        "test_resource_refresh_increment",
        owner_scope="entity",
        owner_entity_id="player1"
    )
    assert rs.current == 5 # initial_current set to 5 in definition
    rs.current = 2 # Simulate resource being spent
    assert rs.current == 2

    resource_engine.refresh_cadence("per_round")
    # Should increment by 1 (from definition)
    assert rs.current == 3 # 2 + 1

    resource_engine.refresh_cadence("per_round")
    assert rs.current == 4 # 3 + 1

def test_resource_engine_refresh_cadence_increment_by_formula(resource_engine, mock_game_state):
    rs, logs = resource_engine.create_from_definition(
        "test_resource_refresh_increment_formula",
        owner_scope="entity",
        owner_entity_id="player1"
    )
    # Player level is 5, capacity formula is level * 2 = 10
    assert rs.max_computed == 10
    assert rs.current == 10 # initial_current defaults to max_computed

    rs.current = 5 # Simulate resource being spent
    assert rs.current == 5

    # Increment by level / 2 = 5 / 2 = 2.5, int(2.5) = 2
    resource_engine.refresh_cadence("per_round")
    assert rs.current == 7 # 5 + 2

    resource_engine.refresh_cadence("per_round")
    assert rs.current == 9 # 7 + 2

    resource_engine.refresh_cadence("per_round")
    assert rs.current == 10 # 9 + 2, capped at max_computed

def test_resource_engine_refresh_cadence_other_cadence_not_triggered(resource_engine, mock_game_state):
    rs, logs = resource_engine.create_from_definition(
        "test_resource_refresh_reset",
        owner_scope="entity",
        owner_entity_id="player1"
    )
    rs.current = 2
    resource_engine.refresh_cadence("per_day") # Should not trigger per_round refresh
    assert rs.current == 2
