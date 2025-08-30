from __future__ import annotations
from pathlib import Path
import json
from dndrpg.engine.schema_models import (
    EffectDefinition, ConditionDefinition, ResourceDefinition, TaskDefinition, ZoneDefinition
)

def export_schemas(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    schemas = {
        "EffectDefinition.schema.json": EffectDefinition.model_json_schema(),
        "ConditionDefinition.schema.json": ConditionDefinition.model_json_schema(),
        "ResourceDefinition.schema.json": ResourceDefinition.model_json_schema(),
        "TaskDefinition.schema.json": TaskDefinition.model_json_schema(),
        "ZoneDefinition.schema.json": ZoneDefinition.model_json_schema(),
    }
    for name, schema in schemas.items():
        (out_dir / name).write_text(json.dumps(schema, indent=2), encoding="utf-8")

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3] / "docs" / "schemas"
    export_schemas(root)
    print(f"Exported schemas to {root}")