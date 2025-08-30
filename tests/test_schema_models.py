import pytest
from pydantic import ValidationError
from dndrpg.engine.schema_models import Modifier

def test_modifier_prefix_allowlist():
    with pytest.raises(ValidationError):
        Modifier(targetPath="combat.bab.effective", operator="add", value=1, bonusType="enhancement")

def test_modifier_bonusType_required_on_ac_add():
    with pytest.raises(ValidationError):
        Modifier(targetPath="ac.deflection", operator="add", value=1)

def test_modifier_speed_multiply_ok():
    Modifier(targetPath="speed.land", operator="multiply", value=1.5)

def test_modifier_tags_only_grant_remove():
    with pytest.raises(ValidationError):
        Modifier(targetPath="tags.haste", operator="add", value=1)
    Modifier(targetPath="tags.haste", operator="grantTag")
    Modifier(targetPath="tags.haste", operator="removeTag")

def test_modifier_replaceFormula_deprecated():
    with pytest.raises(ValidationError):
        Modifier(targetPath="ac.deflection", operator="replaceFormula", value="level()")

def test_valid_modifiers():
    # Valid AC modifier
    Modifier(targetPath="ac.deflection", operator="add", value=2, bonusType="deflection")
    # Valid ability modifier
    Modifier(targetPath="abilities.str.enhancement", operator="add", value=4, bonusType="enhancement")
    # Valid save modifier
    Modifier(targetPath="save.fort.resistance", operator="add", value=2, bonusType="resistance")
    # Valid attack modifier
    Modifier(targetPath="attack.melee.enhancement", operator="add", value=1, bonusType="enhancement")
    # Valid BAB modifier
    Modifier(targetPath="bab.base", operator="add", value=1, bonusType="unnamed")
    # Valid speed modifier
    Modifier(targetPath="speed.land", operator="add", value=10, bonusType="enhancement")
    # Valid resistance
    Modifier(targetPath="resist.fire", operator="add", value=10, bonusType="resistance")
    # Valid DR
    Modifier(targetPath="dr.adamantine", operator="add", value=5, bonusType="unnamed")
    # Valid senses
    Modifier(targetPath="senses.darkvision", operator="set", value=60)
    # Valid resource
    Modifier(targetPath="resources.rage", operator="add", value=1, bonusType="unnamed")

def test_invalid_operator_target_combos():
    # multiply on ac
    with pytest.raises(ValidationError):
        Modifier(targetPath="ac.armor", operator="multiply", value=2, bonusType="unnamed")
    # divide on saves
    with pytest.raises(ValidationError):
        Modifier(targetPath="save.will", operator="divide", value=2, bonusType="unnamed")
    # multiply on resist
    with pytest.raises(ValidationError):
        Modifier(targetPath="resist.cold", operator="multiply", value=2, bonusType="unnamed")
    # add on tags
    with pytest.raises(ValidationError):
        Modifier(targetPath="tags.confused", operator="add", value=1, bonusType="unnamed")
    # invalid operator for speed
    with pytest.raises(ValidationError):
        Modifier(targetPath="speed.fly", operator="grantTag", value=1, bonusType="unnamed")

def test_bonustype_not_required_for_non_add_sub():
    Modifier(targetPath="ac.deflection", operator="max", value=15)
    Modifier(targetPath="abilities.dex", operator="set", value=18)

def test_replaceformula_is_deprecated():
    with pytest.raises(ValidationError, match="deprecated"):
        Modifier(targetPath="ac.armor", operator="replaceFormula", value="10")

def test_converttype_is_invalid():
    with pytest.raises(ValidationError, match="not valid as a generic Modifier"):
        Modifier(targetPath="damage.base", operator="convertType", value="fire")
